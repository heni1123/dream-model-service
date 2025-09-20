from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# JSON Schema (aligne les tests que tu as fournis)
JSON_SCHEMA: Dict[str, Any] = {
  "type": "object",
  "properties": {
    "summary": {"type": "string"},
    "themes": {"type": "array", "items": {"type":"string"}},
    "symbols": {
      "type": "array",
      "items": {
        "type":"object",
        "properties": {
          "token":{"type":"string"},
          "meaning":{"type":"string"},
          "confidence":{"type":"number"}
        },
        "required":["token","meaning"]
      }
    },
    "emotions": {
      "type": "array",
      "items": {
        "type":"object",
        "properties":{"label":{"type":"string"},"score":{"type":"number"}},
        "required":["label","score"]
      }
    },
    "advice": {"type": "array", "items":{"type":"string"}},
    "safety_flags": {
      "type":"object",
      "properties":{"self_harm":{"type":"boolean"},"medical":{"type":"boolean"}},
      "required":["self_harm","medical"]
    },
    "language":{"type":"string"},
    "confidence":{"type":"number","minimum":0,"maximum":1}
  },
  "required": ["summary","themes","symbols","emotions","advice","safety_flags","language","confidence"]
}

# Pydantic pour parsing strict
class Symbol(BaseModel):
    token: str
    meaning: str
    confidence: float | None = None

class Emotion(BaseModel):
    label: str
    score: float

class DreamAnalysis(BaseModel):
    summary: str
    themes: List[str]
    symbols: List[Symbol]
    emotions: List[Emotion]
    advice: List[str]
    safety_flags: dict
    language: str
    confidence: float
    # champs additionnels côté service
    keywords: Optional[List[str]] = None
    sentiment: Optional[float] = None
    estimated_tokens: Optional[int] = None
    ts: Optional[int] = None
    meta: Optional[dict] = None
    rag_used: Optional[bool] = None
