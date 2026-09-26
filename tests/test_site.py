"""Data integrity, query boundaries and real Streamlit interaction regressions."""
from pathlib import Path
import sys,json,sqlite3,unittest
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import retrieval
from bundle import EVIDENCE_ROOT
from data_access import load_json,citation,field_rows,safe_csv
import pandas as pd
from streamlit.testing.v1 import AppTest
from presentation import (assessment, english_fields, formulation_row, comparison_rows,
    product_row, english_value, OMISSIONS, CJK, carrier_review)

class DataTests(unittest.TestCase):
    def test_cohort_and_labels(self):
        p=load_json('products.json');m=load_json('manifest.json')
        self.assertEqual(len(p),351);self.assertEqual(len({x['id'] for x in p}),351)
        self.assertEqual(sum(bool(x['fields']) for x in p),350)
        self.assertEqual(Counter(x['working_label'] for x in p),m['working_labels'])
        self.assertEqual(m['working_labels']['ASD']+m['working_labels']['Likely ASD'],39)
        self.assertEqual(sum(len(x['fields']) for x in p),9254)
        self.assertEqual(len(field_rows(p)),9254)
        self.assertEqual(sum(x['new_since_february'] for x in p),14)
        for x in p:
            if x['working_label']=='Likely ASD':self.assertEqual(x['original_label'],'Insufficient evidence')
    def test_assets_and_public_package(self):
        p=load_json('products.json');images=[im for x in p for im in x['structures']]
        self.assertEqual(len(images),435)
        for im in images:self.assertTrue((EVIDENCE_ROOT/im['file']).is_file(),im)
        for file in (EVIDENCE_ROOT/'data').glob('*.json'):
            text=file.read_text(encoding='utf-8')
            self.assertNotIn('C:\\',text);self.assertNotIn('C:/Users',text)
        with retrieval.connect() as c:
            for table in ['products','facts','pages','chunks']:
                for row in c.execute('SELECT * FROM '+table):
                    self.assertNotIn('C:\\Users',str(tuple(row)))
                    self.assertNotIn('C:/Users',str(tuple(row)))
    def test_all_field_quotes_resolve(self):
        with retrieval.connect() as c:
            pages={r['id']:r['text'] for r in c.execute('SELECT id,text FROM pages')}
            self.assertEqual(len(pages),2434)
            for f in c.execute('SELECT evidence FROM facts'):
                for e in json.loads(f['evidence']):
                    self.assertIn(e['page_id'],pages)
                    self.assertIn(retrieval.norm(e['quote']),retrieval.norm(pages[e['page_id']]))
    def test_benchmark_counts(self):
        b=load_json('benchmark.json');self.assertEqual(len(b['rows']),259)
        self.assertEqual(sum(r['reference_binary']==1 for r in b['rows']),29)
        for m in b['methods']:
            counts=Counter(r[m['name']+'_result'] for r in b['rows'])
            for outcome in ['TP','FP','FN','TN']:self.assertEqual(counts[outcome],m[outcome])
            self.assertEqual(sum(m[k] for k in ['TP','FP','FN','TN'])+len(m['unknown']),259)
    def test_regression_evidence(self):
        e=load_json('evaluation.json');self.assertEqual(len(e['regression']),24);self.assertEqual(len(e['stress']),4)
        for case in e['regression']:
            bundle=retrieval.query(case['question'])
            self.assertEqual(sorted(p['product'] for p in bundle['target_products']),sorted(case['products']),case['id'])
            self.assertTrue(set(case['fields']).issubset({f['key'] for f in bundle['facts']}),case['id'])
            for ident in case['citations']:self.assertIsNotNone(citation(ident),ident)
    def test_catalog_dates_and_exactness(self):
        self.assertEqual(retrieval.catalog('asd_carrier',concept='hpmcas')['products'],14)
        self.assertEqual(retrieval.catalog('asd_carrier',concept='hpmcas',status='reported')['products'],7)
        exact=retrieval.catalog('asd',equals='ASD')
        self.assertEqual(exact['products'],28)
        self.assertTrue(all(r['value']=='ASD' for r in exact['results']))
        new=retrieval.catalog('asd_process',concept='spray_drying',after='2026-02-28')
        self.assertEqual({r['name'] for r in new['results']},{'Palsonify'})
        with self.assertRaises(ValueError):retrieval.catalog('asd',after='not-a-date')
        with self.assertRaises(ValueError):retrieval.catalog('DROP TABLE facts')
        self.assertIsNone(citation('../../secrets'))
    def test_missing_and_unknown_do_not_become_positive(self):
        missing=retrieval.query('Etcamah ASD polymer')
        self.assertEqual(missing['facts'],[]);self.assertEqual(missing['contexts'],[])
        unknown=retrieval.query('Qwertyzumab ASD carrier')
        self.assertEqual(unknown['target_products'],[]);self.assertTrue(unknown['warnings'])
        typo=retrieval.query('Palsonfy pKa')
        self.assertIn('Palsonify',typo['product_suggestions']);self.assertEqual(typo['target_products'],[])
        text=safe_csv(pd.DataFrame({'value':['=1+1','plain']})).decode('utf-8-sig')
        self.assertIn("'=1+1",text)

