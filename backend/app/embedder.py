import numpy as np


FEATURE_SIZE = 24


def embed(text: str) -> np.ndarray:
    words = text.split()
    sentences = max(1, text.count(".") + text.count("!") + text.count("?") + text.count("。") + text.count("！") + text.count("？"))
    unique_words = len(set(w.lower() for w in words))
    word_count = max(1, len(words))

    vec = np.zeros(FEATURE_SIZE, dtype=float)
    vec[0] = len(text)
    vec[1] = len(words)
    vec[2] = text.count("\n")
    vec[3] = text.count(".") + text.count("。")
    vec[4] = text.count(",") + text.count("，")
    vec[5] = text.count("def ")
    vec[6] = text.count("class ")
    vec[7] = text.count("return")
    vec[8] = sum(c.isupper() for c in text)
    vec[9] = sum(c.isdigit() for c in text)
    vec[10] = unique_words / word_count
    vec[11] = len([w for w in words if len(w) > 8])
    vec[12] = text.count("?") + text.count("？")
    vec[13] = text.count("!") + text.count("！")
    vec[14] = text.count("{") + text.count("}")
    vec[15] = text.count("[") + text.count("]")
    vec[16] = text.count("http://") + text.count("https://")
    vec[17] = len(text) / sentences
    vec[18] = sum(ord(c) > 127 for c in text) / max(1, len(text))
    vec[19] = text.lower().count("error") + text.lower().count("exception")
    vec[20] = text.lower().count("risk") + text.count("风险")
    vec[21] = text.count("```")
    vec[22] = sum(c in "+-*/=<>&|" for c in text)
    vec[23] = sum(c.isspace() for c in text) / max(1, len(text))

    scale = np.array([
        2000, 300, 20, 80, 120, 10, 10, 30, 300, 100,
        1, 80, 30, 30, 80, 80, 10, 400, 1, 20,
        20, 20, 300, 1,
    ], dtype=float)
    vec = vec / scale
    norm = np.linalg.norm(vec)
    return vec if norm == 0 else vec / norm
