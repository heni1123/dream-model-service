import os, json, pathlib
from .store_faiss import build_index, save_index

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUT = ROOT / "rag_store"
OUT.mkdir(parents=True, exist_ok=True)

def load_corpus():
    docs, metas = [], []
    # symbols.jsonl
    sym = DATA / "symbols.jsonl"
    if sym.exists():
        with sym.open("r", encoding="utf-8") as f:
            for line in f:
                j = json.loads(line)
                text = f"[SYMBOLE] {j['symbol']}\nMeanings: {', '.join(j['meanings'])}\nNotes: {j.get('notes','')}"
                docs.append(text)
                metas.append({"type":"symbol","symbol":j["symbol"]})
    # themes.md
    th = DATA / "themes.md"
    if th.exists():
        docs.append(th.read_text(encoding="utf-8"))
        metas.append({"type":"themes","file":"themes.md"})
    return docs, metas

def main():
    docs, metas = load_corpus()
    if not docs:
        raise SystemExit("Corpus vide. Ajoute data/symbols.jsonl et/ou data/themes.md")
    index = build_index(docs)
    save_index(index, str(OUT / "faiss.index"))
    (OUT / "docs.json").write_text(json.dumps(docs, ensure_ascii=False), encoding="utf-8")
    (OUT / "metas.json").write_text(json.dumps(metas, ensure_ascii=False), encoding="utf-8")
    print(f"Ingest OK: {len(docs)} docs → {OUT}")

if __name__ == "__main__":
    main()
