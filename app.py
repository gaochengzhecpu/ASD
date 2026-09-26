"""Public EPAR / CMC evidence explorer. No runtime model or embedding API calls."""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import streamlit as st
import retrieval
from bundle import EVIDENCE_ROOT
from data_access import load_json, product_rows, field_rows, wide_rows, flat_value, citation, safe_csv, FIELD_LABELS, GROUPS

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='EMA ASD & CMC Evidence',page_icon='💊',layout='wide')
st.markdown('''<style>
.block-container{max-width:1480px;padding-top:2.5rem;padding-bottom:4rem}
h1,h2,h3{letter-spacing:-.03em}h1{font-weight:750!important}
.hero{background:linear-gradient(115deg,#102b4b,#214e78 68%,#266d80);padding:30px 36px;border-radius:18px;color:white;margin-bottom:24px}
.hero h1{font-size:2.3rem;margin:5px 0 12px;color:white!important;line-height:1.15}
.hero p{color:#d6e4ef;margin:0;max-width:850px;font-size:1rem}
.eyebrow{font-size:.73rem;letter-spacing:.16em;text-transform:uppercase;font-weight:700;color:#a9dfce;margin-bottom:12px}
.hero-meta{margin-top:18px;font-size:.78rem;color:#c6d9e8}
.stMetric{background:#f1f6fa;border:1px solid #dce6ee;border-radius:12px;padding:15px 20px}
[data-testid="stMetricValue"]{color:#153f65}
div[data-testid="stExpander"]{border-color:#dce6ee}
div[data-testid="stAlert"]{border-radius:10px}
</style>''',unsafe_allow_html=True)

@st.cache_data
def dataset():return load_json('products.json'),load_json('manifest.json'),load_json('benchmark.json'),load_json('evaluation.json')
products,manifest,benchmark,evaluation=dataset()
by_id={p['id']:p for p in products};by_name={p['product']:p for p in products}
df=pd.DataFrame(product_rows(products))

def download_csv(label,rows,name,key):
    table=rows if isinstance(rows,pd.DataFrame) else pd.DataFrame(rows)
    st.download_button(label,safe_csv(table),file_name=name,mime='text/csv',key=key)
def download_json(label,obj,name,key):
    st.download_button(label,json.dumps(obj,ensure_ascii=False,indent=2).encode('utf-8'),file_name=name,mime='application/json',key=key)
def jump(page,product=None):
    st.session_state['section']=page
    if product:
        st.session_state['detail_product']=product
        st.session_state['db_search']=''
        st.session_state['db_labels']=[]
        st.session_state['db_period']='All 351 products'

def source_panel(ident):
    data=citation(ident)
    if not data:st.warning('Source identifier unavailable in this snapshot.');return
    p=by_id[data['product_id']]
    st.caption(f"{p['product']} · {ident}")
    st.markdown('[Official EMA product page]('+p['metadata']['ema_url']+')')
    if data['kind']=='page':
        st.caption(f"CMC crop page {data['page']} · {data['source']}");st.text(data['text'])
    elif data['kind']=='field':
        st.write(FIELD_LABELS.get(data['key'],data['key']));st.write(flat_value(data['value']))
        st.caption('Evidence status: '+data['status'])
        for e in data['evidence']:
            st.text(e.get('quote',''));st.caption(f"CMC crop page {e['page']} · {e.get('page_id','')}")
    else:st.json(data['value'])

