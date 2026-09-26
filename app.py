"""English CMC explorer. Retrieval only; no runtime model API."""
from collections import Counter
import pandas as pd
import plotly.express as px
import streamlit as st
import retrieval
from bundle import EVIDENCE_ROOT
from data_access import load_json, citation, safe_csv, FIELD_LABELS, GROUPS
from presentation import (assessment, rationale, basis, product_row, formulation_row,
    english_fields, english_value, entity_name, comparison_rows, field_text,
    OMISSIONS, FORMULATION, STATUS, CJK)

st.set_page_config(page_title='EMA Oral ASD Formulations',page_icon='💊',layout='wide')
st.markdown('''<style>
.block-container{max-width:1480px;padding-top:2.5rem;padding-bottom:3rem}
h1,h2,h3{letter-spacing:-.025em}
.hero{background:linear-gradient(115deg,#102b4b,#214e78 68%,#266d80);padding:28px 34px;border-radius:16px;color:white;margin-bottom:22px}
.hero h1{font-size:2.2rem;color:white!important;margin:6px 0 10px}
.hero p{color:#d6e4ef;margin:0;max-width:900px}
.eyebrow{font-size:.72rem;letter-spacing:.15em;text-transform:uppercase;font-weight:700;color:#a9dfce}
.stMetric{background:#f1f6fa;border:1px solid #dce6ee;border-radius:12px;padding:14px 20px}
[data-testid="stMetricValue"]{color:#153f65}
div[data-testid="stExpander"]{border-color:#dce6ee}
</style>''',unsafe_allow_html=True)

@st.cache_data
def dataset():return load_json('products.json'),load_json('benchmark.json')
products,benchmark=dataset()
by_name={p['product']:p for p in products};by_id={p['id']:p for p in products}
summary=pd.DataFrame([product_row(p) for p in products])
asd_products=[p for p in products if assessment(p)=='ASD']
asd_table=pd.DataFrame([formulation_row(p) for p in asd_products])

def table(rows,**kw):
    st.dataframe(rows if isinstance(rows,pd.DataFrame) else pd.DataFrame(rows),hide_index=True,width='stretch',**kw)

def csv_button(label,rows,filename,key):
    st.download_button(label,safe_csv(rows if isinstance(rows,pd.DataFrame) else pd.DataFrame(rows)),file_name=filename,mime='text/csv',key=key)

def field_source(p,f):
    value,origin=english_value(p,f)
    st.write(value);st.caption(STATUS.get(f['status'],f['status'])+(' · '+origin if origin else ''))
    note=f.get('note','')
    if note and not CJK.search(note):st.caption(note)
    for e in f.get('evidence',[]):
        st.text(e.get('quote',''))
        st.caption(f"CMC crop p. {e['page']}"+(f" · report p. {e['printed_page']}" if e.get('printed_page') else ''))
    if not f.get('evidence') and f.get('visual_evidence'):st.caption('Extracted from a CMC figure or table; no text quotation was attached.')

def source_page(ident):
    data=citation(ident)
    if not data or data['kind']!='page':st.info('Source page unavailable.');return
    p=by_id[data['product_id']]
    st.caption(f"{p['product']} · CMC crop page {data['page']}");st.text(data['text'])
    st.link_button('EMA source documents',p['metadata']['ema_url'])

