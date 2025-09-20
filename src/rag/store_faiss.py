import os, faiss, numpy as np
from typing import List
import hashlib
from ..config import EMBED_MODEL, USE_STUB_OPENAI


def _client():
    # when not using stub, the service-level openai client will be used elsewhere;
    # for embeddings we keep using the OpenAI package when not stubbed.
    from openai import OpenAI
    return OpenAI()

def embed_texts(texts: List[str]) -> np.ndarray:
    chunks = [t.replace("\n"," ") for t in texts]
    if USE_STUB_OPENAI:
        # deterministic pseudo-embeddings: hash each chunk into a 1536-d vector
        dim = 1536
        vecs = []
        for c in chunks:
            h = hashlib.sha256(c.encode('utf-8')).digest()
            # expand to dim by repeating hash bytes and converting to floats
            arr = np.frombuffer(h * (dim // len(h) + 1), dtype='B')[:dim].astype('float32')
            # normalize
            arr = arr / (np.linalg.norm(arr) + 1e-6)
            vecs.append(arr)
        return np.array(vecs, dtype='float32')
    else:
        resp = _client().embeddings.create(model=EMBED_MODEL, input=chunks)
        vecs = np.array([d.embedding for d in resp.data], dtype="float32")
        return vecs

def build_index(texts: List[str]):
    vecs = embed_texts(texts)
    faiss.normalize_L2(vecs)
    index = faiss.IndexFlatIP(vecs.shape[1])
    index.add(vecs)
    return index

def save_index(index: faiss.IndexFlatIP, path: str):
    faiss.write_index(index, path)

def load_index(path: str) -> faiss.IndexFlatIP:
    return faiss.read_index(path)

def search(index: faiss.IndexFlatIP, queries: List[str], k: int = 5):
    q = embed_texts(queries)
    faiss.normalize_L2(q)
    sims, idxs = index.search(q, k)
    return sims, idxs
