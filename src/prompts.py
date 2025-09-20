from .config import PROMPT_PREFIX_PATH

# Charge un prefix STATIQUE (≥1024 tokens avec rules+schema+few-shots)
try:
    with open(PROMPT_PREFIX_PATH, "r", encoding="utf-8") as f:
        STATIC_PREFIX = f.read()
except FileNotFoundError:
    # petit fallback si le fichier n'existe pas (à remplacer par ton vrai prompt)
    STATIC_PREFIX = (
        "Tu es DreamAI, analyste onirique factuel et bienveillant. "
        "Explique les symboles, émotions, hypothèses (stress, routines, mémoire) "
        "sans ésotérisme ni diagnostic. Répond en JSON STRICT selon le schéma."
    )