def product_detail(p,prefix):
    name=p['product'];m=p['metadata']
    st.subheader(name)
    st.caption(f"{m.get('inn') or m.get('active_substance','')} · {m.get('holder','')} · First authorised {m['first_approval_date']}")
    st.markdown('**ASD assessment: '+assessment(p)+'**');st.write(rationale(p))
    if name in OMISSIONS:st.info('Potential literature omission: not in the paper-mapped ASD list. See Literature comparison for evidence and scope.')
    st.link_button('Official EMA product page',m['ema_url'])
    if not p['fields']:return
    tabs=st.tabs(['Drug product','Drug substance','ASD formulation','Structures','Source pages'])
    groups=[GROUPS['Drug product'],GROUPS['Drug substance'],[k for k in GROUPS['ASD & loading'] if k!='asd']]
    for tab,keys in zip(tabs,groups):
        with tab:
            fs=[f for f in p['fields'] if f['key'] in keys]
            rows=[]
            for f in fs:
                val,origin=english_value(p,f)
                rows.append({'Property':FIELD_LABELS[f['key']],'Component':entity_name(f.get('entity','')),'Value':val,'Wording':origin})
            table(rows)
            if keys==groups[-1] and name in FORMULATION:st.caption('Carrier: '+FORMULATION[name][0]+'. Preparation: '+FORMULATION[name][1]+'.')
            with st.expander('Evidence and source excerpts'):
                for f in fs:
                    ent=entity_name(f.get('entity',''))
                    st.markdown('**'+FIELD_LABELS[f['key']]+(' — '+ent if ent else '')+'**');field_source(p,f)
            st.caption('Source wording = original English excerpt. Strength is per unit; a QTPP development target is not a clinical dosing recommendation.')
    with tabs[3]:
        if not p['structures']:st.info('No structure image was extracted for this product.')
        cols=st.columns(2)
        for i,im in enumerate(p['structures']):
            with cols[i%2]:st.image(str(EVIDENCE_ROOT/im['file']),caption=f"{entity_name(im['entity']) or name} · CMC crop p. {im.get('page','?')}",width='content')
    with tabs[4]:
        with retrieval.connect() as c:pages=c.execute('SELECT id FROM pages WHERE product_id=? ORDER BY page',(p['id'],)).fetchall()
        if pages:source_page(st.selectbox('CMC page',[r['id'] for r in pages],format_func=lambda x:'Page '+x.split(':p')[-1],key=prefix+'_page'))
        st.caption('Assessment applies to the saved CMC formulation. First authorisation year is not the introduction date of every later formulation.')
    csv_button('Download product CMC fields',english_fields(p),name+'_CMC.csv',prefix+'_csv')

def asd_view():
    st.markdown('''<div class="hero"><div class="eyebrow">Public EMA evidence · Formulation science</div>
    <h1>EMA Oral ASD Formulations</h1><p>Amorphous solid dispersion formulations, their carriers, manufacturing processes and drug-product properties.</p></div>''',unsafe_allow_html=True)
    for col,label,value in zip(st.columns(3),['Products assessed as ASD','Oral products in the study','Products with CMC records'],[len(asd_products),len(products),sum(bool(p['fields']) for p in products)]):col.metric(label,value)
    st.caption('January 2010–20 September 2026 · Selected centrally authorised oral products; generics, biosimilars and hybrids excluded. ASD counts are review assessments, including interpretations.')
    a,b=st.columns([2,1]);term=a.text_input('Search ASD product, ingredient, carrier or company',key='asd_search')
    view=b.selectbox('Show',['Formulation summary','Manufacturing & excipients','Drug loading'],key='asd_view')
    subset=asd_table.copy()
    if term:subset=subset[subset.astype(str).apply(lambda s:s.str.contains(term,case=False,regex=False)).any(axis=1)]
    cols={'Formulation summary':['Product','Active ingredient','Year','Dosage form','Strength','ASD carrier','ASD preparation','Literature note'],
          'Manufacturing & excipients':['Product','Dosage form','DP manufacturing','Excipients'],
          'Drug loading':['Product','ASD carrier','API : carrier ratio','API fraction in ASD','API fraction in DP']}[view]
    st.subheader('ASD drug-product database');st.caption(f'{len(subset)} products · Candidate carriers are explicitly marked. Undisclosed values remain unfilled.')
    table(subset[cols],height=420);csv_button('Download all ASD formulation columns',subset,'EMA_ASD_formulations.csv','asd_csv')
    if not subset.empty:product_detail(by_name[st.selectbox('Inspect an ASD product',sorted(subset['Product']),key='asd_product')],'asd_detail')
    with st.expander('ASD products by first authorisation year'):
        counts=asd_table.groupby('Year').size().reset_index(name='Products')
        fig=px.bar(counts,x='Year',y='Products',color_discrete_sequence=['#245d89'])
        fig.update_layout(height=310,margin=dict(t=10,l=10,b=10,r=10),plot_bgcolor='rgba(0,0,0,0)');st.plotly_chart(fig,width='stretch')

