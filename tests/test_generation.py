"""Offline checks; never call a paid provider during the test suite."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import generation as g
import retrieval
from data_access import load_json


class GenerationTests(unittest.TestCase):
    def pack(self,name='Gavreto'):
        return g.evidence_pack(retrieval.query(f'What is the ASD carrier of {name}?'),load_json('products.json'))

    def test_review_does_not_promote_inference_and_sources_resolve(self):
        pack=self.pack()
        self.assertEqual(pack['saved_review'][0]['carrier'],'HPMC')
        self.assertEqual(pack['saved_review'][0]['carrier_basis'],'Inferred')
        ids={p['id'] for p in pack['source_passages']}
        self.assertLessEqual(sum(len(p['text']) for p in pack['source_passages']),22000)
        for fact in pack['extracted_facts']:self.assertTrue(set(fact['sources']).issubset(ids))
        self.assertIn('never an exhaustive',pack['retrieval_scope'])

    def test_missing_key_or_sources_never_calls_provider(self):
        with patch.object(g,'provider_answer') as provider:
            with self.assertRaises(g.AnswerError):g.AnswerService().answer(self.pack(),'','session')
            pack=self.pack();pack['source_passages']=[]
            with self.assertRaises(g.AnswerError):g.AnswerService().answer(pack,'test-key','session')
            provider.assert_not_called()

    def test_cache_and_rate_limit(self):
        service=g.AnswerService();pack=self.pack()
        result={'answer':'Test [004759:p1]','citations':[],'model':g.MODEL,'usage':{},'cached':False}
        with patch.object(g,'provider_answer',return_value=result) as provider:
            self.assertFalse(service.answer(pack,'test-key','session')['cached'])
            self.assertTrue(service.answer(pack,'test-key','session')['cached'])
            other={**pack,'question':'Another question'}
            with self.assertRaises(g.AnswerError):service.answer(other,'test-key','session')
            self.assertEqual(provider.call_count,1)

    def test_invalid_citation_and_remote_links_rejected(self):
        pack=self.pack();valid=pack['source_passages'][0]['id']
        for answer in ['No citations','Invented [999999:p999]',f'See https://example.com [{valid}]',f'HPMC is the only polymeric excipient [{valid}]']:
            response=unittest.mock.MagicMock()
            response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':answer},'finish_reason':'stop'}]}).encode()
            with patch.object(g,'urlopen',return_value=response):
                with self.assertRaises(g.AnswerError):g.provider_answer(pack,'test-key','session')

    def test_grouped_citations_validate_every_identifier(self):
        pack=self.pack();first,second=[p['id'] for p in pack['source_passages'][:2]]
        response=unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':f'Inference [{first}, {second}]'},'finish_reason':'stop'}]}).encode()
        with patch.object(g,'urlopen',return_value=response):
            self.assertEqual(g.provider_answer(pack,'test-key','session')['citations'],sorted([first,second]))

    def test_missing_extraction_record_has_its_own_citation(self):
        pack=g.evidence_pack(retrieval.query('What is the pKa of Palsonify?',method='bm25'),load_json('products.json'))
        record=next(r for r in pack['derived_records'] if r.get('field')=='pka')
        self.assertEqual(record['id'],'006636:f5')
        self.assertEqual(record['status'],'not_reported')
        self.assertEqual(record['source_ids'],[])

    def test_reasoning_only_truncation_is_not_treated_as_an_answer(self):
        pack=self.pack()
        response=unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':None,'reasoning_content':'Internal reasoning, not a final answer.'},'finish_reason':'length'}]}).encode()
        with patch.object(g,'urlopen',return_value=response) as provider:
            with self.assertRaisesRegex(g.AnswerError,'response limit'):
                g.provider_answer(pack,'test-key','session')
            payload=json.loads(provider.call_args.args[0].data)
            self.assertEqual(payload['reasoning_effort'],'low')
            self.assertEqual(payload['max_tokens'],4096)
            self.assertEqual(provider.call_count,1)

    def test_reasoning_is_never_used_as_a_fallback_answer(self):
        pack=self.pack()
        response=unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':'','reasoning_content':'Not user-facing content.'},'finish_reason':'stop'}]}).encode()
        with patch.object(g,'urlopen',return_value=response):
            with self.assertRaisesRegex(g.AnswerError,'returned no answer'):
                g.provider_answer(pack,'test-key','session')

    def test_valid_derived_citation_and_invalid_group(self):
        pack=self.pack();ident=pack['derived_records'][0]['id']
        for citation,valid in [(ident,True),(ident+', 999999:f1',False)]:
            response=unittest.mock.MagicMock()
            response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':'Saved record ['+citation+']'},'finish_reason':'stop'}]}).encode()
            with patch.object(g,'urlopen',return_value=response):
                if valid:self.assertEqual(g.provider_answer(pack,'test-key','session')['citations'],[ident])
                else:
                    with self.assertRaises(g.AnswerError):g.provider_answer(pack,'test-key','session')

if __name__=='__main__':unittest.main()
