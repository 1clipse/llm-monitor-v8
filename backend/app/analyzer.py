import threading
from collections import deque
import numpy as np

from app.anomaly import predict as anomaly_predict
from app.cluster import centroid_drift, predict as cluster_predict
from app.config import get_settings
from app.embedder import embed


_HISTORY_LIMIT = 1000
_history_vectors: deque[list[float]] = deque(maxlen=_HISTORY_LIMIT)
_lock = threading.Lock()


def analyze(text: str) -> dict:
    settings = get_settings()
    vector = embed(text)

    with _lock:
        history_snapshot = list(_history_vectors)
        history_with_current = history_snapshot + [vector.tolist()]
        anomaly_label, anomaly_score = anomaly_predict(history_with_current, vector)
        cluster, probabilities = cluster_predict(history_with_current, vector)
        drift_score = centroid_drift(history_with_current, vector)
        _history_vectors.append(vector.tolist())

    max_probability = max(probabilities.values()) if probabilities else 0.0
    mixed_model = max_probability < 0.58

    risk_score = 0.0
    reasons: list[str] = []

    if anomaly_label == -1:
        risk_score += 0.38
        reasons.append("anomaly detector marked this response as out-of-distribution")
    if drift_score > 0.35:
        risk_score += min(0.32, drift_score * 0.45)
        reasons.append("semantic/style drift is elevated against recent history")
    if mixed_model:
        risk_score += 0.18
        reasons.append("model probability distribution is mixed")
    if len(text) > 4000:
        risk_score += 0.08
        reasons.append("response is unusually long")
    if any(token in text.lower() for token in ["error", "exception", "traceback", "failed"]):
        risk_score += 0.08
        reasons.append("response contains failure-related terms")

    risk_score = round(float(min(1.0, risk_score)), 4)
    if risk_score >= settings.risk_high_threshold:
        risk_label = "HIGH"
    elif risk_score >= settings.risk_medium_threshold:
        risk_label = "MEDIUM"
    else:
        risk_label = "LOW"

    if not reasons:
        reasons.append("response is close to recent local baseline")

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
    }


def warm_history(vectors: list[list[float]]) -> None:
    with _lock:
        for vector in vectors[-_HISTORY_LIMIT:]:
            _history_vectors.append(vector)


def history_size() -> int:
    with _lock:
        return len(_history_vectors)
