import numpy as np
from sklearn.cluster import KMeans


MODEL_NAMES = ["gpt_like", "claude_like", "local_or_mixed"]
_MIN_SAMPLES = 6


def _softmax(values: np.ndarray) -> np.ndarray:
    values = values - np.max(values)
    exp = np.exp(values)
    return exp / np.sum(exp)


def predict(history_vectors: list[list[float]] | list[np.ndarray], vector: np.ndarray) -> tuple[int, dict[str, float]]:
    if len(history_vectors) < _MIN_SAMPLES:
        return 0, {"gpt_like": 0.34, "claude_like": 0.33, "local_or_mixed": 0.33}

    matrix = np.asarray(history_vectors, dtype=float)
    cluster_count = min(3, len(matrix))
    kmeans = KMeans(n_clusters=cluster_count, n_init="auto", random_state=42)
    labels = kmeans.fit_predict(matrix)
    cluster = int(kmeans.predict([vector])[0])

    distances = np.linalg.norm(kmeans.cluster_centers_ - vector, axis=1)
    probabilities = _softmax(-distances)

    named = {}
    for idx, name in enumerate(MODEL_NAMES):
        named[name] = float(probabilities[idx]) if idx < len(probabilities) else 0.0

    total = sum(named.values()) or 1.0
    named = {key: round(value / total, 4) for key, value in named.items()}
    return cluster, named


def centroid_drift(history_vectors: list[list[float]] | list[np.ndarray], vector: np.ndarray) -> float:
    if len(history_vectors) < 2:
        return 0.0
    matrix = np.asarray(history_vectors, dtype=float)
    centroid = np.mean(matrix[:-1] if len(matrix) > 2 else matrix, axis=0)
    return float(min(1.0, np.linalg.norm(vector - centroid)))