def all_medicines():
    st.title('All medicines');st.write('One assessment per product, with its CMC properties and source documents.')
    a,b=st.columns([2,1]);term=a.text_input('Search product, ingredient or company',key='db_search')
    status=b.selectbox('ASD assessment',['All','ASD','Non-ASD','Insufficient evidence'],key='db_status')
    subset=summary.copy()
    if term:subset=subset[subset[['Product','Active ingredient','Company']].astype(str).apply(lambda s:s.str.contains(term,case=False,regex=False)).any(axis=1)]
    if status!='All':subset=subset[subset['ASD assessment']==status]
    st.caption(f'{len(subset)} of {len(products)} products');table(subset,height=350)
    csv_button('Download product assessments',subset,'EMA_product_assessments.csv','all_summary')
    chosen=[by_name[n] for n in subset['Product']]
    with st.expander('Export structured CMC data'):
        group=st.selectbox('Properties',['All properties','Drug substance','Drug product','ASD & loading'],key='export_group')
        keys=[k for k in (list(FIELD_LABELS) if group=='All properties' else GROUPS[group]) if k!='asd']
        rows=[{**product_row(p),**{FIELD_LABELS[k]:field_text(p,k) for k in keys}} for p in chosen]
        csv_button('Download one row per product',rows,'EMA_CMC_wide.csv','all_wide')
        csv_button('Download fields with evidence',[r for p in chosen for r in english_fields(p)],'EMA_CMC_evidence.csv','all_fields')
    if subset.empty:st.info('No matching products. Clear or broaden the filters.');return
    product_detail(by_name[st.selectbox('Inspect a product',sorted(subset['Product']),key='all_product')],'all_detail')

def matching_field(p,f):
    matches=[x for x in p['fields'] if x['key']==f['key'] and x.get('entity','')==f.get('entity','')]
    return matches[0] if matches else f

def evidence_search():
    st.title('CMC evidence search');st.write('Find formulation facts and the CMC passages that support them.')
    st.caption('The retrieval component of the RAG workflow. This website searches saved evidence; it does not generate new AI answers or call a paid model API.')
    mode=st.radio('Search mode',['Question search','Complete catalog','Worked examples'],horizontal=True,key='search_mode')
    if mode=='Worked examples':
        examples={
          'Sotyktu — ASD carrier and process':('Sotyktu','HPMCAS H grade is reported. API and polymer are dissolved in acetone/water, then spray-dried.'),
          'Palsonify — crystalline DS and ASD product':('Palsonify','Crystalline input DS and an amorphous spray-dried product describe different manufacturing stages. The saved CMC supports an ASD product.'),
          'Palsonify — missing pKa':('Palsonify','No numerical pKa is disclosed in the saved CMC record. It must remain not reported.'),
          'Rhapsido — spray processing is not sufficient':('Rhapsido','The source describes retained crystalline Form A and a nanosuspension route. Copovidone and spray granulation alone do not establish an ASD.'),
          'Xtandi — formulation mismatch':('Xtandi','The reviewed document covers the earlier liquid-filled capsule. The later ASD tablet cannot be assessed from that record.')}
        label=st.selectbox('Example',list(examples));name,answer=examples[label]
        st.info('Saved answer example, not a live model response.');st.write(answer)
        p=by_name[name];keys=['pka'] if 'pKa' in label else ['dp_form','asd','asd_carrier','asd_process']
        with st.expander('Supporting CMC excerpts'):
            for f in p['fields']:
                if f['key'] in keys:field_source(p,f)
        return
    if mode=='Complete catalog':
        with st.form('catalog_form'):
            a,b,c=st.columns(3);keys=[k for k in FIELD_LABELS if k!='asd']
            key=a.selectbox('Property',keys,index=keys.index('asd_carrier'),format_func=lambda k:FIELD_LABELS[k])
            concept=b.selectbox('Match',['HPMCAS synonyms','Spray-drying synonyms','Literal text'])
            status=c.selectbox('Evidence',['Any','reported','partly_reported','interpretation'])
            text=st.text_input('Search text (for literal matching)');go=st.form_submit_button('Search complete catalog',type='primary')
        if go:
            args={'field':key,'status':None if status=='Any' else status}
            if concept=='HPMCAS synonyms':args['concept']='hpmcas'
            elif concept=='Spray-drying synonyms':args['concept']='spray_drying'
            else:args['contains']=text or None
            st.session_state['catalog']=retrieval.catalog(**args)
        result=st.session_state.get('catalog')
        if result:
            st.subheader(f"{result['products']} matching products")
            st.caption('Matches to saved fields, not automatic confirmation that a listed polymer is the ASD carrier.')
            rows=[]
            for r in result['results']:
                p=by_name[r['name']];f=matching_field(p,r);val,_=english_value(p,f)
                rows.append({'Product':p['product'],'Component':entity_name(f.get('entity','')),'Value':val,'Evidence':STATUS.get(r['status'],r['status'])})
            table(rows);csv_button('Download matches',rows,'CMC_catalog.csv','catalog_csv')
        return
    with st.form('search'):
        question=st.text_input('Question',value='What are the ASD carrier and manufacturing process of Sotyktu?')
        name=st.selectbox('Product (optional)',['Automatic']+sorted(by_name));go=st.form_submit_button('Find evidence',type='primary')
    if go:st.session_state['search_result']=retrieval.query(question,product=None if name=='Automatic' else name)
    result=st.session_state.get('search_result')
    if not result:return
    st.subheader('Retrieved evidence');st.caption(result['question'])
    for p in result['target_products']:
        record=by_name[p['product']];st.markdown('**'+p['product']+' — '+assessment(record)+'**');st.write(rationale(record))
    for warning in result['warnings']:
        if 'separate saved-record interpretation' not in warning:st.info(warning.replace('catalog --after / --before','explicit date filters in an offline catalog analysis'))
    a,b=st.columns([1,1.2])
    with a:
        st.markdown('**Extracted properties**')
        for f in result['facts']:
            if f['key']=='asd':continue
            p=by_id[f['product_id']];field=matching_field(p,f)
            with st.expander(p['product']+' · '+FIELD_LABELS[f['key']],expanded=f['key'] in ['asd_carrier','asd_process']):field_source(p,field)
    with b:
        st.markdown('**CMC source passages**')
        for i,ctx in enumerate(result['contexts']):
            with st.expander(f"{ctx['product']} · CMC page {ctx['crop_page']}",expanded=i==0):
                st.text(ctx['text']);st.caption('Citation: '+ctx['citation'])
                st.link_button('Official EMA source',by_name[ctx['product']]['metadata']['ema_url'])

