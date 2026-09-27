"""Auditable full-cohort queries. Counts never use retrieved top-k passages or an LLM.

Only explicitly supported filters are accepted. Unrecognised conditions trigger clarification.
Salt labels consolidate saved extraction fields; they do not constitute a new scientific review.
"""
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date
import json
import re

from presentation import assessment, carrier_review, english_value, entity_name, STATUS, basis

SALT_LABELS = ['Salt', 'Non-salt', 'Stage-dependent', 'Complex / inorganic', 'Unknown', 'Not applicable']
# These saved narratives require an explicit interpretation of scope, not keyword matching.
SALT_SPECIAL = {
    'Qtern': {'saxagliptin': ('Stage-dependent', 'Free-base input DS is converted to hydrochloride in the coating.')},
    'Olysio': {'*': ('Stage-dependent', 'Crystalline free-form input DS; sodium salt in the product.')},
    'Zontivity': {'*': ('Stage-dependent', 'Sulfate DS; partial conversion to free base during manufacture/storage.')},
    'Komboglyze': {'saxagliptin': ('Unknown', 'Free-base monohydrate DS; the saved field leaves the final DP salt form unresolved.')},
    'Bylvay': {'*': ('Unknown', 'Saved record flags inconsistent salt terminology; hydrate alone does not resolve salt status.')},
    'Voranigo': {'*': ('Unknown', 'Citric-acid co-component is reported; salt versus co-crystal is not confirmed.')},
    'Velphoro': {'*': ('Complex / inorganic', 'Iron oxyhydroxide complex; outside the conventional API/counterion salt count.')},
    'Fexeric': {'*': ('Complex / inorganic', 'Ferric citrate coordination complex.')},
    'Feraccru': {'*': ('Complex / inorganic', 'Ferric maltol coordination complex/chelate.')},
    'Lokelma': {'*': ('Complex / inorganic', 'Inorganic ion-exchange crystal, shown separately from conventional API salts.')},
    'Xoanacyl': {'*': ('Complex / inorganic', 'Ferric citrate coordination complex.')},
    'Sotyktu': {'*': ('Non-salt', 'Commercial free base; the earlier development hydrochloride is not counted.')},
    'Calquence': {'*': ('Non-salt', 'Reviewed formulation uses free-form API; a different maleate formulation is not inferred.')},
    'Braftovi': {'*': ('Non-salt', 'Covalent substituents and succinic-acid excipient are not an API salt.')},
    'Balversa': {'*': ('Non-salt', 'Me glumine is an excipient in the saved record, not a DS counterion.'.replace('Me glumine','Meglumine'))},
}


def salt_component(product, item):
    entity = item.get('entity', '')
    exceptions = SALT_SPECIAL.get(product['product'], {})
    special = exceptions.get(entity, exceptions.get('*'))
    value = item['value']
    if special:
        label, note = special
    elif item['status'] == 'not_applicable':
        label, note = 'Not applicable', 'Salt classification is not applicable to this active substance.'
    elif item['status'] == 'not_reported' or value is None:
        label, note = 'Unknown', 'No usable salt assignment in the saved field.'
    elif isinstance(value, dict) and isinstance(value.get('is_salt'), bool):
        label = 'Salt' if value['is_salt'] else 'Non-salt'
        note = 'Salt assignment recorded in the saved extraction.'
    elif isinstance(value, str):
        # Only salt fields are considered. Negation precedes counterion matching.
        if re.search(r'非盐|非外加|未成盐|未见外加反离子|无对离子|无独立对离子|未示独立对离子|未带.*对离子|无反离子|游离|母体|未见盐对离子', value):
            label, note = 'Non-salt', 'Saved narrative assigns the free / non-salt API form.'
        elif re.search(r'hydrochloride|hydrobromide|sulfate|phosphate|malate|fumarate|acetate|tosylate|tosilate|meglumine|sodium|钠盐|钾|盐酸盐|氢溴酸盐|甲磺酸盐|磷酸盐', value, re.I):
            label, note = 'Salt', 'Named salt in the saved salt field.'
        else:
            label, note = 'Unknown', 'Saved salt narrative needs manual normalization.'
    else:
        label, note = 'Unknown', 'No unambiguous salt assignment in the saved field.'
    return {'component': entity_name(entity) or product['metadata'].get('active_substance', ''),
            'status': label, 'basis': STATUS.get(item['status'], item['status']), 'note': note,
            'pages': sorted({e['page'] for e in item.get('evidence', [])})}


