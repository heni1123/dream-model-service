# src/explainer.py
from typing import Dict, Any
from .service import analyze

def explain_dream(text: str, lang: str | None = None, use_rag: bool | None = False) -> Dict[str, Any]:
    """
    Appelle service.analyze() et renvoie le résultat tel quel (objet DreamAnalysis normalisé + meta).
    Ne reconditionne pas en 'narrative', ne change pas les types.
    """
    return analyze(text=text, lang=lang, use_rag=use_rag)