def literature_view():
    st.title('Literature comparison');st.write('How our formulation review compares with the published FDA ASD list.')
    st.link_button('Moseson et al. (2024), including Tze Ning Hiew','https://doi.org/10.1016/j.ijpx.2024.100259')
    st.markdown('''**Comparison set:** 259 EMA products whose matched oral formulations were also FDA-approved in 2012–2023, the period covered by the paper. Matching uses formulation rather than brand name or indication.

The paper lists ASD formulations. **Not listed does not prove non-ASD.** Unlisted products were initially treated as negative to compare screening methods; the review below separates possible reference omissions and different formulations.''')
    rows=comparison_rows(products,benchmark);frame=pd.DataFrame(rows);counts=Counter(r['Comparison'] for r in rows)
    for col,label,n in zip(st.columns(3),['ASD in both','Potential literature omissions','Different formulations'],[counts['ASD in both'],counts['Potential literature omission'],counts['Different formulation reviewed']]):col.metric(label,n)
    st.caption('29 EMA product/formulation matches to the paper ASD list: 27 agree with our review; 2 involve different formulations. Of 230 unlisted products, 5 are assessed as ASD, 220 as non-ASD and 5 remain unresolved. Vaxchora and Palforzia are included in the overlap but are outside the paper’s NDA scope.')
    st.subheader('Five potential literature omissions')
    st.write('ASD in the saved CMC evidence, but absent from the paper-mapped list. Literature-scope checking is still needed before calling these confirmed omissions.')
    evidence=[]
    for name in OMISSIONS:
        p=by_name[name];quotes=list(dict.fromkeys(e['quote'] for f in p['fields'] if f['key']=='asd' for e in f.get('evidence',[])))
        evidence.append({'Product':name,'Our assessment':'ASD','Paper ASD list':'Not listed','CMC evidence':' / '.join(quotes),'Basis':basis(p)})
    table(evidence)
    st.caption('Against the uncorrected paper labels these appear as our method’s false positives (FP). If independently verified as omissions, they are reference-label errors, not method false positives.')
    st.subheader('Two formulation mismatches')
    table([{'Product':'Xtandi','Reviewed CMC formulation':'Liquid-filled soft capsule','Paper-mapped ASD formulation':'Later tablet'},
           {'Product':'Lynparza','Reviewed CMC formulation':'Crystalline solid-dispersion capsule','Paper-mapped ASD formulation':'Later tablet'}])
    st.caption('Raw label comparison counts these as false negatives (FN). The earlier capsule evidence cannot determine the later tablet formulation; they are therefore shown separately.')
    with st.expander('All 259 product comparisons'):
        group=st.selectbox('Comparison category',['All']+sorted(counts),key='comparison_group')
        table(frame if group=='All' else frame[frame['Comparison']==group]);csv_button('Download comparison',frame,'EMA_literature_comparison.csv','compare_csv')
    with st.expander('Historical V1 / V2 / V3 screening results'):
        st.write('Original screening runs, before consolidation of the CMC review. TP/FP/FN/TN use the original paper labels and assume all unlisted products negative.')
        labels={'v1':'V1: basic keywords','v2':'V2: DP-only rules','v3':'V3: saved Gemini review'}
        table([{'Method':labels[m['name']],**{k:m[k] for k in ['TP','FP','FN','TN']},'Unresolved':259-m['explicit']} for m in benchmark['methods']])
        for m in benchmark['methods']:
            st.markdown('**'+labels[m['name']]+'**');st.write('FN: '+', '.join(m['missed']))
            st.write('FP: '+', '.join(r['product'] for r in m['identified'] if r['outcome']=='FP'))
            if m['unknown']:st.write('Unresolved: '+', '.join(m['unknown']))
        st.caption('Different document scopes and historical inputs make this an exploratory comparison, not a controlled model ranking. The current review also saw the literature comparison and is not a blind test.')

