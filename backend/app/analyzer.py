import re
import threading
from collections import deque
from typing import Any

import numpy as np

from app.anomaly import predict as anomaly_predict
from app.cluster import centroid_drift, predict as cluster_predict
from app.config import get_settings
from app.embedder import embed


_HISTORY_LIMIT = 1000
_COLD_START_LIMIT = 8
_READY_HISTORY_LIMIT = 20
_MIXED_MODEL_CONFIDENCE_THRESHOLD = 0.45
_DRIFT_WARN_THRESHOLD = 0.35
_DRIFT_HIGH_THRESHOLD = 0.65
_HARD_FAILURE_RE = re.compile(
    r"traceback|stack trace|\bfailed\b.*\bfailed\b|exception:|error:",
    re.IGNORECASE,
)
_FAILURE_TERMS = ("error", "exception", "traceback", "failed")

_history_vectors: deque[list[float]] = deque(maxlen=_HISTORY_LIMIT)
_context_histories: dict[str, deque[list[float]]] = {}
_lock = threading.Lock()


def _clean_context_value(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "-")


def _normalize_context(context: dict[str, Any] | None) -> dict[str, str | None]:
    context = context or {}
    provider = _clean_context_value(context.get("provider"))
    model = _clean_context_value(context.get("model") or context.get("model_name"))
    relay = _clean_context_value(context.get("relay"))
    source = _clean_context_value(context.get("source"))
    session = _clean_context_value(context.get("session") or context.get("session_id"))

    if provider and model:
        context_key = f"{provider}:{model}"
    elif model:
        context_key = model
    elif relay:
        context_key = f"relay:{relay}"
    else:
        context_key = "global"

    return {
        "provider": provider or None,
        "model": model or None,
        "relay": relay or None,
        "source": source or None,
        "session": session or None,
        "context_key": context_key,
    }


def _baseline_status(size: int) -> str:
    if size < _COLD_START_LIMIT:
        return "cold_start"
    if size < _READY_HISTORY_LIMIT:
        return "warming"
    return "ready"


def _baseline_confidence(size: int) -> float:
    return round(float(min(1.0, size / _READY_HISTORY_LIMIT)), 4)


def _failure_signal(text: str) -> dict[str, Any]:
    lowered = text.lower()
    matched_terms = [term for term in _FAILURE_TERMS if term in lowered]
    hard_failure = bool(_HARD_FAILURE_RE.search(text))
    return {
        "matched_terms": matched_terms,
        "hard_failure": hard_failure,
        "score": 0.14 if hard_failure else (0.03 if matched_terms else 0.0),
    }


def _score_risk(
    *,
    anomaly_label: int,
    anomaly_score: float,
    drift_score: float,
    mixed_model: bool,
    text_length: int,
    baseline_status: str,
    failure: dict[str, Any],
    settings,
) -> tuple[float, str, list[str], dict[str, Any]]:
    reasons: list[str] = []
    ready = baseline_status == "ready"
    warming = baseline_status == "warming"

    drift_contribution = 0.0
    if drift_score > _DRIFT_WARN_THRESHOLD:
        multiplier = 0.45 if ready else 0.28 if warming else 0.18
        cap = 0.32 if ready else 0.22 if warming else 0.12
        drift_contribution = min(cap, drift_score * multiplier)
        reasons.append("semantic/style drift is elevated against the current context baseline")

    anomaly_contribution = 0.0
    if ready and anomaly_label == -1 and anomaly_score >= 0.15:
        anomaly_contribution = 0.32
        reasons.append("anomaly detector marked this response as out-of-distribution")

    mixed_contribution = 0.0
    if mixed_model:
        mixed_contribution = 0.14
        reasons.append("cluster confidence is low while drift is elevated")

    length_contribution = 0.0
    if text_length > 4000:
        length_contribution = 0.06 if ready else 0.03
        reasons.append("response is unusually long")

    failure_contribution = float(failure["score"])
    if failure["hard_failure"]:
        reasons.append("response contains hard failure or stack-trace markers")
    elif failure["matched_terms"]:
        reasons.append("response contains mild failure-related terms")

    risk_score = drift_contribution + anomaly_contribution + mixed_contribution + length_contribution + failure_contribution

    if baseline_status == "cold_start" and not failure["hard_failure"]:
        risk_score = min(risk_score, settings.risk_medium_threshold - 0.01)
    elif baseline_status == "warming" and not failure["hard_failure"] and risk_score >= settings.risk_high_threshold:
        risk_score = settings.risk_high_threshold - 0.01

    risk_score = round(float(min(1.0, max(0.0, risk_score))), 4)
    if risk_score >= settings.risk_high_threshold:
        risk_label = "HIGH"
    elif risk_score >= settings.risk_medium_threshold:
        risk_label = "MEDIUM"
    else:
        risk_label = "LOW"

    if not reasons:
        reasons.append("response is close to the current context baseline")

    signals = {
        "drift": {
            "score": round(float(drift_score), 4),
            "contribution": round(float(drift_contribution), 4),
            "warn_threshold": _DRIFT_WARN_THRESHOLD,
            "high_threshold": _DRIFT_HIGH_THRESHOLD,
        },
        "anomaly": {
            "label": int(anomaly_label),
            "score": round(float(anomaly_score), 4),
            "contribution": round(float(anomaly_contribution), 4),
            "enabled": ready,
        },
        "cluster": {
            "mixed_model": bool(mixed_model),
            "contribution": round(float(mixed_contribution), 4),
        },
        "length": {
            "characters": text_length,
            "contribution": round(float(length_contribution), 4),
            "threshold": 4000,
        },
        "failure_terms": {
            **failure,
            "contribution": round(float(failure_contribution), 4),
        },
    }
    return risk_score, risk_label, reasons, signals


