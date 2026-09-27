"""English CMC explorer with optional evidence-grounded OpenCode Go answers."""
from collections import Counter
from html import escape
import os
import uuid
import pandas as pd
import plotly.express as px
import streamlit as st
import retrieval
import generation
from bundle import EVIDENCE_ROOT
from data_access import load_json, citation, safe_csv, FIELD_LABELS, GROUPS
from presentation import (assessment, rationale, basis, product_row, formulation_row,
    english_fields, english_value, entity_name, comparison_rows, field_text,
    OMISSIONS, FORMULATION, STATUS, CJK, ingredient, carrier_review)

st.set_page_config(page_title='EMA Oral ASD Formulations',page_icon='💊',layout='wide')
st.markdown('''<style>
.block-container{max-width:1480px;padding:2.5rem 3rem 3rem}
h1,h2,h3{letter-spacing:-.035em;color:#172e3c}
h1{font-weight:650!important} h3{font-size:1.35rem!important}
[data-testid="stHeader"]{background:transparent}
.masthead{display:flex;justify-content:space-between;align-items:center;margin:0 0 16px;gap:20px}
.brand{display:flex;align-items:center;gap:12px;font-weight:700;letter-spacing:-.03em;font-size:1.18rem;color:#183a40}
.brandmark{display:grid;place-items:center;background:#173d43;color:#fff;width:40px;height:40px;border-radius:11px;font-size:.8rem;letter-spacing:.05em}
.masthead-note{font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:#617477;text-align:right}
.st-key-section [role="radiogroup"]{gap:6px;padding:6px;background:#e9efed;border:1px solid #dce5e1;border-radius:13px;width:fit-content;margin-bottom:12px}
.st-key-section [data-baseweb="radio"],.st-key-section [data-testid="stRadioOption"]{margin:0;padding:9px 16px;border-radius:9px;color:#52656a;transition:background .15s}
.st-key-section [data-baseweb="radio"]>div:first-child{display:none}
.st-key-section [data-testid="stRadioOption"]>div>div:first-child{display:none}
.st-key-section [data-baseweb="radio"]:has(input:checked),.st-key-section [data-testid="stRadioOption"][data-selected="true"]{background:#fff;color:#124c46;box-shadow:0 2px 5px #193c3612}
.st-key-section [data-baseweb="radio"]:has(input:focus-visible),.st-key-section [data-testid="stRadioOption"]:has(input:focus-visible){outline:2px solid #0b7a68;outline-offset:2px}
.st-key-section [data-baseweb="radio"] p,.st-key-section [data-testid="stRadioOption"] p{font-weight:600;font-size:.87rem}
.hero{position:relative;overflow:hidden;background:#153e43;padding:25px 32px;border-radius:18px;color:white;margin-bottom:4px}
.hero:after{content:'';position:absolute;width:280px;height:280px;border:1px solid #ffffff16;border-radius:50%;right:-95px;top:-150px;box-shadow:0 0 0 55px #ffffff04,0 0 0 110px #ffffff04;pointer-events:none}
.hero h1{font-size:2.3rem;line-height:1.12;color:#fff!important;margin:10px 0 12px;padding:0;max-width:820px;letter-spacing:-.04em}
.hero p{color:#c3dad7;margin:0;max-width:820px;font-size:.95rem;line-height:1.65}
.eyebrow{font-size:.66rem;letter-spacing:.17em;text-transform:uppercase;font-weight:700;color:#a3d4c2}
.section-intro{padding:16px 0 8px}
.section-intro .eyebrow{color:#0c7563}
.section-intro h1{font-size:2.25rem;padding:8px 0 10px;margin:0}
.section-intro p{color:#52686e;margin:0;max-width:850px}
[data-testid="stMetric"]{background:#fff;border:1px solid #dce5e1;border-radius:13px;padding:12px 22px;border-top:3px solid #7cb7a5}
[data-testid="stMetricValue"]{color:#164f49;font-size:2.15rem;font-weight:600;letter-spacing:-.045em}
[data-testid="stMetricLabel"] p{font-size:.8rem;color:#52666b}
[data-testid="stVerticalBlockBorderWrapper"]>div{border-radius:14px!important;border-color:#dce5e1!important;background:#fff}
[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden}
[data-testid="stForm"]{background:#fff;border-color:#dce5e1;border-radius:14px;padding:24px}
[data-testid="stExpander"]{background:#fff;border-color:#dce5e1;border-radius:11px}
[data-baseweb="tab-list"]{gap:22px;border-bottom:1px solid #dce5e1}
[data-baseweb="tab"]{padding:12px 1px;font-weight:600}
button[kind="secondary"],button[kind="primary"]{border-radius:9px}
button[kind="primary"]{background:#0c7563;border-color:#0c7563}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:#526b72!important}
.detail-heading{margin-top:18px;padding-top:22px;border-top:1px solid #dce5e1;display:flex;justify-content:space-between;align-items:center;gap:16px}
.detail-heading h3{font-size:1.8rem!important;margin:6px 0;padding:0}
.detail-heading .eyebrow{color:#0c7563}
.status-pill{font-size:.75rem;font-weight:600;white-space:nowrap;background:#e0f0e8;color:#175844;padding:7px 12px;border-radius:20px}
.status-neutral{background:#e9eef1;color:#445965}.status-pending{background:#fff1db;color:#7b5622}
.fact-card{background:#fff;border:1px solid #dce5e1;border-radius:13px;padding:20px 22px;min-height:118px;height:100%}
.fact-label{color:#60747a;text-transform:uppercase;letter-spacing:.11em;font-size:.66rem;font-weight:700}
.fact-value{color:#1a4346;font-size:1.1rem;font-weight:600;margin-top:9px;line-height:1.5}
.fact-note{font-size:.77rem;color:#61777d;margin-top:8px}
.search-flow{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:4px 0 14px;font-size:.82rem;color:#53696f}
.search-flow span{background:#fff;border:1px solid #dce5e1;border-radius:8px;padding:9px 14px}
.search-flow .cost{background:#e0f0e8;color:#175844;border-color:#c7e3d5}
.site-footer{display:flex;justify-content:space-between;gap:16px;font-size:.75rem;color:#60747a;padding:10px 0}
@media(max-width:760px){.block-container{padding:2rem 1rem}.hero{padding:25px}.hero h1{font-size:2rem}.masthead-note{display:none}.st-key-section [data-baseweb="radio"]{padding:7px 10px}.st-key-section [role="radiogroup"]{width:100%}.fact-card{min-height:auto}.site-footer{display:block}}
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

def page_intro(kicker,title,description):
    st.markdown(f'<div class="section-intro"><div class="eyebrow">{escape(kicker)}</div><h1>{escape(title)}</h1><p>{escape(description)}</p></div>',unsafe_allow_html=True)

def fact_card(label,value,note=''):
    st.markdown(f'<div class="fact-card"><div class="fact-label">{escape(label)}</div><div class="fact-value">{escape(value)}</div><div class="fact-note">{escape(note)}</div></div>',unsafe_allow_html=True)

def carrier_panel(p):
    review=carrier_review(p)
    left,right=st.columns(2)
    with left:fact_card('ASD polymer / carrier',review['ASD carrier'],review['Carrier basis']+' · saved CMC evidence')
    with right:fact_card('ASD preparation',FORMULATION[p['product']][1],'Intermediate manufacture')
    with st.expander('Why this carrier?'):
        st.write(review['Carrier rationale'])
        st.caption('CMC crop pages: '+review['Carrier CMC pages'])
        st.text(review['Carrier source excerpts'])

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
    decision=assessment(p)
    cls='status-pending' if decision=='Insufficient evidence' else ('status-neutral' if decision=='Non-ASD' else '')
    st.markdown(f'<div class="detail-heading"><div><div class="eyebrow">Formulation profile</div><h3>{escape(name)}</h3></div><span class="status-pill {cls}">ASD assessment: {escape(decision)}</span></div>',unsafe_allow_html=True)
    st.caption(f"{ingredient(p)} · {m.get('holder','')} · First authorised {m['first_approval_date']}")
    st.write(rationale(p))
    if name in OMISSIONS:st.info('Potential literature omission: not in the paper-mapped ASD list. See Literature comparison for evidence and scope.')
    st.link_button('Official EMA product page',m['ema_url'])
    if not p['fields']:return
    if decision=='ASD':carrier_panel(p)
    tabs=st.tabs(['Drug product','Drug substance','ASD formulation','Structures','Source pages'])
    groups=[GROUPS['Drug product'],GROUPS['Drug substance'],[k for k in GROUPS['ASD & loading'] if k!='asd']]
    for tab,keys in zip(tabs,groups):
        with tab:
            fs=[f for f in p['fields'] if f['key'] in keys]
            rows=[]
            if keys==groups[-1] and decision=='ASD':
                review=carrier_review(p)
                rows.append({'Property':'ASD carrier / polymer','Component':'Product-level review','Value':review['ASD carrier'],'Wording':review['Carrier basis']})
            for f in fs:
                if decision=='ASD' and f['key']=='asd_carrier':continue
                val,origin=english_value(p,f)
                rows.append({'Property':FIELD_LABELS[f['key']],'Component':entity_name(f.get('entity','')),'Value':val,'Wording':origin})
            table(rows)
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
    if decision=='ASD':csv_button('Download formulation assessment',[formulation_row(p)],name+'_formulation_review.csv',prefix+'_review_csv')

def asd_view():
    st.markdown('''<div class="hero"><div class="eyebrow">Public EMA evidence · Formulation science</div>
    <h1>EMA Oral ASD Formulations</h1><p>Amorphous solid dispersion formulations, their carriers, manufacturing processes and drug-product properties.</p></div>''',unsafe_allow_html=True)
    for col,label,value in zip(st.columns(3),['Products assessed as ASD','Oral products in the study','Products with CMC records'],[len(asd_products),len(products),sum(bool(p['fields']) for p in products)]):col.metric(label,value)
    st.caption('January 2010–20 September 2026 · Selected centrally authorised oral products; generics, biosimilars and hybrids excluded. ASD counts are review assessments, including interpretations.')
    with st.container(border=True):
        st.subheader('ASD drug-product database')
        a,b=st.columns([2,1]);term=a.text_input('Search ASD product, ingredient, carrier or company',key='asd_search',placeholder='Try copovidone, Gavreto or Vertex…')
        view=b.selectbox('Show',['Formulation summary','Manufacturing & excipients','Drug loading'],key='asd_view')
        subset=asd_table.copy()
        search_cols=['Product','Active ingredient','ASD carrier','Company']
        if term:subset=subset[subset[search_cols].astype(str).apply(lambda s:s.str.contains(term,case=False,regex=False)).any(axis=1)]
        cols={'Formulation summary':['Product','ASD carrier','Carrier basis','ASD preparation','Dosage form','Strength','Active ingredient','Year','Literature note'],
              'Manufacturing & excipients':['Product','Dosage form','DP manufacturing','Excipients'],
              'Drug loading':['Product','ASD carrier','API : carrier ratio','API fraction in ASD','API fraction in DP']}[view]
        st.caption(f"{len(subset)} {'product' if len(subset)==1 else 'products'} · Inferred = carrier assignment from saved CMC evidence. Strength is per unit unless stated; FDC = fixed-dose combination.")
        table(subset[cols],height=min(395,36*(len(subset)+1)+3),column_config={'Product':st.column_config.TextColumn(width='small'),'ASD carrier':st.column_config.TextColumn(width='medium'),'Carrier basis':st.column_config.TextColumn(width='small'),'ASD preparation':st.column_config.TextColumn(width='medium')})
        csv_button('Download all ASD formulation columns',subset,'EMA_ASD_formulations.csv','asd_csv')
    if not subset.empty:product_detail(by_name[st.selectbox('Inspect an ASD product',sorted(subset['Product']),key='asd_product')],'asd_detail')
    with st.expander('ASD products by first authorisation year'):
        counts=asd_table.groupby('Year').size().reset_index(name='Products')
        fig=px.bar(counts,x='Year',y='Products',color_discrete_sequence=['#245d89'])
        fig.update_layout(height=310,margin=dict(t=10,l=10,b=10,r=10),plot_bgcolor='rgba(0,0,0,0)');st.plotly_chart(fig,width='stretch')

def all_medicines():
    page_intro('Product library','Oral product database','Explore the 351 oral products in this study, with structured drug-substance and drug-product properties.')
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

@st.cache_resource
def answer_service():
    return generation.AnswerService()

def model_key():
    key=os.environ.get('OPENCODE_GO_API_KEY','')
    if key:return key
    try:return str(st.secrets.get('OPENCODE_GO_API_KEY',''))
    except (FileNotFoundError,st.errors.StreamlitSecretNotFoundError):return ''

def ai_answer_view():
    key=model_key()
    if not key:st.info('AI answers are temporarily unavailable. You can still use Question search and Complete catalog.')
    st.caption('GLM-5.3-Flash · Answers use retrieved CMC evidence. Reported facts and review inferences are kept distinct.')
    with st.form('ai_question'):
        question=st.text_input('Ask about an oral formulation',value='What are the ASD carrier and manufacturing process of Sotyktu?',max_chars=1500)
        product=st.selectbox('Focus on a product',['Automatic']+sorted(by_name))
        ask=st.form_submit_button('Ask EPAR',type='primary',disabled=not bool(key))
    if ask:
        st.session_state.pop('ai_answer',None)
        st.session_state.pop('ai_error',None)
        st.session_state.pop('ai_evidence',None)
        if not question.strip():st.warning('Please enter a question.');return
        result=retrieval.query(question,product=None if product=='Automatic' else product)
        pack=generation.evidence_pack(result,products)
        st.session_state['ai_evidence']=pack
        if result['product_suggestions'] and not result['target_products']:
            st.session_state['ai_error']='Please confirm the product using the Focus on a product selector. Possible spelling: '+', '.join(result['product_suggestions'])
        else:
            session=st.session_state.setdefault('rag_session',str(uuid.uuid4()))
            with st.spinner('Retrieving CMC evidence and preparing a cited answer…'):
                try:st.session_state['ai_answer']=answer_service().answer(pack,key,session)
                except generation.AnswerError as error:st.session_state['ai_error']=str(error)
    error=st.session_state.get('ai_error')
    if error:st.warning(error)
    pack=st.session_state.get('ai_evidence')
    answer=st.session_state.get('ai_answer')
    if answer:
        st.subheader('Answer');st.caption(pack['question'])
        st.markdown(answer['answer'])
        st.caption('GLM-5.3-Flash · '+('Cached answer; no new model call.' if answer['cached'] else 'Generated from the retrieved evidence.')+' Citation identifiers were checked; this does not independently verify every scientific claim.')
    if pack:
        with st.expander('Retrieved sources',expanded=bool(error)):
            for p in pack['source_passages']:
                st.markdown('**'+p['product']+' · CMC page '+str(p['CMC_page'])+' · ['+p['id']+']**')
                st.text(p['text']);st.link_button('Official EMA product page',by_name[p['product']]['metadata']['ema_url'],key='ai_source_'+p['id'])
        if pack['warnings']:
            with st.expander('Retrieval scope and limitations'):
                for warning in pack['warnings']:st.write(warning)

def evidence_search():
    page_intro('Evidence workspace','CMC evidence search','Search the saved formulation records and read the CMC passages behind each finding.')
    mode=st.radio('Search mode',['AI answer','Question search','Complete catalog','Worked examples'],horizontal=True,key='search_mode')
    if mode=='AI answer':
        st.markdown('<div class="search-flow"><span>Your question</span> → <span>Retrieve CMC evidence</span> → <span>GLM-5.3-Flash answer</span><span class="cost">Cited sources</span></div>',unsafe_allow_html=True)
        ai_answer_view();return
    st.caption('Evidence-only search: no model API calls. Choose AI answer for retrieval-augmented generation with GLM-5.3-Flash.')
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
        if assessment(record)=='ASD' and any(f['key']=='asd_carrier' for f in result['facts']):carrier_panel(record)
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
    page_intro('Reference comparison','Literature comparison','Where the CMC review agrees with the published FDA ASD list — and where the formulations or findings differ.')
    st.link_button('Moseson et al. (2024), including Tze Ning Hiew','https://doi.org/10.1016/j.ijpx.2024.100259')
    st.markdown('''**Comparison set:** 259 EMA products whose matched oral formulations were also FDA-approved in 2012–2023, the period covered by the paper. Matching uses formulation rather than brand name or indication.

The paper lists ASD formulations. **Not listed does not prove non-ASD.** Unlisted products were initially treated as negative to compare screening methods; the review below separates possible reference omissions and different formulations.''')
    rows=comparison_rows(products,benchmark);frame=pd.DataFrame(rows);counts=Counter(r['Comparison'] for r in rows)
    for col,label,n in zip(st.columns(3),['ASD in both','Potential literature omissions','Different formulations'],[counts['ASD in both'],counts['Potential literature omission'],counts['Different formulation reviewed']]):col.metric(label,n)
    st.caption(f"29 EMA product/formulation matches to the paper ASD list: 27 agree with our review; 2 involve different formulations. Of 230 unlisted products, 5 are assessed as ASD, {counts['Not listed; review non-ASD']} as non-ASD and {counts['CMC evidence unresolved']} remain unresolved. Vaxchora and Palforzia are included in the overlap but are outside the paper’s NDA scope.")
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
    page_intro('Project & people','About this project','A formulation research project built on public regulatory evidence.')
    st.markdown('''### Data and assessment
EMA medicines records and Article 57 route information define the selected oral cohort. EPAR CMC sections provide the formulation evidence. This release contains 351 products and 350 CMC records, with a source snapshot of 20 September 2026.

The site consolidates the completed Codex review into one product assessment: **ASD**, **Non-ASD** or **Insufficient evidence**. ASD covers a drug dispersed in an organic carrier matrix in amorphous form, including solid solutions and cyclodextrin-based dispersions. Amorphous silica adsorbates are outside this category. A pure amorphous API or a polymer excipient alone is not sufficient.

The 39 ASD assessments include interpretations of the manufacturing record; they are not 39 independently confirmed experimental findings. Carrier assignments are marked **Reported** or **Inferred**, with their supporting CMC excerpts. Process details and quantitative drug loading are retained only where the record supports them. Combination products can contain both ASD and non-ASD components. Approval year refers to the first product authorisation, not every formulation change.

### Evidence search and RAG
BM25 text retrieval is combined with product and property matching. The **AI answer** mode sends retrieved CMC evidence to **GLM-5.3-Flash via OpenCode Go** and returns a cited answer. Other search modes retrieve evidence without calling a model. Generated answers keep source-reported facts separate from saved review interpretations. Source identifiers are checked automatically; this is not independent scientific verification.

Development used 24 regression questions and 4 stress cases. Required-field coverage improved from 20/24 to 24/24. This measures retrieval coverage, not scientific answer accuracy. Independent held-out evaluation remains necessary.

### Acknowledgements
Thank you to my wife, **Xiuli Li**, for her support; my friends **Tianyi Li, Yongjian Wang, Fan Meng and Zoe Wen** for brainstorming; and my manager **Fady Ibrahim** for his encouragement. Thank you to my PhD advisor **Kevin J. Edgar**, my postdoctoral advisor **Lynne Taylor**, and my mentor **Tze Ning Hiew** for inspiring my work on amorphous solid dispersions.

### Project history
Earlier website versions are available in GitHub’s commit history. Their counts and methods may differ from this release.''')
    st.link_button('GitHub version history','https://github.com/gaochengzhecpu/ASD/commits/main/')
    st.caption('Independent research by Chengzhe Gao using public regulatory evidence. Not an EMA service or clinical dosing resource.')

st.markdown('<div class="masthead"><div class="brand"><span class="brandmark">CMC</span>Formulation Atlas</div><div class="masthead-note">Public EMA evidence<br>Research by Chengzhe Gao</div></div>',unsafe_allow_html=True)
sections={'ASD formulations':asd_view,'Oral product database':all_medicines,'CMC evidence search':evidence_search,'Literature comparison':literature_view,'About':about}
if st.session_state.get('section') not in sections:st.session_state['section']='ASD formulations'
st.radio('Explore',list(sections),horizontal=True,key='section',label_visibility='collapsed')
sections[st.session_state['section']]()
st.divider();st.markdown('<div class="site-footer"><span>Chengzhe Gao · Formulation Atlas</span><span>Public EMA CMC evidence · Data snapshot: 20 September 2026</span></div>',unsafe_allow_html=True)
