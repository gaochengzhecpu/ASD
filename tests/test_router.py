"""Contract, execution and adversarial regressions for model-selected read-only tools."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import catalogue
import generation
import qa
import retrieval
import router
from data_access import load_json


def decision(**changes):
    return dict({'route':'database','operation':'count','normalized_question':'How many products are salts?',
                 'filters':{'salt':'Salt'},'start':None,'end':None,'reported_only':False,
                 'product_names':[],'fields':[],'corrections':[],
                 'unsupported_conditions':[],'clarification':''},**changes)


class RouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.products=load_json('products.json')

    def test_pasted_number_and_paraphrases_execute_model_plan_not_old_parser(self):
        for q in ('How many products are salts? 2.','how meny meds are salt forms pls','多少个口服药是 salt 呀？'):
            with (patch.object(catalogue,'plan_question',side_effect=AssertionError('legacy parser used')),
                  patch.object(retrieval,'query',side_effect=AssertionError('retrieval used for total'))):
                result=qa.prepare_routed(q,self.products,decision())
            self.assertEqual(result['kind'],'catalogue')
            self.assertEqual((len(result['matched']),result['denominator'],len(result['uncertain'])),(146,351,18))
            self.assertEqual(result['question'],q)

    def test_numeric_class_and_date_constraints_are_applied(self):
        d=decision(filters={'bcs':'2'},start='2020-01-01',end='2025-12-31')
        r=qa.prepare_routed('BCS 2 between 2020 and 2025',self.products,d)
        self.assertTrue(r['matched'])
        self.assertTrue(all('2020-01-01'<=x['First authorisation']<='2025-12-31' for x in r['matched']))
        self.assertEqual(r['plan']['filters'],{'bcs':'2'})
        d=decision(operation='percentage')
        self.assertIn('41.6%',qa.prepare_routed('What fraction are salts?',self.products,d)['answer'])

    def test_misspelt_product_lookup_and_missing_pka(self):
        d=decision(operation='lookup',filters={},product_names=['Palsonify'],fields=['pka'],
                   normalized_question='What is the pKa of Palsonify?',corrections=['Interpreted Palsonfy as Palsonify.'])
        with patch.object(retrieval,'query') as search,patch.object(generation,'provider_answer') as answer:
            r=qa.prepare_routed('pka of palsonfy?',self.products,d)
        self.assertEqual(r['kind'],'direct');self.assertIn('Not reported',r['answer']);self.assertIn('006636:f5',r['answer'])
        search.assert_not_called();answer.assert_not_called()
        self.assertIn('Palsonfy',r['routing']['corrections'][0])

    def test_lookup_current_carrier_preserves_inference(self):
        d=decision(operation='lookup',filters={},product_names=['Gavreto'],fields=['asd_carrier'])
        r=qa.prepare_routed('Gavreto polymer?',self.products,d)
        self.assertIn('HPMC',r['answer']);self.assertIn('Inferred',r['answer'])
        self.assertTrue(all(x['kind']=='Saved review interpretation' for x in r['records']))

    def test_combination_lookup_keeps_api_components_separate(self):
        d=decision(operation='lookup',filters={},product_names=['Kaftrio'],fields=['salt'])
        r=qa.prepare_routed('What are the salt forms in Kaftrio?',self.products,d)
        components={record['component'] for record in r['records']}
        self.assertEqual(len(components),3)
        self.assertTrue(all(component in r['answer'] for component in components))

    def test_rag_comparison_uses_only_selected_products(self):
        d=decision(route='rag',operation='compare',filters={},product_names=['Sotyktu','Zelboraf'],
                   fields=['asd_carrier','asd_process'],normalized_question='Compare the ASD carriers and manufacturing processes of Sotyktu and Zelboraf.')
        r=qa.prepare_routed('compare sotyktu vs zelboraf polymer and how made',self.products,d,method='bm25')
        self.assertEqual(r['kind'],'evidence')
        self.assertEqual({p['product'] for p in r['pack']['source_passages']},{'Sotyktu','Zelboraf'})
        self.assertIn('005755:p6',{p['id'] for p in r['pack']['source_passages']})

    def test_unsupported_conditions_do_not_turn_into_broad_counts(self):
        invalid=[decision(filters={'salt':'Salt','indication':'oncology'}),
                 decision(unsupported_conditions=['FDA approval']),decision(filters={'salt':"Salt';DROP TABLE facts;--"}),
                 decision(start='2025-99-99'),decision(start='2026-01-01',end='2025-01-01'),
                 decision(product_names=['Imaginarydrug']),decision(reported_only='false'),
                 decision(route='rag',operation='count',filters={}),decision(sql='select * from products')]
        for d in invalid:
            with self.assertRaises(generation.AnswerError):qa.prepare_routed('question',self.products,d)
        d=decision(route='clarify',filters={},unsupported_conditions=['FDA approval'],
                   clarification='FDA approval needs the Literature comparison section.')
        r=qa.prepare_routed('How many FDA-approved salts?',self.products,d)
        self.assertEqual(r['kind'],'clarification');self.assertNotIn('matched',r)

    def test_unknown_field_and_freeform_provider_output_rejected(self):
        with self.assertRaises(generation.AnswerError):router.validate(decision(operation='lookup',filters={},product_names=['Sotyktu'],fields=['secrets']),self.products)
        for content in ('Here is some Python: print(42)','{"sql":"DROP TABLE products"}',None):
            response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':content}}]}).encode()
            with patch.object(generation,'urlopen',return_value=response):
                with self.assertRaises(generation.AnswerError):router.provider_route('Count salts',self.products,None,'test-key','session')

    def test_model_cannot_insert_remote_images_in_clarifications(self):
        d=decision(route='clarify',clarification='![x](https://example.com/collect)',filters={})
        with self.assertRaises(generation.AnswerError):router.validate(d,self.products)

    def test_no_model_request_without_key_and_shared_budget_applies(self):
        service=generation.AnswerService()
        with patch.object(router,'provider_route') as send:
            with self.assertRaises(generation.AnswerError):service.route('Count salts',self.products,None,'','s')
            service.calls.extend([generation.time.time()]*30)
            with self.assertRaisesRegex(generation.AnswerError,'demo answer limit'):
                service.route('Count salts',self.products,None,'test-key','s')
            send.assert_not_called()

    def test_route_request_contains_only_catalog_metadata_not_cmc_passages(self):
        response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(decision())}}]}).encode()
        with patch.object(generation,'urlopen',return_value=response) as send:
            r=router.provider_route('How many products are salts? 2.',self.products,None,'test-key','session')
        self.assertEqual(r['decision']['route'],'database')
        body=json.loads(send.call_args.args[0].data)
        context=json.loads(body['messages'][1]['content'])
        self.assertEqual(len(context['public_products']),351)
        self.assertNotIn('source_passages',context);self.assertNotIn('test-key',json.dumps(context))

    def test_routing_and_generation_share_limits_but_allow_same_turn(self):
        service=generation.AnswerService()
        routed={'decision':decision(),'cached':False}
        pack={'question':'Explain','source_passages':[{'id':'005755:p6','text':'public text'}]}
        with patch.object(router,'provider_route',return_value=routed) as plan,patch.object(generation,'provider_answer',return_value={'answer':'Cited answer','cached':False}) as answer:
            service.route('Count salts',self.products,None,'test-key','s')
            self.assertTrue(service.route('Count salts',self.products,None,'test-key','s')['cached'])
            service.answer(pack,'test-key','s',routed=True)
            self.assertEqual(len(service.calls),2);self.assertEqual(plan.call_count,1);self.assertEqual(answer.call_count,1)


if __name__=='__main__':unittest.main()
