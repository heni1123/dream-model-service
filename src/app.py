# src/app.py
import logging
from time import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from .service import analyze
from .explainer import explain_dream

# Prometheus
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
)

# registre dédié (évite les doublons quand --reload)
_PROM_REGISTRY = CollectorRegistry()

requests_total = Counter("requests_total", "Total HTTP requests", registry=_PROM_REGISTRY)
explain_requests_total = Counter("explain_requests_total", "Total explain requests", registry=_PROM_REGISTRY)

request_latency_seconds = Histogram(
    "request_latency_seconds", "Request latency in seconds", registry=_PROM_REGISTRY
)

tokens_estimated_total = Counter(
    "tokens_estimated_total", "Sum of estimated tokens sent to model", registry=_PROM_REGISTRY
)
cached_tokens_total = Counter(
    "cached_tokens_total", "Total cached prompt tokens", registry=_PROM_REGISTRY
)
input_tokens_total = Counter(
    "input_tokens_total", "Total prompt input tokens", registry=_PROM_REGISTRY
)
cache_hit_ratio_last = Gauge(
    "cache_hit_ratio_last", "Last request cache hit ratio (cached_tokens / input_tokens)", registry=_PROM_REGISTRY
)
cache_hit_ratio_hist = Histogram(
    "cache_hit_ratio", "Distribution of cache hit ratios per request",
    registry=_PROM_REGISTRY,
    buckets=[0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0, 2.5, 5.0, 7.5, 10.0]
)

logger = logging.getLogger("dream")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # resserre si tu as un domaine précis
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Req(BaseModel):
    text: str
    lang: str | None = None
    seed: int | None = 42
    meta: dict | None = None
    use_rag: bool | None = True

# -------- Playground simple (GET /) --------
@app.get("/", response_class=HTMLResponse)
def index():
    html = Path(__file__).resolve().parent.parent / "static" / "index.html"
    if html.exists():
        return HTMLResponse(html.read_text(encoding="utf-8"))
    # fallback minimal si le fichier n'existe pas
    return HTMLResponse("<h1>DreamAI</h1><p>Copiez la page playground dans static/index.html</p>")

# -------- logging requêtes --------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time()
    resp = await call_next(request)
    logger.info(f"{request.method} {request.url.path} completed_in={time()-start:.3f}s")
    return resp

# -------- endpoints --------
@app.get("/health")
def health():
    requests_total.inc()
    return {"ok": True}

@app.post("/analyze")
def analyze_endpoint(r: Req, response: Response):
    try:
        requests_total.inc()
        with request_latency_seconds.time():
            out = analyze(text=r.text, lang=r.lang, seed=r.seed, meta=r.meta, use_rag=r.use_rag)

        # métriques -> Prometheus + headers
        m = out.get("metrics", {}) if isinstance(out, dict) else {}
        cached = int(m.get("cached_tokens") or 0)
        inp = int(m.get("input_tokens") or 0)
        est = out.get("estimated_tokens")

        cached_tokens_total.inc(cached)
        if inp:
            input_tokens_total.inc(inp)
            ratio = (cached / max(inp, 1))
            cache_hit_ratio_last.set(ratio)
            cache_hit_ratio_hist.observe(ratio)

        if est is not None:
            tokens_estimated_total.inc(int(est))

        if cached:
            response.headers["X-Cached-Tokens"] = str(cached)
        if est is not None:
            response.headers["X-Estimated-Tokens"] = str(int(est))

        return out
    except Exception as e:
        logger.exception("Error in /analyze")  # Ajout du log d'exception
        raise HTTPException(status_code=502, detail=str(e)) from e

@app.post("/explain")
def explain_endpoint(r: Req, response: Response):
    try:
        requests_total.inc(); explain_requests_total.inc()
        out = explain_dream(text=r.text, lang=r.lang, use_rag=bool(r.use_rag))

        # propage quelques métriques depuis l'analyse brute si dispo
        raw = out.get("raw") if isinstance(out, dict) else None
        m = raw.get("metrics", {}) if isinstance(raw, dict) else {}
        cached = int(m.get("cached_tokens") or 0)
        inp = int(m.get("input_tokens") or 0)
        est = out.get("estimated_tokens")

        cached_tokens_total.inc(cached)
        if inp:
            input_tokens_total.inc(inp)
            ratio = (cached / max(inp, 1))
            cache_hit_ratio_last.set(ratio)
            cache_hit_ratio_hist.observe(ratio)

        if est is not None:
            tokens_estimated_total.inc(int(est))

        if cached:
            response.headers["X-Cached-Tokens"] = str(cached)
        if est is not None:
            response.headers["X-Estimated-Tokens"] = str(int(est))

        return out
    except Exception as e:
        logger.exception("Error in /explain")  # Ajout du log d'exception
        raise HTTPException(status_code=502, detail=str(e)) from e

@app.post("/explain/compact")
def explain_compact_endpoint(r: Req, response: Response):
    try:
        requests_total.inc(); explain_requests_total.inc()
        if not r.text or not r.text.strip():
            raise HTTPException(status_code=400, detail="Le champ 'text' est vide.")

        # ⚠️ compact = sans RAG pour rester court et éviter les troncatures
        out = explain_dream(text=r.text, lang=r.lang, use_rag=False)

        # propage métriques (inchangé)
        m = out.get("metrics", {}) if isinstance(out, dict) else {}
        cached = int(m.get("cached_tokens") or 0)
        inp = int(m.get("input_tokens") or 0)
        est = out.get("estimated_tokens")

        cached_tokens_total.inc(cached)
        if inp:
            input_tokens_total.inc(inp)
            ratio = (cached / max(inp, 1))
            cache_hit_ratio_last.set(ratio)
            cache_hit_ratio_hist.observe(ratio)
        if est is not None:
            tokens_estimated_total.inc(int(est))
            response.headers["X-Estimated-Tokens"] = str(int(est))
        if cached:
            response.headers["X-Cached-Tokens"] = str(cached)

        return out
    except Exception as e:
        logger.exception("Error in /explain/compact")
        raise HTTPException(status_code=502, detail=str(e)) from e




@app.get("/metrics")
def metrics():
    data = generate_latest(_PROM_REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

# --- optionnel: /warmup pour précharger le cache prompt côté modèle ---
@app.post("/warmup")
def warmup():
    payloads = [
        {"text": "Je tombe dans un puits sans fin.", "lang": "fr", "use_rag": False},
        {"text": "Je cours dans un couloir sombre, quelqu’un me poursuit.", "lang": "fr", "use_rag": False},
    ]
    summary = []
    for p in payloads:
        out = analyze(**p)
        m = out.get("metrics", {})
        summary.append({
            "cached_tokens": int(m.get("cached_tokens") or 0),
            "input_tokens": int(m.get("input_tokens") or 0),
            "latency_ms": int(m.get("latency_ms") or 0),
        })
    return {"ok": True, "calls": len(summary), "summary": summary}