class PresentationTests(unittest.TestCase):
    def test_all_public_values_are_english_and_traceable(self):
        ps=load_json('products.json')
        for p in ps:
            self.assertIsNone(CJK.search(str(product_row(p))))
            self.assertIsNone(CJK.search(str(english_fields(p))),p['product'])
            for f in p['fields']:
                value,origin=english_value(p,f)
                self.assertIsNone(CJK.search(value),p['product'])
                if origin=='Source wording':
                    self.assertTrue(all(e['quote'].strip() in value for e in f['evidence'] if e['quote'].strip()))
        self.assertEqual(Counter(assessment(p) for p in ps),{'ASD':39,'Non-ASD':303,'Insufficient evidence':9})
        self.assertEqual(assessment(next(p for p in ps if p['product']=='Evotaz')),'Insufficient evidence')
        rows=[formulation_row(p) for p in ps if assessment(p)=='ASD']
        self.assertEqual(len(rows),39);self.assertIsNone(CJK.search(str(rows)))
        self.assertTrue(all('DP manufacturing' in r and 'Excipients' in r for r in rows))
    def test_carrier_interpretations_preserve_source_uncertainty(self):
        ps={p['product']:p for p in load_json('products.json')}
        for name in ['Maviret','Braftovi','Kaftrio','Gavreto','Sunlenca','Tibsovo','Palsonify']:
            review=carrier_review(ps[name])
            self.assertEqual(review['Carrier basis'],'Inferred')
            self.assertTrue(review['Carrier source excerpts'])
            self.assertTrue(review['Carrier CMC pages'])
            self.assertNotIn('Not disclosed',review['ASD carrier'])
        self.assertEqual(carrier_review(ps['Gavreto'])['ASD carrier'],'HPMC')
        self.assertTrue(all(f['value'] is None for f in ps['Gavreto']['fields'] if f['key']=='asd_carrier'))
        self.assertNotIn('poloxamer',carrier_review(ps['Sunlenca'])['ASD carrier'].lower())
        self.assertIn('second co-sprayed excipient is not identified',carrier_review(ps['Sunlenca'])['Carrier rationale'])
        self.assertIn('assignments remain unresolved',carrier_review(ps['Kaftrio'])['Carrier rationale'])
        self.assertEqual(carrier_review(ps['Sotyktu'])['Carrier basis'],'Reported')

    def test_reference_disagreements_are_not_silently_relabelled(self):
        rows=comparison_rows(load_json('products.json'),load_json('benchmark.json'))
        counts=Counter(r['Comparison'] for r in rows)
        self.assertEqual(counts,{'ASD in both':27,'Potential literature omission':5,
            'Different formulation reviewed':2,'CMC evidence unresolved':6,'Not listed; review non-ASD':219})
        self.assertEqual({r['Product'] for r in rows if r['Comparison']=='Potential literature omission'},set(OMISSIONS))
        self.assertEqual({r['Product'] for r in rows if r['Comparison']=='Different formulation reviewed'},{'Xtandi','Lynparza'})

class UITests(unittest.TestCase):
    def setUp(self):self.a=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run();self.good()
    def good(self):self.assertEqual([e.message for e in self.a.exception],[])
    def route(self,section):self.a.radio(key='section').set_value(section).run();self.good()
    def select(self,label):return next(x for x in self.a.selectbox if x.label==label)
    def button(self,label):return next(x for x in self.a.button if x.label==label)
    def test_database_filter_empty_missing_and_images(self):
        self.route('Oral product database')
        self.a.text_input(key='db_search').set_value('Etcamah').run();self.good()
        self.assertTrue(any('No public CMC source' in x.value for x in self.a.markdown))
        self.a.text_input(key='db_search').set_value('absent[*').run();self.good()
        self.assertTrue(any('No matching' in x.value for x in self.a.info))
        self.a.text_input(key='db_search').set_value('').run();self.good()
        self.select('Inspect a product').set_value('Jinarc').run();self.good()
        self.assertTrue(any('ASD assessment: ASD' in x.value for x in self.a.markdown))
        self.select('Inspect a product').set_value('Kygevvi').run();self.good()
    def test_search_catalog_examples(self):
        self.route('CMC evidence search');self.button('Find evidence').click().run();self.good()
        self.assertTrue(any('Retrieved evidence' in h.value for h in self.a.subheader))
        self.a.radio(key='search_mode').set_value('Complete catalog').run();self.good()
        self.button('Search complete catalog').click().run();self.good()
        self.assertTrue(any('14 matching' in h.value for h in self.a.subheader))
        self.select('Evidence').set_value('reported');self.button('Search complete catalog').click().run();self.good()
        self.assertTrue(any('7 matching' in h.value for h in self.a.subheader))
        self.a.radio(key='search_mode').set_value('Worked examples').run();self.good()
        self.assertTrue(any('not a live' in x.value for x in self.a.info))
    def test_benchmark_and_navigation(self):
        self.route('Literature comparison')
        self.assertEqual([m.value for m in self.a.metric],['27','5','2'])
        self.assertEqual(len(self.a.dataframe[0].value),5)
        self.route('ASD formulations');self.assertEqual([m.value for m in self.a.metric],['39','351','350'])
        self.assertEqual(len(self.a.dataframe[0].value),39)
        self.select('Show').set_value('Manufacturing & excipients').run();self.good()
        self.assertIn('DP manufacturing',self.a.dataframe[0].value.columns)
        self.route('About')
        self.assertTrue(any('Xiuli Li' in x.value for x in self.a.markdown))
    def test_english_ui_and_removed_sections(self):
        for section in ['ASD formulations','Oral product database','CMC evidence search','Literature comparison','About']:
            self.route(section)
            for elements in [self.a.markdown,self.a.caption,self.a.text,self.a.info,self.a.warning]:
                for element in elements:self.assertIsNone(CJK.search(element.value),section)
            for frame in self.a.dataframe:self.assertIsNone(CJK.search(frame.value.to_csv(index=False)),section)
        text=(ROOT/'app.py').read_text(encoding='utf8')
        for phrase in ['14 products added','What changed from','Original extraction label','Working classification','### English presentation']:
            self.assertNotIn(phrase,text)

if __name__=='__main__':unittest.main(verbosity=2)
