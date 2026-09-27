"""User-oriented regressions: query boundaries, missing data and compound salt scope."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import catalogue as c
import qa
import retrieval
import generation
from data_access import load_json


class QueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products=load_json('products.json')
        cls.by_name={p['product']:p for p in cls.products}

    def test_counts_never_retrieve_or_call_model(self):
        with patch.object(retrieval,'query') as search,patch.object(generation,'provider_answer') as provider:
            r=qa.prepare('How many products are salts?',self.products)
            self.assertEqual(r['kind'],'catalogue')
            self.assertEqual(r['denominator'],351)
            self.assertEqual(len(r['matched'])+r['excluded_count']+len(r['uncertain']),351)
            search.assert_not_called();provider.assert_not_called()
            self.assertIn('Twynsta',[p['Product'] for p in r['matched']])
            self.assertNotIn('Sotyktu',[p['Product'] for p in r['matched']])

    def test_salt_scientific_boundaries(self):
        for name,expected in [('Qtern','Stage-dependent'),('Olysio','Stage-dependent'),('Zontivity','Stage-dependent'),
            ('Bylvay','Unknown'),('Voranigo','Unknown'),('Sotyktu','Non-salt'),('Braftovi','Non-salt'),
            ('Fylrevy','Non-salt'),('Fexeric','Complex / inorganic'),('Palforzia','Not applicable'),('Etcamah','Unknown')]:
            self.assertEqual(c.salt_record(self.by_name[name])['status'],expected,name)

    def test_dates_are_actually_applied(self):
        plan=c.plan_question('List salt products approved between 2020 and 2025')
        r=c.execute(plan,self.products)
        self.assertTrue(r['matched'])
        self.assertTrue(all('2020-01-01'<=p['First authorisation']<='2025-12-31' for p in r['matched']))
        self.assertEqual(c.plan_question('How many ASD products after 2025?').start,'2026-01-01')
        self.assertTrue(c.plan_question('How many salts in 2025-99-99?').problem)

    def test_unsupported_conditions_never_silently_count(self):
        for q in ['How many salt drugs were FDA approved?','How many ASD products do not contain HPMCAS?',
                  'List salt products for oncology','Count salts before February 2020',
                  'List HPMCAS or copovidone products','How many hydrochloride products?',
                  'Count products; DROP TABLE products']:
            r=qa.prepare(q,self.products)
            self.assertEqual(r['kind'],'clarification',q)

    def test_mixed_language_and_bcs(self):
        plan=c.plan_question('有多少个药物是salt被批准的')
        self.assertEqual(plan.filters,{'salt':'Salt'});self.assertFalse(plan.problem)
        plan=c.plan_question('How many BCS class II products are there?')
        self.assertFalse(plan.problem);self.assertEqual(plan.filters,{'bcs':'2'})
        def product(v):
            return {'fields':[{'key':'bcs','value':v,'status':'reported'}]}
        self.assertFalse(c._field_match(product('Class III'),'bcs',r'\b(?:class\s*)?(?:II|2)\b',False)[0])

    def test_carrier_role_and_uncertainty(self):
        r=qa.prepare('List ASD products using HPMCAS',self.products)
        self.assertIn('Sotyktu',[x['Product'] for x in r['matched']])
        self.assertIn('Tibsovo',[x['Product'] for x in r['matched']])
        r=qa.prepare('List ASD products using HPMCAS, reported only',self.products)
        self.assertIn('Sotyktu',[x['Product'] for x in r['matched']])
        self.assertNotIn('Tibsovo',[x['Product'] for x in r['matched']])
        self.assertNotIn('Rhapsido',[x['Product'] for x in r['matched']])
        r=qa.prepare('Which drugs use HPMCAS as an excipient?',self.products)
        self.assertEqual(r['kind'],'catalogue')
        self.assertIn('excipient',r['plan']['filters'])
        self.assertEqual(qa.prepare('Which drugs use HPMCAS?',self.products)['kind'],'clarification')

    def test_missing_properties_are_direct_and_bounded(self):
        with patch.object(generation,'provider_answer') as provider:
            r=qa.prepare('What is the pKa of Palsonify?',self.products,method='bm25')
            self.assertEqual(r['kind'],'direct');self.assertIn('not reported',r['answer'])
            self.assertIn('006636:f5',r['answer'])
            r=qa.prepare('What is the polymer of Etcamah?',self.products,method='bm25')
            self.assertEqual(r['kind'],'direct');self.assertIn('no public CMC',r['answer'])
            provider.assert_not_called()

    def test_comparison_keeps_both_products(self):
        r=qa.prepare('Compare the ASD carrier of Sotyktu and Gavreto',self.products,method='bm25')
        self.assertEqual(r['kind'],'evidence')
        self.assertEqual({p['product'] for p in r['pack']['source_passages']},{'Sotyktu','Gavreto'})
        self.assertIn('Inferred',[r.get('carrier_basis') for r in r['pack']['saved_review']])

    def test_rrf_uses_rank_not_raw_scores(self):
        a=[{'id':'a','score':-500},{'id':'b','score':-1}]
        b=[{'id':'b','score':.9},{'id':'c','score':.8}]
        self.assertEqual(retrieval.reciprocal_rank_fusion(a,b)[0]['id'],'b')

    def test_out_of_scope_and_unknown_names(self):
        for question in ['What is the salt of Ozempic?', 'Why does the FDA paper omit Gavreto?', 'Write a poem about Paris']:
            self.assertEqual(qa.prepare(question,self.products)['kind'],'clarification')

    def test_real_local_semantic_filter(self):
        import semantic
        if not semantic.available():self.skipTest('Semantic bundle not installed')
        vectors,ids,products=semantic.index()
        self.assertEqual(vectors.shape,(6348,384))
        name='EMEA/H/C/005755'
        hits=semantic.search('carrier in the dried dispersion',{name},8)
        self.assertTrue(hits)
        mapping=dict(zip(ids,products))
        self.assertTrue(all(mapping[h['id']]==name for h in hits))


if __name__=='__main__':unittest.main()