def analyze(text: str, context: dict[str, Any] | None = None) -> dict:
    settings = get_settings()
    normalized_context = _normalize_context(context)
    context_key = str(normalized_context["context_key"])
    vector = embed(text)

    with _lock:
        history = _context_histories.setdefault(context_key, deque(maxlen=_HISTORY_LIMIT))
        history_snapshot = list(history)
        history_with_current = history_snapshot + [vector.tolist()]
        history_size_before_current = len(history_snapshot)
        status = _baseline_status(history_size_before_current)
        anomaly_label, anomaly_score = anomaly_predict(history_with_current, vector)
        cluster, probabilities = cluster_predict(history_with_current, vector)
        drift_score = centroid_drift(history_with_current, vector)
        history.append(vector.tolist())
        _history_vectors.append(vector.tolist())

    max_probability = max(probabilities.values()) if probabilities else 0.0
    mixed_model = (
        status == "ready"
        and drift_score > _DRIFT_WARN_THRESHOLD
        and max_probability < _MIXED_MODEL_CONFIDENCE_THRESHOLD
    )
    failure = _failure_signal(text)
    risk_score, risk_label, reasons, signals = _score_risk(
        anomaly_label=anomaly_label,
        anomaly_score=anomaly_score,
        drift_score=drift_score,
        mixed_model=mixed_model,
        text_length=len(text),
        baseline_status=status,
        failure=failure,
        settings=settings,
    )
    signals["cluster"].update({
        "max_probability": round(float(max_probability), 4),
        "confidence_threshold": _MIXED_MODEL_CONFIDENCE_THRESHOLD,
    })

    return {
        "vector": np.round(vector, 6).tolist(),
        "anomaly_label": int(anomaly_label),
        "anomaly_score": round(float(anomaly_score), 4),
        "cluster": int(cluster),
        "drift_score": round(float(drift_score), 4),
        "model_probabilities": probabilities,
        "mixed_model": bool(mixed_model),
        "risk_score": risk_score,
        "risk_label": risk_label,
        "reasons": reasons,
        "context_key": context_key,
        "baseline_size": history_size_before_current,
        "baseline_status": status,
        "confidence": _baseline_confidence(history_size_before_current),
        "signals": signals,
    }


def warm_history(vectors: list[list[float]], context: dict[str, Any] | None = None) -> None:
    context_key = str(_normalize_context(context)["context_key"])
    with _lock:
        history = _context_histories.setdefault(context_key, deque(maxlen=_HISTORY_LIMIT))
        for vector in vectors[-_HISTORY_LIMIT:]:
            history.append(vector)
            _history_vectors.append(vector)


def history_size(context: dict[str, Any] | None = None) -> int:
    if context is None:
        with _lock:
            return len(_history_vectors)
    context_key = str(_normalize_context(context)["context_key"])
    with _lock:
        return len(_context_histories.get(context_key, ()))


def reset_history() -> None:
    with _lock:
        _history_vectors.clear()
        _context_histories.clear()
