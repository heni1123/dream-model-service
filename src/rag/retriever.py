import json, os, pathlib
from typing import List, Dict
from .store_faiss import load_index, search
from ..config import RAG_TOP_K, RAG_MAX_TOKENS

ROOT = pathlib.Path(__file__).resolve().parents[2]
STORE = ROOT / "rag_store"

class RAG:
    def __init__(self):
        self.index = load_index(str(STORE / "faiss.index"))
        self.docs = json.loads((STORE / "docs.json").read_text(encoding="utf-8"))
        self.metas = json.loads((STORE / "metas.json").read_text(encoding="utf-8"))

    def retrieve(self, query: str, k: int = RAG_TOP_K) -> List[Dict]:
        _, idxs = search(self.index, [query], k=k)
        items = []
        for i in idxs[0]:
            if i < 0: continue
            items.append({"text": self.docs[i], "meta": self.metas[i]})
        return items

    def pack_context(self, items: List[Dict]) -> str:
        MAX_CTX_CHARS = RAG_MAX_TOKENS * 3
        buf, total = [], 0
        for it in items:
            chunk = it["text"].strip()
            if total + len(chunk) > MAX_CTX_CHARS: break
            buf.append(chunk)
            total += len(chunk)
        return "\n\n---\n\n".join(buf)

    def compress_for_query(self, items: List[Dict], query: str, max_chars: int = 800) -> str:
        """Simple semantic compression: split docs into sentences and pick those
        with highest token overlap with the query until max_chars reached.
        This is a lightweight heuristic to avoid extra LLM calls while reducing tokens.
        """
        import re
        from collections import Counter
        q_toks = re.findall(r"[\wÀ-ÖØ-öø-ÿ']+", query.lower())
        q_set = set([t for t in q_toks if len(t) > 2])

        sentences = []
        for it in items:
            # split into sentences
            parts = re.split(r'(?<=[\.!?])\s+', it.get('text','').strip())
            for p in parts:
                if not p: continue
                tokens = re.findall(r"[\wÀ-ÖØ-öø-ÿ']+", p.lower())
                tokens = [t for t in tokens if len(t) > 2]
                overlap = sum(1 for t in tokens if t in q_set)
                sentences.append((overlap, len(p), p))

        # sort by overlap desc then shorter length asc
        sentences.sort(key=lambda x: (-x[0], x[1]))

        out = []
        total = 0
        for ov, ln, sent in sentences:
            if ov == 0 and total > (max_chars // 3):
                # after collecting some relevant bits, stop when sentences have no overlap
                break
            if total + len(sent) > max_chars:
                continue
            out.append(sent.strip())
            total += len(sent)
            if total >= max_chars:
                break

        return "\n\n---\n\n".join(out)
