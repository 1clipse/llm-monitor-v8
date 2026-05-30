import csv
import io
import math
import time
from datetime import datetime, time as datetime_time

from fastapi import APIRouter, Depends, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.analyzer import analyze
from app.auth import require_auth
from app.client import call_llm, delete_relay_config, list_relay_configs, save_relay_config
from app.db import get_db, get_logs_between, get_logs_for_export, get_logs_page, get_model_usage, get_recent_logs, save_log
from app.metrics import ANALYSIS_LATENCY, ASK_REQUESTS, DRIFT_SCORE, HIGH_RISK_RESPONSES, RISK_SCORE, metrics_response
from app.models import LogEntry
from app.notifier import notify_if_configured
from app.schemas import AskRequest, IngestRequest, LogResponse, ModelUsageResponse, PaginatedLogsResponse, RelayConfig, StatsResponse
from app.websocket import manager

router = APIRouter()


_SECRET_KEYS = {"api_key", "apikey", "authorization", "token", "secret", "password"}
_TEXT_PATHS = [
    ("message", "text"),
    ("message", "content"),
    ("message", "body"),
    ("data", "message", "text"),
    ("data", "message", "content"),
    ("data", "content"),
    ("data", "text"),
    ("payload", "message", "text"),
    ("payload", "content"),
    ("text",),
    ("content",),
    ("reply",),
    ("response",),
    ("output",),
]


def _get_nested(payload: dict, path: tuple[str, ...]):
    current = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _stringify_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part).strip()
    if isinstance(value, dict):
        return str(value.get("text") or value.get("content") or value.get("body") or "").strip()
    return str(value).strip()


def _extract_text(payload: dict) -> str:
    for path in _TEXT_PATHS:
        text = _stringify_text(_get_nested(payload, path))
        if text:
            return text
    return ""


def _extract_metadata_value(payload: dict, *names: str):
    for name in names:
        value = payload.get(name)
        if value:
            return value
    for container in (payload.get("data"), payload.get("message"), payload.get("payload")):
        if isinstance(container, dict):
            for name in names:
                value = container.get(name)
                if value:
                    return value
    return None


def _redact_secrets(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if any(secret in key.lower() for secret in _SECRET_KEYS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [_redact_secrets(item) for item in value]
    return value


def _entry_to_response(entry: LogEntry) -> dict:
    return {
        "id": entry.id,
        "time": entry.created_at,
        "relay": entry.relay,
        "prompt": entry.prompt,
        "text": entry.response_text,
        "analysis": entry.analysis,
        "model_name": entry.model_name,
        "provider": entry.provider,
        "prompt_tokens": entry.prompt_tokens,
        "completion_tokens": entry.completion_tokens,
        "total_tokens": entry.total_tokens,
        "token_source": entry.token_source,
    }


def _day_start(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value.date(), datetime_time.min)


def _day_end(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value.date(), datetime_time.max)


def _stats_from_entries(entries: list[LogEntry]) -> dict:
    total = len(entries)
    high = sum(1 for item in entries if item.risk_label == "HIGH")
    high_drift = sum(1 for item in entries if item.drift_score >= 0.65)
    medium = sum(1 for item in entries if item.risk_label == "MEDIUM")
    low = sum(1 for item in entries if item.risk_label == "LOW")
    anomaly = high + medium
    average_risk = sum(item.risk_score for item in entries) / total if total else 0.0
    average_drift = sum(item.drift_score for item in entries) / total if total else 0.0
    latest_drift = entries[0].drift_score if entries else 0.0

    probabilities: dict[str, float] = {}
    if entries:
        latest_probs = entries[0].analysis.get("model_probabilities", {})
        probabilities = {key: float(value) for key, value in latest_probs.items()}

    return {
        "total": total,
        "high_risk": high,
        "high_drift": high_drift,
        "medium_risk": medium,
        "low_risk": low,
        "average_risk_score": round(average_risk, 4),
        "average_drift_score": round(average_drift, 4),
        "latest_drift_score": round(latest_drift, 4),
        "anomaly_ratio": round(anomaly / total, 4) if total else 0.0,
        "model_probabilities": probabilities,
    }


async def _analyze_and_store(
    db: Session,
    *,
    relay: str,
    prompt: str,
    text: str,
    metadata: dict | None = None,
    raw: dict | None = None,
) -> dict:
    started = time.perf_counter()
    with ANALYSIS_LATENCY.time():
        analysis = analyze(text)
    elapsed = time.perf_counter() - started
    analysis["analysis_latency_seconds"] = round(elapsed, 6)

    DRIFT_SCORE.set(analysis["drift_score"])
    RISK_SCORE.set(analysis["risk_score"])
    if analysis["risk_label"] == "HIGH":
        HIGH_RISK_RESPONSES.inc()

    log_payload = {
        "time": datetime.utcnow(),
        "relay": relay,
        "prompt": prompt,
        "text": text,
        "analysis": analysis,
        "metadata": metadata or {},
        "raw": raw,
    }
    entry = save_log(db, log_payload)
    response = _entry_to_response(entry)

    await manager.broadcast({"type": "log", "payload": response})
    if analysis["risk_label"] == "HIGH":
        await notify_if_configured(response)

    return response


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "llm-monitor-v8"}


@router.get("/relays", response_model=list[RelayConfig])
def relays(_: dict = Depends(require_auth)) -> list[dict]:
    return list_relay_configs(mask_keys=True)


@router.post("/relays", response_model=RelayConfig)
def upsert_relay(payload: RelayConfig, _: dict = Depends(require_auth)) -> dict:
    try:
        return save_relay_config(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/relays/{name}")
def delete_relay(name: str, _: dict = Depends(require_auth)) -> dict:
    try:
        delete_relay_config(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "deleted", "name": name}


@router.post("/ask", response_model=LogResponse)
async def ask(payload: AskRequest, db: Session = Depends(get_db), _: dict = Depends(require_auth)) -> dict:
    relay = payload.relay or "mock"
    ASK_REQUESTS.labels(relay=relay).inc()

    llm_result = await call_llm(payload.prompt, relay)
    return await _analyze_and_store(
        db,
        relay=relay,
        prompt=payload.prompt,
        text=llm_result["text"],
        metadata=payload.metadata,
        raw=llm_result.get("raw"),
    )


@router.post("/ingest", response_model=LogResponse)
async def ingest(payload: IngestRequest, db: Session = Depends(get_db), _: dict = Depends(require_auth)) -> dict:
    ASK_REQUESTS.labels(relay=f"ingest:{payload.relay}").inc()
    metadata = dict(payload.metadata)
    if payload.model:
        metadata["model"] = payload.model
    metadata["monitoring_mode"] = "passive_ingest_zero_api_cost"
    return await _analyze_and_store(
        db,
        relay=payload.relay,
        prompt=payload.prompt or "",
        text=payload.text,
        metadata=metadata,
        raw={"source": "ingest", "model": payload.model},
    )


@router.post("/integrations/cc-connect", response_model=LogResponse)
async def cc_connect_hook(payload: dict, db: Session = Depends(get_db)) -> dict:
    text = _extract_text(payload)
    if not text:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "No reply text found in cc-connect hook payload",
                "top_level_keys": sorted(payload.keys()),
            },
        )

    project = _extract_metadata_value(payload, "project", "project_name") or "cc-connect"
    model = _extract_metadata_value(payload, "model", "model_name")
    provider = _extract_metadata_value(payload, "provider", "provider_name")
    session = _extract_metadata_value(payload, "session", "session_id", "session_key")
    event = _extract_metadata_value(payload, "event") or "message.sent"
    prompt = _stringify_text(_extract_metadata_value(payload, "prompt", "input", "user_message"))

    metadata = {
        "source": "cc-connect",
        "event": event,
        "project": project,
        "session": session,
        "model": model,
        "provider": provider,
        "monitoring_mode": "cc_connect_hook_zero_api_cost",
    }
    ASK_REQUESTS.labels(relay="cc-connect").inc()
    return await _analyze_and_store(
        db,
        relay="cc-connect",
        prompt=prompt,
        text=text,
        metadata={key: value for key, value in metadata.items() if value},
        raw={"source": "cc-connect", "payload": _redact_secrets(payload)},
    )


