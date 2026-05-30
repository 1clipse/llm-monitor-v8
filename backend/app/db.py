from collections.abc import Generator
from datetime import datetime
from math import ceil
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base, LogEntry


settings = get_settings()
engine_kwargs = {}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, future=True, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

_SQLITE_LOG_COLUMNS = {
    "model_name": "TEXT",
    "provider": "TEXT",
    "session_id": "TEXT",
    "prompt_tokens": "INTEGER",
    "completion_tokens": "INTEGER",
    "total_tokens": "INTEGER",
    "token_source": "TEXT",
    "metadata": "JSON",
    "raw": "JSON",
}


def _ensure_log_schema() -> None:
    inspector = inspect(engine)
    existing = {column["name"] for column in inspector.get_columns("logs")}
    missing = [(name, column_type) for name, column_type in _SQLITE_LOG_COLUMNS.items() if name not in existing]
    if not missing:
        return

    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        for name, column_type in missing:
            connection.execute(text(f"ALTER TABLE logs ADD COLUMN {name} {column_type}"))
        connection.execute(text("UPDATE logs SET prompt_tokens = CAST((length(coalesce(prompt, '')) + 3) / 4 AS INTEGER) WHERE prompt_tokens IS NULL"))
        connection.execute(text("UPDATE logs SET completion_tokens = CAST((length(coalesce(response_text, '')) + 3) / 4 AS INTEGER) WHERE completion_tokens IS NULL"))
        connection.execute(text("UPDATE logs SET total_tokens = coalesce(prompt_tokens, 0) + coalesce(completion_tokens, 0) WHERE total_tokens IS NULL OR total_tokens = 0"))
        connection.execute(text("UPDATE logs SET model_name = coalesce(nullif(model_name, ''), 'unknown-model') WHERE model_name IS NULL OR model_name = ''"))
        connection.execute(text("UPDATE logs SET token_source = coalesce(nullif(token_source, ''), 'estimated') WHERE token_source IS NULL OR token_source = ''"))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_log_schema()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _nested_value(source: Any, *paths: tuple[str, ...]):
    for path in paths:
        current = source
        for key in path:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if current not in (None, ""):
            return current
    return None


def _extract_model_name(metadata: dict, raw: dict | None) -> str:
    model = _nested_value(
        metadata,
        ("model",),
        ("model_name",),
        ("data", "model"),
        ("payload", "model"),
    ) or _nested_value(
        raw,
        ("model",),
        ("response", "model"),
        ("payload", "model"),
        ("source", "model"),
    )
    return str(model or "unknown-model")


def _extract_provider(metadata: dict, raw: dict | None) -> str | None:
    provider = _nested_value(metadata, ("provider",), ("provider_name",)) or _nested_value(raw, ("provider",), ("source",))
    return str(provider) if provider else None


def _extract_session_id(metadata: dict, raw: dict | None) -> str | None:
    session = _nested_value(metadata, ("session",), ("session_id",), ("session_key",)) or _nested_value(raw, ("session",), ("session_id",))
    return str(session) if session else None