def overview():
    st.markdown('''<div class="hero"><div class="eyebrow">Public regulatory evidence → formulation knowledge</div>
    <h1>EMA ASD &amp; CMC Evidence</h1><p>Explore oral medicines, inspect formulation evidence, and trace extracted properties back to their CMC source.</p>
    <div class="hero-meta">Corpus: 20 September 2026 · Website: 26 September 2026 · Research prototype by Chengzhe Gao</div></div>''',unsafe_allow_html=True)
    counts=manifest['working_labels'];positive=counts['ASD']+counts['Likely ASD']
    for col,label,value,note in zip(st.columns(4),['Selected oral products','CMC records extracted','ASD working set','FDA-overlap benchmark'],[len(products),manifest['completed'],positive,len(benchmark['rows'])],['337 baseline + 14 additions','1 public CMC source unavailable','28 extraction labels + 11 likely ASD','29 reference positives; 230 assumed negatives']):
        col.metric(label,value);col.caption(note)
    st.info('Scope: selected oral products first authorised through the EU centralised procedure, January 2010–20 September 2026. Generics, biosimilars and hybrids are excluded. This is not a count of all EMA medicines or new molecular entities.')
    st.subheader('From an ASD list to a reviewable CMC resource')
    for col,title,body,label,route in zip(st.columns(3),['Explore all 351 products','Ask for the evidence','Inspect the evaluation'],['Chemical structures, salt and solid form, formulation, excipients, manufacturing, and ASD-specific fields.','Search CMC passages, inspect cited pages, and use complete field scans for catalog questions.','Compare V1, V2 and V3 errors, reference-label disputes, and the RAG regression tests.'],['Open CMC database','Open evidence search','Open benchmark'],['CMC database','Evidence search','Benchmark & validation']):
        with col:
            st.markdown('**'+title+'**');st.write(body)
            st.button(label,on_click=jump,args=(route,'Palsonify') if route=='CMC database' else (route,),width='stretch')
    st.divider()
    a,b=st.columns([1.2,1])
    with a:
        st.subheader('ASD working set by authorisation year')
        subset=df[df['Working label'].isin(['ASD','Likely ASD'])].copy()
        subset['Label layer']=subset['Working label'].replace({'ASD':'Original extraction: ASD','Likely ASD':'Later review: likely ASD'})
        annual=subset.groupby(['Year','Label layer']).size().reset_index(name='Products')
        fig=px.bar(annual,x='Year',y='Products',color='Label layer',color_discrete_map={'Original extraction: ASD':'#245d89','Later review: likely ASD':'#dca24a'})
        fig.update_layout(height=330,margin=dict(l=5,r=5,t=10,b=5),legend_title_text='',legend=dict(orientation='h',y=-.3),xaxis=dict(dtick=2),plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig,width='stretch')
        st.caption('Any ASD entity yields an ASD product label. Labels include interpretations and refer to the reviewed formulation; this is not independently validated prevalence.')
    with b:
        st.subheader('Keep uncertainty visible')
        order=['ASD','Likely ASD','Non-ASD','Likely non-ASD','Unresolved','Inorganic adsorbate','Source unavailable']
        st.dataframe(pd.DataFrame([{'Working classification':k,'Products':counts[k]} for k in order]),hide_index=True,width='stretch')
        st.caption('Later review reclassified 58 originally insufficient records using saved evidence. Original labels remain available alongside the review.')
    st.subheader('14 products added after the February baseline')
    st.dataframe(df[df['New since February']][['Product','Active substance','First authorisation','Working label','CMC availability']],hide_index=True,width='stretch')
    st.caption('Includes Ojemda and Palsonify. Etcamah lacks a public CMC source in this snapshot.')
    with st.expander('What changed from the July website?'):
        st.markdown('''- Replaced the legacy 457-record denominator with a defined 337-product February cohort plus 14 additions.
- Replaced “34 confirmed ASD” with explicit original and later-review label layers.
- Expanded from an ASD-only list to 351 products, 9,254 field records and 435 structure images.
- Added CMC source pages, benchmark errors and retrieval evaluation.
- This is a September snapshot, not a live EMA feed.''')

