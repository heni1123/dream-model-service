import time
from typing import Any, Dict, Tuple

_STORE: Dict[str, Tuple[float, Any]] = {}

def get(key: str):
    item = _STORE.get(key)
    if not item:
        return None
    exp, val = item
    if exp < time.time():
        _STORE.pop(key, None)
        return None
    return val

def setex(key: str, ttl_seconds: int, value: Any):
    _STORE[key] = (time.time() + ttl_seconds, value)
