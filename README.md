# Dream Model Service (RAG + GPT)

## Démarrage

1) Copier l'exemple d'env et renseigner votre clé OpenAI:

```bash
cp .env.example .env
# puis éditez .env et remplissez OPENAI_API_KEY
```

2) Installer et démarrer:

```bash
pip install -e .
# (optionnel) reconstruire l'index de RAG si vous avez des données:
make ingest
# lancer le serveur
make run
```

## Test rapide

```bash
pytest -q
```

## Demo local (script)

Un script de démonstration est fourni pour appeler `/explain` localement sans réseau (utilise TestClient):

```bash
python scripts/demo_explain.py
```

L'estimation des tokens utilise `tiktoken` si installé, sinon une approximation simple.

## Endpoints principaux

- GET /health — vérifie que le service est up
- POST /analyze — lance l'analyse structurée (retourne le schéma complet)
- POST /explain — retourne une explication narrative compacte (optimisée en tokens)

## Notes sur l'optimisation des tokens

- Le service compacte le prompt système et tronque le contexte RAG avant envoi.
- Il envoie une petite liste de mots-clés extraits du contexte au lieu d'un contexte long.
- Pour réduire encore la consommation: définir `USE_STUB_OPENAI=true` pour tests locaux, augmenter `RAG_TOP_K` ou réduire `RAG_MAX_TOKENS` selon besoin.

## Variables d'environnement importantes

Voir `.env.example`. Les principales sont:

- OPENAI_API_KEY — clé OpenAI
- MODEL_NAME — modèle LLM utilisé
- EMBED_MODEL — modèle d'embeddings
- USE_STUB_OPENAI — si true, utilise des embeddings/stubs locaux pour tests
- RAG_TOP_K / RAG_MAX_TOKENS — contrôle de la récupération RAG

***

Pour toute amélioration plus avancée (ex: fine-tuning, pipelines NLP plus lourds, ou réduction plus agressive des tokens), je peux ajouter des composants optionnels: résumé préalable des docs RAG, usage d'un modèle d'embed plus petit, ou compression sémantique.