def cmc_database():
    st.title('CMC database');st.write('One product at a time, with the source and uncertainty preserved.')
    a,b,c=st.columns([2,1,1])
    term=a.text_input('Search product, ingredient or company',key='db_search')
    labels=b.multiselect('Working classification',list(manifest['working_labels']),key='db_labels')
    period=c.selectbox('Approval cohort',['All 351 products','February baseline (337)','Added after February (14)'],key='db_period')
    subset=df.copy()
    if term:
        match=subset[['Product','Active substance','Company']].fillna('').astype(str).apply(lambda s:s.str.contains(term,case=False,regex=False)).any(axis=1)
        subset=subset[match]
    if labels:subset=subset[subset['Working label'].isin(labels)]
    if period!='All 351 products':subset=subset[subset['New since February']==period.startswith('Added')]
    st.caption(f'{len(subset)} of {len(products)} products · Search matches are literal, not regular expressions.')
    selected=[by_name[n] for n in subset['Product']]
    view=st.radio('Table view',['Product summary','All CMC fields — one row per product'],horizontal=True)
    display=subset[['Product','Active substance','First authorisation','Company','Original label','Working label','CMC availability']] if view=='Product summary' else pd.DataFrame(wide_rows(selected))
    st.dataframe(display,hide_index=True,width='stretch',height=340)
    with st.expander('Download this selection'):
        a,b,c=st.columns(3)
        with a:download_csv('Wide CMC table CSV',wide_rows(selected),'ema_products_cmc_wide.csv','download_products')
        with b:download_csv('All structured fields CSV',field_rows(selected),'ema_cmc_fields.csv','download_fields')
        with c:download_json('Full structured JSON',selected,'ema_cmc_records.json','download_records')
        st.caption('Field CSV keeps every entity, value, evidence status, quotation and page. Structure images are shown below.')
    if subset.empty:st.info('No matching products. Clear or broaden the filters.');return
    options=sorted(subset['Product'])
    if st.session_state.get('detail_product') not in options:st.session_state['detail_product']='Palsonify' if 'Palsonify' in options else options[0]
    name=st.selectbox('Inspect a product',options,key='detail_product');p=by_name[name];m=p['metadata']
    st.subheader(f"{name} · {m.get('inn') or m.get('active_substance','')}")
    st.caption(f"{m.get('holder','')} · First authorised {m.get('first_approval_date','')} · {p['id']}")
    st.link_button('Official EMA product page',m['ema_url'])
    a,b=st.columns(2);a.metric('Original extraction label',p['original_label']);b.metric('Working classification',p['working_label'])
    if p['review']:st.info('Later interpretation from saved records · '+p['review']['adjudication']);st.write(p['review']['reason'])
    if not p['fields']:st.warning('Public CMC source unavailable in this snapshot. Technical properties and ASD status are unknown.');return
    st.caption('Labels apply to the reviewed formulation. An original extraction label can be reported or interpreted; inspect the field status below.')
    with st.expander('Document scope and source identity'):st.write(p['scope']);st.json(p['source'])
    tabs=st.tabs(list(GROUPS)+['Structures','Source pages'])
    for tab,(group,keys) in zip(tabs,GROUPS.items()):
        with tab:
            fs=[f for f in p['fields'] if f['key'] in keys]
            table=[{'Field':FIELD_LABELS.get(f['key'],f['key']),'Entity':f.get('entity',''),'Value':flat_value(f['value']),'Status':f['status']} for f in fs]
            st.dataframe(pd.DataFrame(table),hide_index=True,width='stretch')
            for f in fs:
                with st.expander(FIELD_LABELS.get(f['key'],f['key'])+' · '+f.get('entity','')+' · '+f['status']):
                    st.write(flat_value(f['value']))
                    if f.get('note'):st.caption(f['note'])
                    if not f.get('evidence'):st.caption('No text quotation attached to this field. Absence is not a numerical zero.')
                    for e in f.get('evidence',[]):
                        st.text(e.get('quote',''));st.caption(f"CMC crop p. {e.get('page')}"+(f" · original report p. {e['printed_page']}" if e.get('printed_page') else ''))
                    if f.get('visual_evidence'):st.json(f['visual_evidence'])
    with tabs[-2]:
        if not p['structures']:st.info('No structure image extracted in this record.')
        cols=st.columns(2)
        for i,im in enumerate(p['structures']):
            with cols[i%2]:st.image(str(EVIDENCE_ROOT/im['file']),caption=f"{im['entity']} · CMC crop p. {im.get('page','?')}",width='content')
    with tabs[-1]:
        with retrieval.connect() as conn:pages=conn.execute('SELECT id,page FROM pages WHERE product_id=? ORDER BY page',(p['id'],)).fetchall()
        if pages:
            source_id=st.selectbox('CMC page',[r['id'] for r in pages],format_func=lambda x:'CMC crop page '+x.split(':p')[-1],key='product_source_page')
            source_panel(source_id);st.caption('Saved CMC text pages; drawings appear under Structures. The EMA link provides the published documents.')

