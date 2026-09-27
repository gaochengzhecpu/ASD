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

if __name__=='__main__':unittest.main()
