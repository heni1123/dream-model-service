run:
	uvicorn src.app:app --host 0.0.0.0 --port 8080 --reload

test:
	pytest

eval:
	python eval/evaluate.py  # si tu ajoutes l’éval plus tard

ingest:
	python -m src.rag.ingest
