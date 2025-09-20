#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "1) Créer/activer venv .venv"
if [ ! -d .venv ]; then
  python -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip

echo "2) Installer dépendances"
pip install -r requirements.txt || true

echo "3) Préparer .env (ne sera pas écrasé si existe)"
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "Copié .env.example → .env (vérifie et complète OPENAI_API_KEY)"
  else
    echo "Fichier .env.example manquant; crée un .env minimal"
    cat > .env <<EOF
OPENAI_API_KEY=
MODEL_NAME=gpt-5
USE_STUB_OPENAI=true
EOF
  fi
else
  echo ".env existe déjà — je ne le modifie pas"
fi

echo "4) Ingest (reconstruire l'index RAG)"
make ingest || true

echo "5) Démarrer uvicorn en arrière-plan (utilise le python du venv)"
# charge .env pour les variables
set -a; source .env; set +a

# tuer proprement les uvicorn existants
PIDS=$(ps aux | awk '/[u]vicorn/ {print $2}') || true
if [ -n "${PIDS}" ]; then
  echo "Killing existing uvicorn PIDs: ${PIDS}"
  kill ${PIDS} || true
  sleep 0.5
fi

VENV_PY="$ROOT/.venv/bin/python"
"$VENV_PY" -m uvicorn src.app:app --host 0.0.0.0 --port ${PORT:-8080} &
UV_PID=$!
echo "uvicorn started (pid=$UV_PID)"

echo "Waiting for server to become ready..."
for i in {1..10}; do
  if curl -sS http://127.0.0.1:${PORT:-8080}/health >/dev/null 2>&1; then
    echo "Server is up"
    break
  fi
  sleep 1
done

echo "6) Tester /health"
curl -sS http://127.0.0.1:${PORT:-8080}/health || true

echo "7) Test /analyze (payload court)"
curl -sS -X POST http://127.0.0.1:${PORT:-8080}/analyze -H 'Content-Type: application/json' -d '{"text":"Je volais.","lang":"fr","use_rag":false}' || true

echo "8) Lancer pytest (avec PYTHONPATH)
"
PYTHONPATH=./ pytest -q || true

echo "Script auto_run.sh terminé"
