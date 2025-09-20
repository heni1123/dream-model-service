# src/service.py
import os
import json
import time
import tiktoken
from hashlib import sha256
from openai import OpenAI
from jsonschema import validate

from .openai_client import client
from .prompts import STATIC_PREFIX
from .schema import JSON_SCHEMA, DreamAnalysis
from .config import MODEL_NAME, CACHE_TTL_SECONDS
from .nlp import keywords as nlp_keywords, sentiment_score
from .cache import get as cache_get, setex as cache_setex
from .utils import key_for, uniq_sorted, now_ms, estimate_tokens

client = OpenAI()

USE_PROMPT_CACHE_KEY = os.getenv("USE_PROMPT_CACHE_KEY", "true").lower() in ("1", "true", "yes")


# ---------- Helpers ----------
def _trim_tokens(text: str, max_tokens: int = 1200) -> str:
    """Tronque le texte par nombre de tokens (cl100k_base)."""
    try:
        enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        return text[:4000]
    ids = enc.encode(text)
    if len(ids) <= max_tokens:
        return text
    return enc.decode(ids[:max_tokens])

def _extract_json_block(txt: str) -> str | None:
    if not txt: return None
    start, end = txt.find("{"), txt.rfind("}")
    if start != -1 and end != -1 and end > start:
        return txt[start:end+1].strip()
    return None

def _attempt_json_repair(txt: str) -> str | None:
    blk = _extract_json_block(txt) or txt
    open_count, close_count = blk.count("{"), blk.count("}")
    if open_count > close_count:
        blk = blk + ("}" * (open_count - close_count))
    blk = blk.replace(", }", " }").replace(",}", "}")
    return blk.strip()



# ---------- RAG stub ----------
_rag = None
def rag():
    global _rag
    if _rag is None:
        class _Dummy:
            def retrieve(self, q): return []
            def compress_for_query(self, items, query, max_chars=900): return ""
            def pack_context(self, items): return ""
        _rag = _Dummy()
    return _rag


