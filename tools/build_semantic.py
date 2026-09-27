"""Build a reproducible bundled index from existing chunks; never modify source data.

Usage: python tools/build_semantic.py --model-dir /path/to/downloaded/snapshot
The model must already exist locally. No provider API is called.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

import numpy as np
from fastembed import TextEmbedding

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import retrieval


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--model-dir', required=True)
    options = args.parse_args()
    model_dir = Path(options.model_dir)
    model = TextEmbedding('BAAI/bge-small-en-v1.5', specific_model_path=str(model_dir),
                          local_files_only=True, threads=4, cuda=False)
    with retrieval.connect() as conn:
        rows = conn.execute('SELECT c.*, p.name FROM chunks c JOIN products p ON c.product_id=p.id ORDER BY c.id').fetchall()
    texts = [f"Product: {row['name']}\n{row['text']}" for row in rows]
    vectors = []
    for i in range(0, len(rows), 128):
        vectors.extend(model.passage_embed(texts[i:i+128], batch_size=16))
        print(f'Embedded {min(i+128,len(rows))}/{len(rows)} chunks', flush=True)
    matrix = np.asarray(vectors, dtype=np.float32)
    matrix /= np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-12)
    with tempfile.TemporaryDirectory() as work:
        output = Path(work) / 'vectors.npz'
        np.savez_compressed(output, vectors=matrix, ids=np.array([r['id'] for r in rows]),
                            products=np.array([r['product_id'] for r in rows]))
        manifest = {'model':'BAAI/bge-small-en-v1.5', 'model_repository':'Qdrant/bge-small-en-v1.5-onnx-Q',
                    'revision':model_dir.name, 'license':'MIT', 'dimensions':384, 'chunks':len(rows),
                    'corpus_sha256':hashlib.sha256(retrieval.DB.read_bytes()).hexdigest(),
                    'vectors_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
                    'language':'English', 'max_tokens':512, 'chunk_characters':1700,
                    'chunk_overlap_characters':250, 'query_api_cost':0,
                    'search':'Exact normalized dot product; equal-weight RRF k=60 with BM25',
                    'model_files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in model_dir.iterdir() if p.is_file()}}
        archive = REPO / 'semantic_bundle.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(output,'data/semantic/vectors.npz')
            bundle.writestr('data/semantic/manifest.json',json.dumps(manifest,indent=2))
            for path in model_dir.iterdir():
                if path.is_file():bundle.write(path,'assets/semantic_model/'+path.name)
        print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'chunks':len(rows)}))


if __name__ == '__main__':main()
