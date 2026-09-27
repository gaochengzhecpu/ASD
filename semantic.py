"""Local CPU embeddings and exact cosine search; no remote model calls at runtime."""
from functools import lru_cache
import hashlib
import json
import threading
from pathlib import Path

import numpy as np
from bundle import EVIDENCE_ROOT, ensure_bundle

MODEL = 'BAAI/bge-small-en-v1.5'
ROOT = EVIDENCE_ROOT / 'data' / 'semantic'
_lock = threading.Lock()


@lru_cache(maxsize=1)
def index():
    ensure_bundle()
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    corpus=EVIDENCE_ROOT/'data'/'epar.sqlite3'
    if hashlib.sha256(corpus.read_bytes()).hexdigest()!=manifest['corpus_sha256']:
        raise ValueError('Semantic index does not match this CMC corpus')
    path = ROOT / 'vectors.npz'
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['vectors_sha256']:
        raise ValueError('Semantic index integrity check failed')
    with np.load(path, allow_pickle=False) as saved:
        vectors = saved['vectors'].astype(np.float32)
        ids = saved['ids'].tolist()
        products = saved['products'].tolist()
    if len(ids) != len(vectors) or vectors.shape[1] != 384:
        raise ValueError('Semantic index shape mismatch')
    vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
    return vectors, ids, products


@lru_cache(maxsize=1)
def encoder():
    from fastembed import TextEmbedding
    model_dir = EVIDENCE_ROOT / 'assets' / 'semantic_model'
    if not (model_dir / 'model_optimized.onnx').exists():
        raise FileNotFoundError('Bundled embedding model is unavailable')
    # This path and local_files_only prevent an implicit network download in the app.
    return TextEmbedding(MODEL, specific_model_path=str(model_dir), local_files_only=True,
                         threads=2, cuda=False)


@lru_cache(maxsize=128)
def query_vector(text):
    with _lock:
        vector = np.asarray(next(encoder().query_embed(text)), dtype=np.float32)
    return vector / max(float(np.linalg.norm(vector)), 1e-12)


def search(question, targets=None, limit=40):
    vectors, ids, products = index()
    if targets:
        positions = np.array([i for i, product in enumerate(products) if product in targets])
    else:
        positions = np.arange(len(ids))
    if not len(positions):
        return []
    scores = vectors[positions] @ query_vector(question)
    order = np.argsort(-scores, kind='stable')[:limit]
    return [{'id': ids[int(positions[i])], 'score': float(scores[i])} for i in order]


def available():
    ensure_bundle()
    return (ROOT / 'manifest.json').exists()