def about():
    st.title('About this project')
    st.markdown('''### Data and assessment
EMA medicines records and Article 57 route information define the selected oral cohort. EPAR CMC sections provide the formulation evidence. This release contains 351 products and 350 CMC records, with a source snapshot of 20 September 2026.

The site consolidates the completed Codex review into one product assessment: **ASD**, **Non-ASD** or **Insufficient evidence**. ASD covers a drug dispersed in an organic carrier matrix in amorphous form, including solid solutions and cyclodextrin-based dispersions. Amorphous silica adsorbates are outside this category. A pure amorphous API or a polymer excipient alone is not sufficient.

The 39 ASD assessments include interpretations of the manufacturing record; they are not 39 independently confirmed experimental findings. Carrier identity, process and drug loading remain undisclosed where the record does not establish them. Combination products can contain both ASD and non-ASD components. Approval year refers to the first product authorisation, not every formulation change.

### English presentation
English extracted values are retained, with concise English summaries for the ASD table. Where an extraction was written in Chinese, its original English CMC quotation is displayed and marked **Source wording**, rather than silently translating or guessing. These excerpts can be less complete than the original narrative. Original records remain in the project archive.

### Evidence search and RAG
BM25 text retrieval is combined with product and property matching. Codex was used outside the public website to answer questions from retrieved evidence. The website provides the retrieval step and worked examples; it has no live model-generation backend and makes no model API calls.

Development used 24 regression questions and 4 stress cases. Required-field coverage improved from 20/24 to 24/24. This measures retrieval coverage, not scientific answer accuracy. Independent held-out evaluation remains necessary.

### Acknowledgements
Thank you to my wife, **Xiuli Li**, for her support; my friends **Tianyi Li, Yongjian Wang, Fan Meng and Zoe Wen** for brainstorming; and my manager **Fady Ibrahim** for his encouragement. Thank you to my PhD advisor **Kevin J. Edgar**, my postdoctoral advisor **Lynne Taylor**, and my mentor **Tze Ning Hiew** for inspiring my work on amorphous solid dispersions.

### Project history
Earlier website versions are available in GitHub’s commit history. Their counts and methods may differ from this release.''')
    st.link_button('GitHub version history','https://github.com/gaochengzhecpu/ASD/commits/main/')
    st.caption('Independent research by Chengzhe Gao using public regulatory evidence. Not an EMA service or clinical dosing resource.')

sections={'ASD formulations':asd_view,'All medicines':all_medicines,'CMC evidence search':evidence_search,'Literature comparison':literature_view,'About':about}
if st.session_state.get('section') not in sections:st.session_state['section']='ASD formulations'
st.radio('Explore',list(sections),horizontal=True,key='section',label_visibility='collapsed')
sections[st.session_state['section']]()
st.divider();st.caption('Chengzhe Gao · Public EMA CMC evidence · Data snapshot: 20 September 2026')