def salt_record(product):
    components = [salt_component(product, f) for f in product['fields'] if f['key'] == 'salt']
    labels = {x['status'] for x in components}
    if 'Salt' in labels: label = 'Salt'
    elif 'Stage-dependent' in labels: label = 'Stage-dependent'
    elif not labels or 'Unknown' in labels: label = 'Unknown'
    elif 'Complex / inorganic' in labels: label = 'Complex / inorganic'
    elif labels == {'Not applicable'}: label = 'Not applicable'
    else: label = 'Non-salt'
    return {'status': label, 'components': components}


@dataclass
class Plan:
    kind: str = 'evidence'
    question: str = ''
    filters: dict = field(default_factory=dict)
    start: str | None = None
    end: str | None = None
    reported_only: bool = False
    problem: str = ''

    def public(self): return asdict(self)


def plan_question(question, named_product=False):
    """Conservative parser: never execute SQL or code supplied by a user or a model."""
    text = question.lower().strip()
    text = re.sub(r'([\u3400-\u9fff])([a-z])|([a-z])([\u3400-\u9fff])',lambda m:(m[1]+' '+m[2]) if m[1] else (m[3]+' '+m[4]),text)
    aggregate = bool(re.search(r'\bhow many\b|\bnumber of\b|\bcount\b|\bpercentage\b|\bpercent\b|\blist\b|\ball\b|\bwhich (?:\w+ ){0,2}(?:drugs|products|medicines)\b|多少|哪些|全部|比例', text))
    plan = Plan(question=question)
    if not aggregate or named_product: return plan
    plan.kind = 'catalogue'
    rest = text
    # Supported dates are ISO dates or complete years, with unambiguous inclusive boundaries.
    def period(match):
        nonlocal plan
        a, b = match.group(1), match.group(2)
        plan.start = a+'-01-01' if len(a)==4 else a
        plan.end = b+'-12-31' if len(b)==4 else b
        return ' '
    rest = re.sub(r'\b(?:between|from)\s+(20\d\d(?:-\d\d-\d\d)?)\s+(?:and|to|through)\s+(20\d\d(?:-\d\d-\d\d)?)', period, rest)
    def bound(match):
        word, when = match.group(1), match.group(2)
        if word == 'in': plan.start, plan.end = (when+'-01-01', when+'-12-31') if len(when)==4 else (when,when)
        elif word in ('since','after'):
            plan.start = when+'-01-01' if len(when)==4 and word=='since' else (str(int(when)+1)+'-01-01' if len(when)==4 else when)
            if word=='after' and len(when)>4:
                from datetime import timedelta
                plan.start=(date.fromisoformat(when)+timedelta(days=1)).isoformat()
        else:
            plan.end = (str(int(when)-1)+'-12-31') if len(when)==4 else when
            if len(when)>4:
                from datetime import timedelta
                plan.end=(date.fromisoformat(when)-timedelta(days=1)).isoformat()
        return ' '
    try:
        rest = re.sub(r'\b(in|since|after|before)\s+(20\d\d(?:-\d\d-\d\d)?)', bound, rest)
        if plan.start: date.fromisoformat(plan.start)
        if plan.end: date.fromisoformat(plan.end)
        if plan.start and plan.end and plan.start>plan.end: raise ValueError()
    except ValueError:
        plan.problem='Please use a valid authorisation date range, for example between 2020 and 2025.'
        return plan
    if re.search(r'\breported\b|原文披露', rest):
        plan.reported_only=True
        rest=re.sub(r'reported only|only reported|explicitly reported|\breported\b|原文披露',' ',rest)
    patterns = [
        ('asd','Non-ASD',r'\bnon[- ]asd\b'),
        ('asd','ASD',r'\basds?\b|amorphous solid dispersions?|无定形固体分散体'),
        ('salt','Non-salt',r'\bnon[- ]salts?\b|非盐'),
        ('salt','Salt',r'\bsalts?\b|盐型|盐'),
        ('polymer','HPMCAS',r'\bhpmcas\b|hypromellose acetate succinate|hydroxypropyl methylcellulose acetate succinate'),
        ('polymer','HPMC',r'\bhpmc\b|\bhypromellose\b'),
        ('polymer','HPC',r'\bhpc\b|hydroxypropyl cellulose'),
        ('polymer','Copovidone',r'\bcopovidone\b|\bpvp[- /]?va\b|共聚维酮'),
        ('polymer','Povidone',r'\bpovidone\b|\bpvp\b'),
        ('process','Spray drying',r'spray[- ](?:drying|dried|dry)|喷雾干燥|喷干'),
        ('process','Hot-melt extrusion',r'hot[- ]melt extru\w+|\bhme\b|热熔挤出'),
        ('form','Tablet',r'\btablets?\b|片剂'),
        ('form','Capsule',r'\bcapsules?\b|胶囊'),
        ('form','Oral solution',r'oral solutions?|口服溶液'),
        ('pka','Reported',r'(?:reported |numerical )?\bpka\b'),
    ]
    for key,value,pattern in patterns:
        if re.search(pattern,rest):
            if key in plan.filters and plan.filters[key]!=value:
                plan.problem='Please ask for one value per property; OR comparisons need separate queries.'
            plan.filters[key]=value
            rest=re.sub(pattern,' ',rest)
    bcs=re.search(r'\bbcs\s*(?:class\s*)?(iv|iii|ii|i|[1-4])\b',rest)
    if bcs:
        plan.filters['bcs']={'i':'1','ii':'2','iii':'3','iv':'4'}.get(bcs[1],bcs[1])
        rest=rest[:bcs.start()]+' '+rest[bcs.end():]
    if 'polymer' in plan.filters:
        if re.search(r'excipients?|辅料',rest):
            plan.filters['excipient']=plan.filters.pop('polymer')
            rest=re.sub(r'excipients?|辅料',' ',rest)
        elif 'asd' not in plan.filters and not re.search(r'carrier|matrix|载体',rest):
            plan.problem='Do you mean use as an ASD carrier or presence as an excipient? For example: "List ASD products using HPMCAS" or "List products with HPMCAS as an excipient".'
    # Explicitly reject unsupported residual conditions (FDA, oncology, counterion subtype,
    # efficacy, negation, etc.), rather than silently broadening a count.
    rest=re.sub(r'\b(?:how|many|number|count|percentage|percent|of|the|a|an|are|is|were|was|have|has|had|been|be|being|do|does|which|what|list|all|total|products?|drugs?|medicines?|medicinal|oral|approved|authori[sz]ed|ema|eu|in|this|dataset|database|cohort|study|with|as|that|and|using|use|uses|used|contain|contains|containing|include|includes|please|show|me|give|their|there|names|formulations?|form|carrier|carriers|polymer|polymers|manufactured|made|produced|by|process|at|least|one|active|ingredient|ingredients|first|new|salted)\b',' ',rest)
    rest=re.sub(r'有多少个|多少个|多少|哪些|药物|产品|批准的|被批准|口服|是|采用|使用|含有|列出|全部|共有|统计|有|的|和|在|比例',' ',rest)
    rest=re.sub(r'\bvalues?\b|\bavailable\b',' ',rest)
    residue=re.sub(r'[\s?.,;:!%()\-]','',rest)
    if residue:
        plan.problem='I cannot safely apply every condition in this question. Supported filters: ASD, salt status, carrier (HPMCAS/HPMC/HPC/copovidone/povidone), spray drying/HME, dosage form, BCS class, pKa availability and EMA first-authorisation dates. Please simplify the question or use the database filters.'
    return plan