# ---------- Service principal ----------
def analyze(text: str, lang: str | None = None, seed: int | None = 42,
            meta: dict | None = None, use_rag: bool | None = True):
    if not text or not text.strip():
        raise ValueError("Le texte du rêve est vide.")

    # Cache applicatif
    cache_key = key_for(f"{text}|{lang}|{use_rag}", lang)
    cached = cache_get(cache_key)
    if cached:
        return cached | {"cached": True}

    # Baseline locale
    baseline_keywords = [w for w in text.replace("\n", " ").split() if len(w) > 4]
    lite_keywords = nlp_keywords(text, top_k=6)
    sent = sentiment_score(text)

    # RAG optionnel
    context = ""
    if use_rag:
        items = rag().retrieve(text)
        try:
            context = rag().compress_for_query(items, query=text, max_chars=900)
        except Exception:
            context = (rag().pack_context(items) or "")[:1200]
        if items:
            doc_text = "\n".join([getattr(it, "text", "") or it.get("text", "") for it in items if it])
            doc_kws = nlp_keywords(doc_text, top_k=8)
            if doc_kws:
                context += "\n\nContexte mots-clés: " + ", ".join(doc_kws)

    # Préfixe statique TRONQUÉ
    compact_prefix = _trim_tokens(STATIC_PREFIX or "", 1200)
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        print("[debug] prefix_tokens(before)=", len(enc.encode(STATIC_PREFIX or "")))
        print("[debug] prefix_tokens(after) =", len(enc.encode(compact_prefix)))
    except Exception:
        pass

    # Messages (format Responses)
    system_msg = (
        "You are DreamAI. Return ONLY compact JSON that matches the schema. "
        "No markdown. No extra text. No explanations."
    )
    user_msg = (
        f"<locale>{lang or 'auto'}</locale>\n"
        f"{f'<context>{context[:1200]}</context>\n' if context else ''}"
        f"<dream>{text}</dream>"
    )
    messages = [
        {"role": "system", "content": [{"type": "text", "text": compact_prefix + "\n\n" + system_msg}]},
        {"role": "user",   "content": [{"type": "text", "text": user_msg}]},
        {"role": "user",   "content": [{"type": "text", "text":
            "BASELINE_HINT=" + json.dumps({
                "keywords": lite_keywords[:6],
                "sentiment_hint": sent
            }, ensure_ascii=False)
        }]},
    ]

    # Clé stable pour cache prompt
    PREFIX_VERSION = os.getenv("PROMPT_VERSION", "v1")
    prefix_hash = sha256(compact_prefix.encode("utf-8")).hexdigest()[:16]
    stable_cache_key = f"dreamai:{PREFIX_VERSION}:{prefix_hash}"

    # ----- Appel modèle -----
    t0 = time.time()
    text_out = ""
    model_returned = MODEL_NAME
    usage = None

    try:
        # Chemin 1: Responses API + JSON Schema
        resp = client.responses.create(
            model=MODEL_NAME,
            input=messages,
            max_output_tokens=300,
            response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
            prompt_cache_key=stable_cache_key if USE_PROMPT_CACHE_KEY else None,
        )
        text_out = resp.output[0].content[0].text
        model_returned = getattr(resp, "model", MODEL_NAME)
        usage = getattr(resp, "usage", None)
        text_out = (text_out or "").strip()
        candidate = _extract_json_block(text_out)
        if candidate:
            text_out = candidate
        else:
            text_out = _attempt_json_repair(text_out)


    except TypeError as e:
        # Chemin 2: fallback Chat Completions (sans temperature) + schéma imposé
        from openai import OpenAI as _OpenAI
        _fallback = _OpenAI()
        print("[fallback] responses.create() incompatible -> chat.completions.create()", e)

        schema_in_system = (
            "You are DreamAI. Return ONLY a JSON object with EXACTLY these fields:\n"
            '{ "summary": "string (≤2 sentences)",'
            '  "themes": ["string"] (≤5),'
            '  "emotions": ["joy","fear","sadness","anger","surprise","disgust","neutral"],'
            '  "sentiment": {"score": number in [-1,1]},'
            '  "keywords": ["string"] (≤8, lowercase),'
            '  "advice": "string (≤2 sentences)",'
            '  "language": "input language code" }\n'
            "No markdown, no explanation, no extra fields."
        )
        compact_system = compact_prefix + "\n\n" + schema_in_system

        def _call_chat(model_name: str) -> tuple[str, str, object]:
            user_prompt = (
                f"LANG={lang or 'auto'}\n"
                f"TEXT={text}\n"
                "BASELINE_HINT=" + json.dumps({
                    "keywords": lite_keywords[:6],
                    "sentiment_hint": sent,
                }, ensure_ascii=False) + "\n"
                "Respond with the JSON object ONLY (no backticks)."
            )
            comp = _fallback.chat.completions.create(
                model=model_name,
                max_completion_tokens=400,  # certains SDK exigent ce nom
                messages=[
                    {"role": "system", "content": compact_system},
                    {"role": "user", "content": user_prompt},
                ],
            )
            out = (comp.choices[0].message.content or "").strip()
            candidate = _extract_json_block(out)
            if candidate:
                out = candidate
            else:
                out = _attempt_json_repair(out)
            mdl = getattr(comp, "model", model_name)
            return out, mdl, getattr(comp, "usage", None)


        text_out, model_returned, usage = _call_chat(MODEL_NAME)

        def _looks_like_schema(s: str) -> bool:
            return s.startswith("{") and all(k in s for k in ('"summary"', '"themes"', '"emotions"', '"sentiment"'))

        if not _looks_like_schema(text_out):
            FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gpt-4o-mini")
            print(f"[fallback2] output not matching schema with {MODEL_NAME} -> retry with {FALLBACK_MODEL}")
            try:
                text_out, model_returned, usage = _call_chat(FALLBACK_MODEL)
            except Exception as e2:
                print("[fallback2] error:", e2)
                text_out = ""
                
        if not text_out:
            baseline_obj = {
                "summary": (text.strip()[:180] or "Rêve enregistré."),
                "themes": lite_keywords[:5] or [],
                "symbols": [],
                "emotions": (["fear"] if isinstance(sent, dict) and sent.get("score", 0) < 0 else ["neutral"]),
                "sentiment": float(sent.get("score", 0)) if isinstance(sent, dict) else 0.0,  # <- nombre
                "keywords": [k.lower() for k in (lite_keywords[:6] or [])],
                "advice": ["Note le rêve au réveil et observe les thèmes récurrents."],         # <- liste
                "safety_flags": {"self_harm": False, "medical": False},                         # <- requis
                "confidence": 0.7,                                                              # <- requis
                "language": lang or "auto",
                }
            text_out = json.dumps(baseline_obj, ensure_ascii=False)


    latency_ms = int((time.time() - t0) * 1000)

    # Usage/métriques
    cached_tokens = 0
    input_tokens = 0
    try:
        if isinstance(usage, dict):
            input_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
            ptd = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
            cached_tokens = int(ptd.get("cached_tokens") or 0)
        elif usage:
            input_tokens = int(getattr(usage, "input_tokens", 0) or getattr(usage, "prompt_tokens", 0) or 0)
            ptd = getattr(usage, "input_tokens_details", None) or getattr(usage, "prompt_tokens_details", None)
            if isinstance(ptd, dict):
                cached_tokens = int(ptd.get("cached_tokens") or 0)
            else:
                cached_tokens = int(getattr(ptd, "cached_tokens", 0) or 0)
    except Exception:
        pass

      # Parsing JSON strict + normalisation vers DreamAnalysis
    try:
        data = json.loads(text_out)

        # --- Normalisation vers ton Pydantic DreamAnalysis ---
        # advice: string -> [string]
        if "advice" in data and isinstance(data["advice"], str):
            data["advice"] = [data["advice"]]

        # sentiment: {score: x} -> x (float)
        if isinstance(data.get("sentiment"), dict):
            data["sentiment"] = float(data["sentiment"].get("score", 0.0))

        # champs requis par DreamAnalysis: defaults si manquants
        data.setdefault("symbols", [])
        data.setdefault("safety_flags", {"self_harm": False, "medical": False})
        data.setdefault("confidence", 0.7)

        # si keywords absents: fallback minimal
        if "keywords" not in data or not isinstance(data["keywords"], list):
            data["keywords"] = (lite_keywords[:6] or [])

        # language
        data.setdefault("language", lang or "auto")

        # ⚠️ On peut valider contre JSON_SCHEMA *après* normalisation si tu veux :
        # validate(data, JSON_SCHEMA)

        obj = DreamAnalysis(**data)

    except Exception:
        print("[LLM RAW OUTPUT]", (text_out or "")[:400])
        data = {
            "summary": (text_out.strip() or "Analyse non disponible."),
            "themes": [],
            "symbols": [],
            "emotions": [],
            "advice": [],                       # liste vide OK
            "safety_flags": {"self_harm": False, "medical": False},
            "language": lang or "auto",
            "confidence": 0.4,
            "sentiment": 0.0,                   # nombre (pas objet)
            "keywords": [],
        }
        obj = DreamAnalysis(**data)


    # Réponse finale
    merged_keywords = uniq_sorted((getattr(obj, "keywords", []) or []) + baseline_keywords + lite_keywords)
    result = obj.model_dump()
    result["keywords"] = merged_keywords
    result["sentiment"] = sent
    result["estimated_tokens"] = estimate_tokens(compact_prefix) + estimate_tokens(user_msg)
    result["ts"] = result.get("ts") or now_ms()
    result["meta"] = meta or None
    result["cached"] = False
    result["rag_used"] = bool(use_rag)
    result["metrics"] = {
        "latency_ms": latency_ms,
        "cached_tokens": cached_tokens,
        "input_tokens": input_tokens,
        "model": model_returned,
    }

    cache_setex(cache_key, CACHE_TTL_SECONDS, result)
    return result