def _int_value(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return None


def _extract_usage(metadata: dict, raw: dict | None) -> tuple[int | None, int | None, int | None, str]:
    prompt_tokens = _int_value(_nested_value(
        raw,
        ("usage", "prompt_tokens"),
        ("usage", "input_tokens"),
        ("token_usage", "prompt_tokens"),
        ("token_usage", "input"),
    ) or _nested_value(
        metadata,
        ("usage", "prompt_tokens"),
        ("usage", "input_tokens"),
        ("token_usage", "prompt_tokens"),
        ("token_usage", "input"),
        ("input_tokens",),
    ))
    completion_tokens = _int_value(_nested_value(
        raw,
        ("usage", "completion_tokens"),
        ("usage", "output_tokens"),
        ("token_usage", "completion_tokens"),
        ("token_usage", "output"),
    ) or _nested_value(
        metadata,
        ("usage", "completion_tokens"),
        ("usage", "output_tokens"),
        ("token_usage", "completion_tokens"),
        ("token_usage", "output"),
        ("output_tokens",),
    ))
    total_tokens = _int_value(_nested_value(
        raw,
        ("usage", "total_tokens"),
        ("token_usage", "total_tokens"),
    ) or _nested_value(
        metadata,
        ("usage", "total_tokens"),
        ("token_usage", "total_tokens"),
        ("total_tokens",),
    ))

    if prompt_tokens is not None or completion_tokens is not None or total_tokens is not None:
        total_tokens = total_tokens if total_tokens is not None else (prompt_tokens or 0) + (completion_tokens or 0)
        return prompt_tokens, completion_tokens, total_tokens, "reported"

    return None, None, None, "estimated"


def _estimate_tokens(text_value: str | None) -> int:
    return ceil(len(text_value or "") / 4)


def save_log(db: Session, payload: dict) -> LogEntry:
    metadata = payload.get("metadata") or {}
    raw = payload.get("raw") or {}
    prompt_tokens, completion_tokens, total_tokens, token_source = _extract_usage(metadata, raw)
    if total_tokens is None:
        prompt_tokens = _estimate_tokens(payload.get("prompt"))
        completion_tokens = _estimate_tokens(payload.get("text"))
        total_tokens = prompt_tokens + completion_tokens

    entry = LogEntry(
        created_at=payload.get("time") or datetime.utcnow(),
        relay=payload.get("relay", "mock"),
        prompt=payload["prompt"],
        response_text=payload["text"],
        risk_label=payload["analysis"]["risk_label"],
        risk_score=payload["analysis"]["risk_score"],
        drift_score=payload["analysis"].get("drift_score", 0.0),
        mixed_model=payload["analysis"].get("mixed_model", False),
        model_name=_extract_model_name(metadata, raw),
        provider=_extract_provider(metadata, raw),
        session_id=_extract_session_id(metadata, raw),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        token_source=token_source,
        metadata_json=metadata,
        raw_json=raw,
        analysis=payload["analysis"],
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def build_logs_query(db: Session, start: datetime | None = None, end: datetime | None = None):
    query = db.query(LogEntry)
    if start:
        query = query.filter(LogEntry.created_at >= start)
    if end:
        query = query.filter(LogEntry.created_at <= end)
    return query


def get_recent_logs(db: Session, limit: int = 100) -> list[LogEntry]:
    return build_logs_query(db).order_by(LogEntry.id.desc()).limit(limit).all()


def get_logs_between(db: Session, start: datetime | None = None, end: datetime | None = None, limit: int | None = 500) -> list[LogEntry]:
    query = build_logs_query(db, start, end).order_by(LogEntry.id.desc())
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def get_logs_page(
    db: Session,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[LogEntry], int]:
    query = build_logs_query(db, start, end)
    total = query.count()
    entries = query.order_by(LogEntry.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return entries, total


def get_logs_for_export(db: Session, start: datetime | None = None, end: datetime | None = None, max_rows: int = 10000) -> list[LogEntry]:
    return build_logs_query(db, start, end).order_by(LogEntry.id.desc()).limit(max_rows).all()


def get_model_usage(db: Session, start: datetime | None = None, end: datetime | None = None) -> list[dict]:
    buckets: dict[str, dict] = {}
    for entry in build_logs_query(db, start, end).all():
        model_name = entry.model_name or "unknown-model"
        if model_name not in buckets:
            buckets[model_name] = {
                "model_name": model_name,
                "provider": entry.provider,
                "token_source": entry.token_source or "estimated",
                "tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "request_count": 0,
            }
        item = buckets[model_name]
        item["tokens"] += int(entry.total_tokens or 0)
        item["prompt_tokens"] += int(entry.prompt_tokens or 0)
        item["completion_tokens"] += int(entry.completion_tokens or 0)
        item["request_count"] += 1
        if item["token_source"] != "reported" and entry.token_source == "reported":
            item["token_source"] = "reported"
        if not item["provider"] and entry.provider:
            item["provider"] = entry.provider

    return sorted(buckets.values(), key=lambda item: item["tokens"], reverse=True)