def _flatten(value):
    return json.dumps(value,ensure_ascii=False).lower()


def _field_match(product, key, pattern, reported_only):
    fields=[f for f in product['fields'] if f['key']==key]
    valid=[f for f in fields if f['status'] not in ('not_reported','not_applicable') and f['value'] is not None]
    matches=[f for f in valid if re.search(pattern,_flatten(f['value']),re.I)]
    if reported_only: matches=[f for f in matches if f['status']=='reported']
    if matches: return True, matches
    return (False if valid and not reported_only else None), []


def execute(plan, products):
    if plan.problem:return {'kind':'clarification','message':plan.problem,'plan':plan.public()}
    scoped=[p for p in products if (not plan.start or p['metadata']['first_approval_date']>=plan.start) and (not plan.end or p['metadata']['first_approval_date']<=plan.end)]
    rows=[];uncertain=[];excluded=[]
    distribution=Counter()
    for p in scoped:
        salt=salt_record(p)
        if 'salt' in plan.filters:distribution[salt['status']]+=1
        checks=[];details=[];refs=set();bases=[]
        for key,value in plan.filters.items():
            if key=='asd':
                label=assessment(p); checks.append(None if label=='Insufficient evidence' else label==value)
                fields=[f for f in p['fields'] if f['key']=='asd']
                explicit=[f['status']=='reported' and f['value']==value for f in fields]
                reported=(any(explicit) if value=='ASD' else bool(explicit) and all(explicit))
                if plan.reported_only and checks[-1] is True and not reported:checks[-1]=None
                details.append('ASD: '+label)
                bases.append('Reported' if reported else basis(p))
                refs.update(p['id'].rsplit('/',1)[-1]+':p'+str(e['page']) for f in fields for e in f.get('evidence',[]))
            elif key=='salt':
                label=salt['status']; checks.append(label==value if label in ('Salt','Non-salt') else None)
                positive=[c for c in salt['components'] if c['status']==value]
                if plan.reported_only and any(c is True for c in checks[-1:]):
                    checks[-1]=True if any(c['basis']=='Reported' for c in positive) else None
                details.append('Salt status: '+label)
                bases.extend(c['basis'] for c in positive)
                for c in salt['components']:
                    refs.update(p['id'].rsplit('/',1)[-1]+':p'+str(page) for page in c['pages'])
            elif key=='polymer':
                if assessment(p)!='ASD':
                    checks.append(None if assessment(p)=='Insufficient evidence' else False);continue
                carrier=carrier_review(p); pattern=r'\b'+re.escape(value)+r'\b'
                found=bool(re.search(pattern,carrier['ASD carrier'],re.I))
                checks.append(None if carrier['Carrier basis']=='Not disclosed' or (plan.reported_only and carrier['Carrier basis']!='Reported') else found)
                details.append('Carrier: '+carrier['ASD carrier']);bases.append(carrier['Carrier basis'])
                for f in p['fields']:
                    if f['key'] in ('asd_carrier','excipients'):
                        refs.update(p['id'].rsplit('/',1)[-1]+':p'+str(e['page']) for e in f.get('evidence',[]))
            else:
                polymer_patterns={'HPMCAS':r'\bhpmcas\b|hypromellose acetate succinate|hydroxypropyl methylcellulose acetate succinate|醋酸.*琥珀酸',
                                  'HPMC':r'\bhpmc\b|hypromellose(?! acetate)|hydroxypropyl methylcellulose(?! acetate)',
                                  'HPC':r'\bhpc\b|hydroxypropyl cellulose',
                                  'Copovidone':r'\bcopovidone\b|\bpvp[- /]?va\b|共聚维酮',
                                  'Povidone':r'\bpovidone\b|\bpvp\b(?![- /]?va)'}
                spec={'process':('asd_process' if plan.filters.get('asd')=='ASD' else 'dp_process',r'spray[- ]?(?:dry|dried)|喷干|喷雾干燥' if value=='Spray drying' else r'hot[- ]melt|extrusion|热熔|挤出'),
                      'excipient':('excipients',polymer_patterns.get(value,'')),
                      'form':('dp_form',{'Tablet':r'tablet|片剂','Capsule':r'capsule|胶囊','Oral solution':r'oral solution|口服溶液'}.get(value,'')),
                      'bcs':('bcs',r'\b(?:class\s*)?(?:'+{'1':'I|1','2':'II|2','3':'III|3','4':'IV|4'}.get(value,'')+r')\b'),
                      'pka':('pka',r'\d')}[key]
                match, fs=_field_match(p,*spec,plan.reported_only)
                checks.append(match); details.append(key+': '+value)
                for f in fs:
                    bases.append(STATUS[f['status']]);refs.update(p['id'].rsplit('/',1)[-1]+':p'+str(e['page']) for e in f.get('evidence',[]))
        row={'Product':p['product'],'First authorisation':p['metadata']['first_approval_date'],
             'Result':'; '.join(details) or 'In selected cohort','Evidence basis':'; '.join(sorted(set(bases))) or 'Saved review',
             'CMC references':'; '.join(sorted(refs)),'EMA ID':p['id']}
        if 'salt' in plan.filters:
            row['Component assignments']='; '.join(c['component']+': '+c['status']+' ('+c['basis']+')' for c in salt['components']) or 'No CMC record'
            row['Salt scope notes']='; '.join(dict.fromkeys(c['note'] for c in salt['components']))
        if any(x is False for x in checks):excluded.append(row)
        elif any(x is None for x in checks):uncertain.append(row)
        else:rows.append(row)
    title=f"{len(rows)} of {len(scoped)} products match the supported filters."
    if re.search(r'percent|比例',plan.question,re.I) and scoped:title+=f" This is {len(rows)/len(scoped):.1%} of the selected cohort."
    if uncertain:title+=f" {len(uncertain)} unresolved or special-case products are shown separately."
    return {'kind':'catalogue','question':plan.question,'answer':title,'plan':plan.public(),'matched':rows,
            'uncertain':uncertain,'excluded_count':len(excluded),'denominator':len(scoped),
            'salt_distribution':dict(distribution),'method':'Complete scan of saved structured records; no model call.',
            'scope':'Selected EMA oral cohort, snapshot 20 September 2026. One product counts once; this is not a count of unique molecules or all EMA medicines. Dates mean first EU centralised authorisation. In combination products, different filters may match different API components. Carrier queries use the ASD review, including labelled inferences unless reported-only is requested.',
            'salt_policy':'Any active ingredient with an unambiguous salt assignment qualifies. Excipients do not count. Stage-dependent conversions, coordination/inorganic complexes, unknown and not-applicable records are shown separately, not classified as non-salts. Hydrates/solvates alone do not imply salt.'}
