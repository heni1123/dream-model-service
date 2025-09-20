import hashlib, base64, time, json
from typing import Iterable

def key_for(text: str, lang: str | None) -> str:
    raw = f"{lang or 'auto'}:{text}".encode("utf-8")
    return "dream:" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode()[:44]

def uniq_sorted(xs: Iterable[str]) -> list[str]:
    return sorted(list({x.strip().lower() for x in xs if x and isinstance(x, str)}))

def now_ms() -> int:
    return int(time.time() * 1000)

def safe_json_parse(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None

def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, int(len(text) / 4))