def evidence_search():
    st.title('Evidence search');st.write('Retrieve CMC facts and source passages. Use the catalog for complete lists and explicit date filters.')
    st.caption('Live retrieval runs on the server. No model API is called. Saved Codex answers are labelled examples; this website does not generate new model answers.')
    mode=st.radio('Search mode',['Question search','Complete catalog','Saved answer examples'],horizontal=True,key='search_mode')
    if mode=='Saved answer examples':
        english={
          'D01':('Why can Palsonify have a crystalline DS and an ASD drug product?','The commercial tablet is described as an amorphous spray-dried dispersion. Input DS Form A and the final ASD belong to different manufacturing stages; there is no contradiction.'),
          'D02':('What is the pKa of Palsonify?','No numerical pKa is disclosed in the saved CMC record. Keep this field as not reported; do not fill it from assumption or model memory.'),
          'D03':('Do copovidone and spray granulation make Rhapsido an ASD?','No. The source describes retained crystalline Form A in the finished product and a nanosuspension route. These facts support a non-ASD interpretation.'),
          'D05':('Does this Xtandi EPAR describe the later ASD tablet?','The record covers the earlier liquid-filled soft capsule. It cannot establish the solid state of a later tablet formulation.'),
          'T05':('What are the Sotyktu ASD carrier and process?','HPMCAS H grade is reported. API and polymer are dissolved in acetone/water and the solution is spray-dried.'),
          'T06':('Are Ojemda HME and copovidone both directly confirmed?','Extrusion is reported; interpreting it as hot-melt extrusion is qualified. Copovidone is listed, but its ASD-carrier role is not explicitly confirmed.')}
        index={x['id']:x for x in evaluation['regression']}
        code=st.selectbox('Saved question',list(index),format_func=lambda k:k+' · '+english.get(k,(index[k]['question'],''))[0]);saved=index[code]
        st.info('Saved Codex answer · generated during internal evaluation, not live. English summaries preserve the saved answer.')
        st.write(english[code][1] if code in english else saved['answer'])
        if code in english:
            with st.expander('Original saved answer'):st.write(saved['answer'])
        st.caption(saved['review'])
        for ident in saved.get('citations',[]):
            with st.expander('Inspect source '+ident):source_panel(ident)
        return
    if mode=='Complete catalog':
        with st.form('catalog_form'):
            a,b,c=st.columns(3)
            field=a.selectbox('Field',list(retrieval.FIELD_TERMS),index=list(retrieval.FIELD_TERMS).index('asd_carrier'),format_func=lambda k:FIELD_LABELS.get(k,k))
            concept=b.selectbox('Term matching',['HPMCAS synonyms','Spray-drying synonyms','Literal text','Exact value'])
            status=c.selectbox('Evidence status',['Any','reported','partly_reported','interpretation','not_reported','not_applicable'])
            literal=st.text_input('Text / exact value (used for literal or exact matching)')
            a,b=st.columns(2)
            after=a.text_input('First authorisation after (exclusive, YYYY-MM-DD)',placeholder='2026-02-28')
            before=b.text_input('First authorisation on or before (inclusive, YYYY-MM-DD)',placeholder='2026-09-20')
            submitted=st.form_submit_button('Scan complete catalog',type='primary')
        if submitted:
            try:
                args={'field':field,'status':None if status=='Any' else status,'after':after.strip() or None,'before':before.strip() or None}
                if concept=='HPMCAS synonyms':args['concept']='hpmcas'
                elif concept=='Spray-drying synonyms':args['concept']='spray_drying'
                elif concept=='Exact value':args['equals']=literal
                else:args['contains']=literal or None
                st.session_state['catalog_result']=retrieval.catalog(**args)
            except ValueError as e:st.session_state.pop('catalog_result',None);st.error(str(e))
        result=st.session_state.get('catalog_result')
        if result:
            st.subheader(f"{result['products']} products · {result['records']} field records")
            st.caption('Applied filters: '+json.dumps({k:result[k] for k in ['field','contains','equals','concept','status','after_exclusive','before_inclusive']},ensure_ascii=False))
            st.warning('A polymer-name match does not confirm its carrier role. Counts refer to saved fields, not independently adjudicated formulation truth.')
            rows=[{'Product':r['name'],'Entity':r['entity'],'Value':flat_value(r['value']),'Status':r['status'],'First authorisation':r['metadata'].get('first_approval_date'),'Citation':r['id']} for r in result['results']]
            st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch');download_csv('Download catalog matches',rows,'catalog_matches.csv','catalog_csv')
            if rows:source_panel(st.selectbox('Inspect a matching field',[r['Citation'] for r in rows],key='catalog_citation'))
        return
    with st.form('question_form'):
        question=st.text_input('CMC question',value='What are the ASD carrier and manufacturing process of Sotyktu?',max_chars=4000)
        a,b=st.columns([2,1]);product=a.selectbox('Restrict to a product (optional)',['Automatic']+sorted(by_name));limit=b.selectbox('Ranked pages',[5,8,12],index=1)
        submitted=st.form_submit_button('Retrieve evidence',type='primary')
    if submitted:
        try:st.session_state['evidence_result']=retrieval.query(question,limit=limit,product=None if product=='Automatic' else product)
        except (ValueError,RuntimeError) as e:st.session_state.pop('evidence_result',None);st.error(str(e))
    result=st.session_state.get('evidence_result')
    if not result:
        st.markdown('**Try:** “Palsonify pKa” · “Rhapsido copovidone spray granulation ASD” · “Xtandi dosage form”');return
    st.subheader('Retrieved evidence');st.caption('Results for: '+result['question'])
    for warning in result['warnings']:st.warning(warning)
    for p in result['target_products']:
        with st.expander(p['product']+' · formulation and document scope'):
            st.write(p['document_scope'])
            if p['review']:st.json(p['review'])
    a,b=st.columns([1,1.1])
    with a:
        st.markdown('**Structured records**')
        for f in result['facts']:
            name=by_id[f['product_id']]['product']
            with st.expander(name+' · '+FIELD_LABELS.get(f['key'],f['key'])+' · '+f['status']):
                st.write(flat_value(f['value']));st.caption(f['entity']+' · '+f['id'])
                if f['note']:st.caption(f['note'])
                for e in f['evidence']:
                    st.text(e.get('quote',''));st.caption(e['page_id']+(' · quotation matched to saved page' if e['quote_verified'] else ' · verify quotation'))
    with b:
        st.markdown('**CMC source passages**')
        for i,ctx in enumerate(result['contexts']):
            with st.expander(f"{ctx['product']} · CMC p. {ctx['crop_page']} · {ctx['citation']}",expanded=i==0):
                st.caption('Full page via field citation' if ctx['complete_page'] else 'Ranked passage; inspect the full page for context')
                st.text(ctx['text']);st.markdown('[Official EMA source]('+by_name[ctx['product']]['metadata']['ema_url']+')')
    download_json('Export evidence bundle for Codex',result,'epar_evidence_bundle.json','evidence_download')
    if result['contexts']:
        with st.expander('Open any retrieved page in full'):source_panel(st.selectbox('Source citation',[x['citation'] for x in result['contexts']],key='full_source'))

