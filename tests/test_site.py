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

class UITests(unittest.TestCase):
    def setUp(self):self.a=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run();self.good()
    def good(self):self.assertEqual([e.message for e in self.a.exception],[])
    def route(self,section):self.a.radio(key='section').set_value(section).run();self.good()
    def select(self,label):return next(x for x in self.a.selectbox if x.label==label)
    def button(self,label):return next(x for x in self.a.button if x.label==label)
    def test_database_filter_empty_missing_and_images(self):
        self.button('Open CMC database').click().run();self.good()
        self.assertEqual(self.select('Inspect a product').value,'Palsonify')
        self.a.text_input(key='db_search').set_value('Etcamah').run();self.good()
        self.assertIn('Public CMC source unavailable',self.a.warning[0].value)
        self.a.text_input(key='db_search').set_value('absent[*').run();self.good()
        self.assertTrue(any('No matching' in x.value for x in self.a.info))
        self.a.text_input(key='db_search').set_value('').run();self.good()
        self.select('Inspect a product').set_value('Jinarc').run();self.good()
        self.assertEqual([m.value for m in self.a.metric],['Insufficient evidence','Likely ASD'])
        self.select('Inspect a product').set_value('Kygevvi').run();self.good()
    def test_search_catalog_examples(self):
        self.route('Evidence search');self.button('Retrieve evidence').click().run();self.good()
        self.assertTrue(any('Retrieved evidence' in h.value for h in self.a.subheader))
        self.a.radio(key='search_mode').set_value('Complete catalog').run();self.good()
        self.button('Scan complete catalog').click().run();self.good()
        self.assertTrue(any('14 products' in h.value for h in self.a.subheader))
        self.select('Evidence status').set_value('reported');self.button('Scan complete catalog').click().run();self.good()
        self.assertTrue(any('7 products' in h.value for h in self.a.subheader))
        next(x for x in self.a.text_input if 'after (exclusive' in x.label).set_value('bad-date')
        self.button('Scan complete catalog').click().run();self.good();self.assertTrue(self.a.error)
        self.a.radio(key='search_mode').set_value('Saved answer examples').run();self.good()
        self.assertTrue(any('not live' in x.value for x in self.a.info))
    def test_benchmark_and_navigation(self):
        self.route('Benchmark & validation');self.good()
        self.assertEqual(len(self.a.dataframe[0].value),3)
        self.route('Overview');self.assertEqual([m.value for m in self.a.metric],['351','350','39','259'])

if __name__=='__main__':unittest.main(verbosity=2)