@router.get("/logs", response_model=PaginatedLogsResponse)
def logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
) -> dict:
    entries, total = get_logs_page(db, _day_start(start), _day_end(end), page, page_size)
    total_pages = math.ceil(total / page_size) if total else 0
    return {
        "items": [_entry_to_response(entry) for entry in entries],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


@router.get("/logs/chart", response_model=list[LogResponse])
def chart_logs(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=2000, ge=1, le=10000),
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
) -> list[dict]:
    entries = get_logs_between(db, _day_start(start), _day_end(end), limit)
    return [_entry_to_response(entry) for entry in reversed(entries)]


@router.get("/models/usage", response_model=ModelUsageResponse)
def model_usage(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
) -> dict:
    items = get_model_usage(db, _day_start(start), _day_end(end))
    return {
        "items": items,
        "total_tokens": sum(item["tokens"] for item in items),
        "total_requests": sum(item["request_count"] for item in items),
    }


@router.get("/stats", response_model=StatsResponse)
def stats(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
) -> dict:
    entries = get_logs_between(db, _day_start(start), _day_end(end), None) if start or end else get_logs_between(db, None, None, None)
    return _stats_from_entries(entries)


@router.get("/logs/export")
def export_logs(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
) -> Response:
    entries = get_logs_for_export(db, _day_start(start), _day_end(end))
    output = io.StringIO()
    output.write("﻿")
    writer = csv.writer(output)
    writer.writerow(["ID", "时间", "中转", "模型", "Provider", "Token", "Token 来源", "状态", "风险分", "漂移分", "混模型", "提示词", "回复内容", "原因"])
    for entry in entries:
        analysis = entry.analysis or {}
        writer.writerow([
            entry.id,
            entry.created_at.isoformat(sep=" ", timespec="seconds"),
            entry.relay,
            entry.model_name or "unknown-model",
            entry.provider or "",
            entry.total_tokens or 0,
            entry.token_source or "estimated",
            entry.risk_label,
            round(float(entry.risk_score or 0), 4),
            round(float(entry.drift_score or 0), 4),
            "是" if bool(analysis.get("mixed_model", entry.mixed_model)) else "否",
            entry.prompt,
            entry.response_text,
            "; ".join(analysis.get("reasons", [])),
        ])

    filename = f"llm-monitor-logs-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/metrics")
def metrics():
    return metrics_response()


@router.websocket("/ws/logs")
async def logs_ws(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