def benchmark_view():
    st.title('Benchmark & validation');st.write('What the comparisons show, where they fail, and what remains to be validated.')
    tabs=st.tabs(['ASD methods','RAG evaluation','Scope & reproducibility'])
    with tabs[0]:
        st.info('Frozen February EMA cohort → 259 products overlapping FDA approvals in 2012–2023. Mapping yields 29 ASD positives; 230 unlisted products are assumed negative for this exploratory comparison.')
        st.link_button('Moseson et al. (2024), including Tze Ning Hiew','https://doi.org/10.1016/j.ijpx.2024.100259')
        labels={'v1':'V1 · basic keywords','v2':'V2 · DP-only rules','v3':'V3 · saved Gemini + backfill'}
        rows=[{'Method':labels[m['name']],**{k:m[k] for k in ['TP','FP','FN','TN']},'Unresolved':259-m['explicit']} for m in benchmark['methods']]
        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
        st.caption('Different document scopes and mixed historical/backfilled V3 inputs: not a controlled model ranking. Vaxchora and Palforzia extend beyond the paper’s NDA scope.')
        for col,m in zip(st.columns(3),benchmark['methods']):
            with col:
                st.markdown('**'+labels[m['name']]+'**');st.markdown('**FN — missed reference ASD**');st.write(', '.join(m['missed']))
                st.markdown('**FP — reference negative**');st.write(', '.join(x['product'] for x in m['identified'] if x['outcome']=='FP'))
                if m['unknown']:st.warning('Unresolved: '+', '.join(m['unknown']))
        st.subheader('An apparent model error can be a formulation mismatch')
        st.markdown('''- **Xtandi:** early liquid-filled capsules in the reviewed EPAR differ from the later ASD tablets.
- **Lynparza:** the reviewed capsule is a crystalline solid dispersion; the later tablet differs.
- **Votubia, Gavreto, Tavneos, Zokinvy and Vanflyta:** evidence supports reviewing possible reference omissions; formulation matching and literature scope must be resolved before changing labels.''')
        st.caption('Shared explicit FN: Xtandi. Shared reference FP: Votubia, Gavreto, Zokinvy and Vanflyta.')
        with st.expander('All 259 product-level comparisons'):
            st.dataframe(pd.DataFrame(benchmark['rows']),hide_index=True,width='stretch');download_csv('Download benchmark comparisons',benchmark['rows'],'benchmark_259.csv','benchmark_csv')
        with st.expander('Later Codex review — separate, non-blind comparison'):
            working=load_json('working_label_comparison.json')
            st.write('The original 337-product cohort has 37 later working ASD labels versus 33 saved Gemini positives. Two additional ASD extraction labels in the extension give a current working set of 39.')
            st.json({k:v['counts'] for k,v in working['benchmark259'].items()})
            for line in working['limitations']:st.caption(line)
    with tabs[1]:
        a,b,c=st.columns(3);a.metric('Selected regression questions',24);b.metric('Required-field coverage','20/24 → 24/24');c.metric('Additional stress questions',4)
        st.warning('These questions were used during development. Coverage and citation resolution are not answer accuracy. Answers were generated and reviewed in the same Codex conversation, without an independent blind evaluator.')
        st.write('44 mechanical checks passed for source consistency, identifiers and query behavior. They do not validate scientific conclusions.')
        st.dataframe(pd.DataFrame([
            {'Stress case':'Misspelled Palsonfy','Response':'Suggest Palsonify; confirm identity.'},
            {'Stress case':'Approvals after February 2026','Response':'Use explicit date-filtered catalog scan.'},
            {'Stress case':'List all HPMCAS carriers','Response':'14 product matches / 15 records; 7 products have fields marked reported.'},
            {'Stress case':'Give a certain ASD prevalence','Response':'Specify labels, formulation scope and denominator first.'}]),hide_index=True,width='stretch')
        for answer in evaluation['regression']:
            with st.expander(answer['id']+' · '+answer['question']):
                st.write(answer['answer']);st.caption(answer['review']);st.code(', '.join(answer['citations']) or 'No supporting product citation',language=None)
        for answer in evaluation['stress']:
            with st.expander(answer['id']+' · '+answer['question']):st.write(answer['answer']);st.caption(answer['limitation'])
        download_json('Download 28 saved evaluation cases',evaluation,'rag_evaluation.json','evaluation_json')
    with tabs[2]:
        st.markdown('''### Data scope
Selected centrally authorised oral products from January 2010 through 20 September 2026. Generics, biosimilars and hybrids are excluded. Product count is not molecule count. Historic authorisations are retained; first authorisation does not imply current marketing availability.

### Evidence contract
Drug substance and finished product are separate. Commercial formulation, historical development formulation, unit strength and clinical regimen are not interchangeable. Drug loading in the ASD intermediate and whole product have distinct denominators. Numerical pKa, BCS class and carrier roles are not filled from model memory.

### Retrieval and answers
SQLite FTS5/BM25, limited bilingual expansion, product/ingredient aliases and field routing. Exhaustive queries use explicit catalog filters. No embedding or model API is called. Codex generated the saved evaluation answers from retrieved bundles. For a new question, export the evidence bundle for use in Codex. This deployment does not connect a personal Codex session to a public chatbot.

### Validation still needed
Independent formulation-specific adjudication, unseen questions, answer–citation entailment review and completeness checks. A source-linked answer can still contain an interpretation error.''')
        st.json(manifest);download_json('Download data manifest',manifest,'manifest.json','manifest_json')
        st.caption('Independent research prototype using public EMA evidence; not an EMA service or clinical dosing advice. Extraction notes retain their original language.')

st.markdown('<div class="eyebrow" style="color:#426b89">EMA / CMC KNOWLEDGE</div>',unsafe_allow_html=True)
st.radio('Explore',['Overview','CMC database','Evidence search','Benchmark & validation'],horizontal=True,key='section',label_visibility='collapsed')
{'Overview':overview,'CMC database':cmc_database,'Evidence search':evidence_search,'Benchmark & validation':benchmark_view}[st.session_state['section']]()
st.divider();st.caption('Public EMA regulatory evidence · Corpus snapshot 2026-09-20 · Separate reported facts, interpretations and missing information.')
