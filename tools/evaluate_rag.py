"""Same-corpus retrieval comparison. No LLM/embedding API or answer-quality score."""
import json
from pathlib import Path
import sys
import time
from collections import defaultdict
REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
import retrieval
import generation
from data_access import load_json


def main():
    suite=json.loads((REPO/'evaluation/questions.json').read_text())
    products=load_json('products.json');runs=[]
    for method in ['bm25','dense','hybrid']:
        for case in suite['questions']:
            start=time.perf_counter()
            r=retrieval.query(case['q'],method=method)
            seconds=time.perf_counter()-start
            ranked=[p['page_id'] for p in r['ranked_pages']]
            pack=generation.evidence_pack(r,products)
            packed={p['id'] for p in pack['source_passages']}
            expected=set(case['pages'])
            rank=next((i for i,p in enumerate(ranked,1) if p in expected),None)
            row={'id':case['id'],'group':case['group'],'method':method,'actual_method':r['retrieval_method'],
                 'known_page_hit_at_5':bool(expected & set(ranked[:5])),
                 'known_page_recall_at_8':len(expected & set(ranked[:8]))/len(expected),
                 'reciprocal_rank_at_8':1/rank if rank else 0,
                 'packed_reference_coverage':len(expected & packed)/len(expected),
                 'seconds':round(seconds,4),'ranked_pages':ranked,'packed_pages':sorted(packed)}
            runs.append(row)
        print('Completed '+method,flush=True)
    metrics=[]
    for method in ['bm25','dense','hybrid']:
        for group in ['all','named product','paraphrase','no brand name']:
            subset=[r for r in runs if r['method']==method and (group=='all' or r['group']==group)]
            metrics.append({'method':method,'group':group,'questions':len(subset),
                            **{key:round(sum(r[key] for r in subset)/len(subset),3) for key in ['known_page_hit_at_5','known_page_recall_at_8','reciprocal_rank_at_8','packed_reference_coverage','seconds']}})
    out={'scope':suite['scope'],'model':'BAAI/bge-small-en-v1.5, local ONNX','corpus':'same 6,348 chunks for every method',
         'metrics':metrics,'runs':runs,'limitations':['Reference pages selected by the same assistant implementing the system.','Development/regression evaluation, not blinded.','Known-page hits are not precision or answer factual accuracy.','Named products are filtered consistently before all three retrieval methods.','Packed coverage includes structured-field routing; raw rank metrics exclude it.','Latency includes model cold start; not a controlled server benchmark.']}
    (REPO/'evaluation/results.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps(metrics,indent=2))


if __name__=='__main__':main()
