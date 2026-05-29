import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM


_MIN_SAMPLES = 8


def predict(history_vectors: list[list[float]] | list[np.ndarray], vector: np.ndarray) -> tuple[int, float]:
    if len(history_vectors) < _MIN_SAMPLES:
        return 1, 0.0

    matrix = np.asarray(history_vectors, dtype=float)
    forest = IsolationForest(contamination="auto", random_state=42)
    forest.fit(matrix)
    forest_label = int(forest.predict([vector])[0])
    forest_score = float(-forest.score_samples([vector])[0])

    svm_label = 1
    try:
        svm = OneClassSVM(gamma="auto", nu=0.12)
        svm.fit(matrix)
        svm_label = int(svm.predict([vector])[0])
    except Exception:
        svm_label = forest_label

    label = -1 if forest_label == -1 or svm_label == -1 else 1
    normalized_score = min(1.0, max(0.0, forest_score / 0.8))
    return label, normalized_score
