import re
from collections import Counter
from typing import List

_SENT_LEX = {
    "bon": 1, "bien": 1, "heureux": 1, "calme": 1,
    "triste": -1, "anxieux": -1, "peur": -1, "colère": -1, "colere": -1,
}

def tokenize(text: str) -> List[str]:
    return re.findall(r"[\wÀ-ÖØ-öø-ÿ']+", (text or "").lower())

def keywords(text: str, top_k: int = 8) -> List[str]:
    toks = [t for t in tokenize(text) if len(t) > 3]
    cnt = Counter(toks)
    return [w for w,_ in cnt.most_common(top_k)]

def sentiment_score(text: str) -> float:
    toks = tokenize(text)
    s = n = 0
    for t in toks:
        if t in _SENT_LEX:
            s += _SENT_LEX[t]; n += 1
    if n == 0:
        return 0.0
    return max(-1.0, min(1.0, s / n))
