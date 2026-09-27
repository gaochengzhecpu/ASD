from pathlib import Path
import json,re
import retrieval
from bundle import EVIDENCE_ROOT, ensure_bundle
ROOT=Path(__file__).resolve().parent
FIELD_LABELS={
 'chemical_name':'Chemical name','molecular_formula':'Molecular formula','molecular_weight':'Molecular weight',
 'acid_base':'Acid / base character','pka':'pKa','salt':'Salt / counterion','hydrate_solvate':'Hydrate / solvate',
 'ds_final_form':'Commercial DS solid form','solubility':'Solubility','bcs':'Reported BCS class',
 'dp_form':'Dosage form / release','strength':'Strength per unit','excipients':'DP excipients',
 'dp_process':'Commercial DP process','dose_regimen':'Dosing regimen (if in CMC)',
 'asd':'ASD classification','asd_carrier':'ASD carrier / polymer','asd_process':'ASD process',
 'drug_carrier_ratio':'API : carrier ratio','api_fraction_asd':'API fraction in ASD intermediate','api_fraction_dp':'API fraction in whole DP'}
GROUPS={'Drug substance':['chemical_name','molecular_formula','molecular_weight','acid_base','pka','salt','hydrate_solvate','ds_final_form','solubility','bcs'],
        'Drug product':['dp_form','strength','excipients','dp_process','dose_regimen'],
        'ASD & loading':['asd','asd_carrier','asd_process','drug_carrier_ratio','api_fraction_asd','api_fraction_dp']}
def load_json(name):
    ensure_bundle()
    return json.loads((EVIDENCE_ROOT/'data'/name).read_text(encoding='utf-8'))
def flat_value(v):
    if v is None:return 'Not reported / no value'
    if isinstance(v,bool):return 'Yes' if v else 'No'
    if isinstance(v,list):return '; '.join(flat_value(x) for x in v)
    if isinstance(v,dict):return '; '.join(k.replace('_',' ')+': '+flat_value(x) for k,x in v.items())
    return str(v)
def product_rows(products):
    return [{'Product':p['product'],'EMA ID':p['id'],'Active substance':p['metadata'].get('active_substance',''),
      'First authorisation':p['metadata'].get('first_approval_date',''),'Year':int(p['metadata']['first_approval_date'][:4]),
      'Company':p['metadata'].get('holder',''),'Original label':p['original_label'],'Working label':p['working_label'],
      'CMC availability':'Available' if p['fields'] else 'Unavailable','New since February':p['new_since_february']} for p in products]
def field_rows(products):
    return [{'Product':p['product'],'EMA ID':p['id'],'Entity':f.get('entity',''),'Field':FIELD_LABELS.get(f['key'],f['key']),
        'Value':flat_value(f['value']),'Status':f['status'],'Note':f.get('note',''),
        'CMC crop pages':'; '.join(str(e['page']) for e in f.get('evidence',[])),
        'Evidence quotations':'\n'.join(e.get('quote','') for e in f.get('evidence',[])),
        'EMA source':p['metadata']['ema_url']} for p in products for f in p['fields']]
def wide_rows(products):
    rows=product_rows(products)
    for row,p in zip(rows,products):
        for key,label in FIELD_LABELS.items():
            row[label]='\n'.join(f"{f.get('entity','')}: {flat_value(f['value'])} [{f['status']}]" for f in p['fields'] if f['key']==key)
    return rows
def safe_csv(df):
    result=df.copy()
    for col in result.columns:
        result[col]=result[col].map(lambda v:"'"+v if isinstance(v,str) and re.match(r'^\s*[=+@-]',v) else v)
    return result.to_csv(index=False).encode('utf-8-sig')
def citation(ident):
    if not re.fullmatch(r'\d{6}:(?:p\d+|f\d+|r1|meta)',ident):return None
    with retrieval.connect() as c:
        if ':p' in ident:
            row=c.execute('SELECT * FROM pages WHERE id=?',(ident,)).fetchone()
            return {**dict(row),'kind':'page'} if row else None
        if ':f' in ident:
            row=c.execute('SELECT * FROM facts WHERE id=?',(ident,)).fetchone()
            return {**retrieval.fact_out(row),'kind':'field'} if row else None
        row=c.execute('SELECT id,name,metadata,review,status FROM products WHERE id=?',('EMEA/H/C/'+ident.split(':')[0],)).fetchone()
        if not row:return None
        return {'kind':'review' if ident.endswith(':r1') else 'metadata','product_id':row['id'],
                'value':json.loads(row['review']) if ident.endswith(':r1') else {'name':row['name'],'metadata':json.loads(row['metadata']),'status':row['status']}}
