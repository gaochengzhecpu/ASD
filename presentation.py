"""English presentation of saved evidence; original records remain unchanged.

The single assessment consolidates the previously completed record review.
It is not a fresh EPAR review or an independently validated model prediction.
"""
import re
from data_access import FIELD_LABELS, flat_value

CJK = re.compile(r'[\u3400-\u9fff]')
ENTITY_NAMES = {
    '产品': '', 'lenacapavir（口服）': 'lenacapavir (oral)',
    'alpelisib 薄膜包衣片': 'alpelisib film-coated tablets',
    'alpelisib 袋装颗粒': 'alpelisib granules in sachets',
    'alpelisib（两种口服DP共用DS）': 'alpelisib (DS shared by both oral formulations)',
}
OMISSIONS = ['Votubia', 'Gavreto', 'Zokinvy', 'Vanflyta']
# Review reclassifications of the saved working label; the original records remain unchanged.
RECLASSIFIED = {'Tavneos': 'Non-ASD'}
MISMATCHES = ['Xtandi', 'Lynparza']
STATUS = {'reported':'Reported', 'partly_reported':'Partly reported',
          'interpretation':'Interpretation', 'not_reported':'Not reported',
          'not_applicable':'Not applicable'}

# Explicit English consolidation of the prior assessments, with their limitations.
REASONS = {
 'Jinarc': 'ASD is the review conclusion from a stable amorphous tolvaptan intermediate and its tablet route. Polymer co-dispersion is not directly disclosed; HPC is a candidate carrier, not a confirmed assignment.',
 'Epclusa': 'The review assigns ASD to the velpatasvir component using its amorphous functional intermediate and solution/drying route. Copovidone is a candidate; its intermediate role is not disclosed. Sofosbuvir is not assigned ASD.',
 'Zepatier': 'Separate spray-dried intermediates and the polymer-containing formulation support the prior ASD assessment. The final phase and the carrier assignment for each API are not directly disclosed.',
 'Vosevi': 'The review assigns ASD at product level from the amorphous velpatasvir component and two solution/drying intermediates. It does not establish that every API is ASD. Sofosbuvir is added separately.',
 'Braftovi': 'ASD is an inference from the functional intermediate and its solid-state controls. The saved CMC record does not directly disclose the final amorphous dispersion, carrier or preparation method.',
 'Pifeltro': 'A separate spray-dried intermediate, HPMCAS in the formulation and downstream tablet manufacture support the prior ASD assessment. Polymer co-dispersion and final amorphicity are not directly disclosed.',
 'Erleada': 'The prior ASD assessment is an inference from HPMCAS, a functional intermediate and solid-state dependence of bioavailability. The intermediate phase and preparation method are not disclosed; evidence is limited.',
 'Paxlovid': 'The review assigns ASD to the ritonavir tablet based on copovidone, premix manufacture and hot-melt extrusion. Final amorphicity is not directly stated in this record. Nirmatrelvir is not assigned ASD.',
 'Tibsovo': 'The prior ASD assessment is an inference from the functional intermediate, HPMCAS and the limited relevance of input-DS crystallinity to bioavailability. The intermediate phase and preparation method are not disclosed; evidence is limited.',
 'Aquipta': 'Polymer/surfactant development and hot-melt extrusion support the prior ASD assessment. The final amorphous phase and the specific carrier role are not directly disclosed.',
 'Welireg': 'API dissolution in acetone, spray drying and HPMCAS in the formulation support the prior ASD assessment. Polymer co-dissolution and final amorphicity are not directly disclosed.',
 'Twynsta': 'The commercial telmisartan intermediate and final phase are not disclosed. Povidone and alkalising excipients alone cannot establish ASD.',
 'Komboglyze': 'Saxagliptin is dissolved and incorporated into an active film coat, but its final phase and dispersion structure are not disclosed.',
 'Constella': 'An amorphous peptide is layered onto beads with HPMC. The record does not establish an ASD in the final drug layer.',
 'Duavive': 'The record does not resolve the dispersion structure of the lactose-diluted oestrogens or the amorphous/crystalline balance in the bazedoxifene coating.',
 'Qtrilmet': 'The final phase of saxagliptin in the active coating is not disclosed. Conclusions about the other components do not resolve this gap.',
 'Evotaz': 'Cobicistat is an amorphous silica adsorbate, outside the ASD category used here. The saved record also leaves the final atazanavir phase unresolved; excluding the cobicistat adsorbate does not establish a non-ASD conclusion for the entire combination.',
 'Xtandi': 'The reviewed EPAR describes the earlier liquid-filled soft capsule. The paper-mapped ASD is the later tablet: these are different formulations.',
 'Lynparza': 'The reviewed EPAR describes the earlier crystalline solid-dispersion capsule. The paper-mapped ASD is the later tablet: these are different formulations.',
 'Votubia': 'Amorphous everolimus, an HPMC solid dispersion and crystallinity controls jointly support ASD. The conclusion is an interpretation of those statements.',
 'Deltyba': 'A polymer-matrix dispersion, comparison against a crystalline formulation and crystallinity controls support ASD as an interpretation.',
 'Delstrigo': 'Doravirine and HPMCAS are spray-dried from a common solution, supporting ASD as an interpretation. Lamivudine and tenofovir disoproxil are not assigned ASD.',
 'Ojemda': 'An excipient-containing extruded intermediate converts crystalline tovorafenib to amorphous material. ASD is the review interpretation for both oral forms; the carrier role and melting step are not directly disclosed.',
 'Gavreto': 'The CMC record explicitly describes an amorphous dried dispersion and spray drying. Crystalline input DS does not contradict the final dispersion.',
 'Tavneos': 'Reclassified as non-ASD. The EPAR describes avacopan in amorphous form as a solid solution in the capsule, made by dissolving it in molten excipients (PEG 4000 / macrogolglycerol hydroxystearate), filling and solidifying. This is a melt-filled amorphous solution in a capsule, not an ASD intermediate: amorphous is not the same as ASD. The earlier working label (ASD) is kept in the original record.',
 'Zokinvy': 'The CMC record explicitly describes an amorphous solid dispersion of lonafarnib stabilised in a povidone matrix.',
 'Vanflyta': 'The CMC record explicitly describes an amorphous solid dispersion with hydroxypropyl-beta-cyclodextrin.',
}

# Compact formulation summaries derived from the saved fields, not external memory.
# Candidate carrier assignments stay qualified even when the product assessment is ASD.
FORMULATION = {
 'Votubia': ('HPMC', 'Not disclosed'),
 'Incivo': ('HPMCAS', 'Spray drying; secondary drying'),
 'Zelboraf': ('HPMCAS', 'Co-precipitation'),
 'Kalydeco': ('HPMCAS', 'Spray drying; secondary drying'),
 'Stivarga': ('Povidone (candidate)', 'Co-precipitate; preparation method not disclosed'),
 'Deltyba': ('HPMCP (candidate)', 'Polymer-matrix intermediate; method not disclosed'),
 'Harvoni': ('Copovidone (candidate for ledipasvir)', 'Spray drying from ethanolic solution'),
 'Viekirax': ('Copovidone', 'Hot-melt extrusion; separate API extrudates'),
 'Jinarc': ('HPC (candidate)', 'Amorphous powder intermediate; method not disclosed'),
 'Orkambi': ('HPMCAS (candidate for ivacaftor)', 'Spray drying; secondary drying'),
 'Epclusa': ('Copovidone (candidate for velpatasvir)', 'Feed solution; drying; secondary drying. Drying type not disclosed'),
 'Zepatier': ('Copovidone / HPMC (candidates; per-API assignment not disclosed)', 'Separate spray drying of each API intermediate'),
 'Venclyxto': ('Copovidone, K value 28', 'Not disclosed'),
 'Maviret': ('Not disclosed', 'Separate ASD intermediates; preparation method not disclosed'),
 'Vosevi': ('Copovidone (candidate; per-API assignment not disclosed)', 'Two feed solutions; drying; secondary drying. Drying type not disclosed'),
 'Braftovi': ('Not disclosed', 'Not disclosed'),
 'Symkevi': ('Ivacaftor: HPMCAS; tezacaftor: HPMC (candidate)', 'Separate spray-dried intermediates'),
 'Delstrigo': ('Doravirine: HPMCAS', 'Spray drying from API / HPMCAS solution'),
 'Pifeltro': ('HPMCAS (candidate)', 'Spray drying'),
 'Erleada': ('HPMCAS (candidate)', 'Not disclosed'),
 'Kaftrio': ('Stabilising polymers; per-API identities not disclosed', 'Separate spray drying of ivacaftor and tezacaftor; secondary drying'),
 'Tukysa': ('Copovidone (candidate)', 'Spray drying; secondary drying'),
 'Gavreto': ('Not disclosed', 'Spray drying'),
 'Qinlock': ('HPMCAS', 'Spray drying'),
 'Tavneos': ('PEG 4000 / macrogolglycerol hydroxystearate matrix', 'Dissolution in molten excipients; capsule filling and solidification'),
 'Paxlovid': ('Ritonavir: copovidone (candidate)', 'Ritonavir: hot-melt extrusion'),
 'Zokinvy': ('Povidone K30', 'Spray drying; secondary tray drying'),
 'Sunlenca': ('Two excipients; identities not disclosed in this record', 'Spray drying'),
 'Sotyktu': ('HPMCAS, H grade', 'Spray drying from acetone / water'),
 'Tibsovo': ('Not disclosed', 'Not disclosed'),
 'Aquipta': ('PVP/VA copolymer (candidate)', 'Hot-melt extrusion'),
 'Jaypirca': ('HPMCAS', 'Spray drying; secondary drying'),
 'Vanflyta': ('Hydroxypropyl-beta-cyclodextrin', 'Spray drying from aqueous feed'),
 'Voydeya': ('HPMCAS', 'Spray drying; secondary drying'),
 'Welireg': ('HPMCAS (candidate)', 'API dissolution in acetone; spray drying'),
 'Alyftrek': ('HPMC / HPMCAS (candidates; per-SDD assignment not disclosed)', 'Separate spray drying of deutivacaftor and tezacaftor; secondary drying'),
 'Yeytuo': ('Copovidone with poloxamer 407', 'Spray drying; secondary drying'),
 'Ojemda': ('Copovidone (candidate)', 'Extrusion; hot-melt interpretation, melting step not explicitly stated'),
 'Palsonify': ('Not disclosed', 'Spray drying from methanol; secondary drying'),
}

OVERRIDES = {
 ('Maviret','dp_form'): 'Immediate-release fixed-dose combination film-coated tablet',
 ('Maviret','strength'): 'Glecaprevir 100 mg + pibrentasvir 40 mg per tablet',
 ('Braftovi','dp_form'): 'Immediate-release hard gelatin capsule',
 ('Braftovi','strength'): '50 mg or 75 mg per capsule; 100 mg was a development strength',
 ('Delstrigo','dp_form'): 'Immediate-release bilayer film-coated tablet',
 ('Delstrigo','strength'): 'Doravirine 100 mg + lamivudine 300 mg + TDF 300 mg (245 mg tenofovir disoproxil) per tablet',
 ('Kaftrio','dp_form'): 'Immediate-release fixed-dose combination film-coated tablet',
 ('Kaftrio','strength'): 'Ivacaftor 75 mg + tezacaftor 50 mg + elexacaftor 100 mg per tablet',
 ('Gavreto','dp_form'): 'Immediate-release hard capsule containing dry-granulated ASD',
 ('Gavreto','strength'): '100 mg per capsule',
 ('Tavneos','dp_form'): 'Immediate-release hard capsule containing an amorphous solid solution',
 ('Tavneos','strength'): '10 mg per capsule',
 ('Sunlenca','dp_form'): 'Immediate-release film-coated oral tablet',
 ('Sunlenca','strength'): '300 mg lenacapavir (306.8 mg sodium salt) per tablet',
 ('Sotyktu','dp_form'): 'Immediate-release film-coated tablet',
 ('Sotyktu','strength'): '6 mg per tablet',
 ('Tibsovo','dp_form'): 'Film-coated oral tablet; non-functional coating',
 ('Tibsovo','strength'): '250 mg per tablet',
 ('Voydeya','dp_form'): 'Immediate-release film-coated tablet',
 ('Voydeya','strength'): '50 mg or 100 mg per tablet',
 ('Welireg','dp_form'): 'Immediate-release film-coated tablet',
 ('Welireg','strength'): '40 mg per tablet',
 ('Palsonify','dp_form'): 'Immediate-release film-coated tablet',
 ('Palsonify','strength'): '20 mg or 30 mg paltusotine (as hydrochloride) per tablet',
 ('Pemazyre','dose_regimen'): 'QTPP development target: maximum 13.5 mg once daily. Cycle, treatment breaks and dose adjustments are not specified.',
 ('Orserdu','dose_regimen'): 'QTPP development target: maximum 400 mg once daily. The salt/free-base basis is unclear; this is not a verified clinical regimen.',
 ('Welireg','dose_regimen'): 'QTPP development target: maximum 200 mg once daily. This is not a verified current clinical regimen.',
 ('Cenrifki','dose_regimen'): 'QTPP development target: once daily. Tablet count per dose and dose-adjustment regimen are not specified.',
}

# Product-level carrier interpretations from the already saved CMC records.
# Do not overwrite the original extraction or assign undisclosed FDC polymers to APIs.
CARRIER_REVIEW = {
 'Maviret': ('Copovidone (K28)', 'The tablet core contains copovidone K28 and each API has a separate ASD intermediate. Copovidone is inferred as the matrix polymer; the record does not assign the excipients to each intermediate.'),
 'Braftovi': ('Copovidone', 'Copovidone is listed in the capsule contents alongside poloxamer 188 and a functional intermediate is described. Copovidone is the inferred matrix polymer; poloxamer 188 is not independently assigned as a carrier.'),
 'Kaftrio': ('HPMC / HPMCAS', 'The core contains HPMC and HPMCAS, and the ivacaftor and tezacaftor spray-dried dispersions use stabilising polymers. These are inferred carrier candidates; the individual API-to-polymer assignments remain unresolved.'),
 'Gavreto': ('HPMC', 'Hypromellose is listed in the capsule contents, separately from the capsule shell, and an amorphous spray-dried dispersion is reported. HPMC is therefore inferred as the matrix polymer.'),
 'Sunlenca': ('Copovidone', 'Copovidone is listed in the tablet core and lenacapavir is spray-dried with two excipients. Copovidone is the inferred polymer; the second co-sprayed excipient is not identified. No assignment is borrowed from Yeytuo.'),
 'Tibsovo': ('HPMCAS', 'HPMCAS is listed in the core, distinct from HPMC in the film coat. It is the inferred carrier for the functional intermediate; both the carrier role and the ASD phase remain interpretations.'),
 'Palsonify': ('Copovidone', 'Copovidone is listed in the core, while HPMC is in the film coat. Together with the methanolic spray-drying route, this supports copovidone as the inferred matrix polymer.'),
}


def carrier_review(p):
    """Return one readable assignment, its uncertainty and the saved source trail."""
    name = p['product']
    original = FORMULATION[name][0]
    if name in CARRIER_REVIEW:
        polymer, note = CARRIER_REVIEW[name]
        evidence = 'Inferred'
    else:
        polymer = original.replace(' (candidate)', '').replace('(candidate for ', '(')
        polymer = polymer.replace('(candidates; ', '(').replace('(candidate; ', '(')
        inferred = 'candidate' in original.lower() or any(
            f['key']=='asd_carrier' and f['status']=='interpretation' for f in p['fields'])
        evidence = 'Inferred' if inferred else 'Reported'
        note = ('Carrier role is inferred from the saved formulation and excipient evidence. '
                'Presence in the formulation alone does not confirm co-dispersion; any unresolved component assignment is retained.'
                if inferred else 'Carrier identity is described in the saved CMC extraction. See the source excerpts for component scope.')
    source_fields = [f for f in p['fields'] if f['key'] in ('asd_carrier', 'excipients', 'asd_process')]
    excerpts = list(dict.fromkeys(e['quote'] for f in source_fields for e in f.get('evidence', []) if e.get('quote')))
    pages = sorted({e['page'] for f in source_fields for e in f.get('evidence', [])})
    return {'ASD carrier': polymer, 'Carrier basis': evidence, 'Carrier rationale': note,
            'Carrier CMC pages': ', '.join(map(str, pages)), 'Carrier source excerpts': '\n'.join(excerpts)}

SHORT_DP = {
 'Votubia': ('Immediate-release tablet','2.5, 5, 10 mg'),
 'Incivo': ('Immediate-release film-coated tablet','375 mg'),
 'Zelboraf': ('Film-coated tablet','240 mg'),
 'Kalydeco': ('Film-coated tablet','150 mg'),
 'Stivarga': ('Immediate-release film-coated tablet','40 mg'),
 'Deltyba': ('Film-coated tablet','50 mg'),
 'Harvoni': ('Immediate-release FDC tablet','Ledipasvir 90 mg / sofosbuvir 400 mg'),
 'Viekirax': ('Immediate-release FDC tablet','Ombitasvir 12.5 mg / paritaprevir 75 mg / ritonavir 50 mg'),
 'Jinarc': ('Immediate-release uncoated tablet','15, 30, 45, 60, 90 mg'),
 'Orkambi': ('Immediate-release FDC tablet','Lumacaftor 200 mg / ivacaftor 125 mg'),
 'Epclusa': ('Immediate-release FDC tablet','Sofosbuvir 400 mg / velpatasvir 100 mg'),
 'Zepatier': ('Immediate-release FDC tablet','Elbasvir 50 mg / grazoprevir 100 mg'),
 'Venclyxto': ('Immediate-release film-coated tablet','10, 50, 100 mg'),
 'Maviret': ('Immediate-release FDC tablet','Glecaprevir 100 mg / pibrentasvir 40 mg'),
 'Vosevi': ('Immediate-release FDC tablet','Sofosbuvir 400 mg / velpatasvir 100 mg / voxilaprevir 100 mg'),
 'Braftovi': ('Immediate-release hard capsule','50, 75 mg'),
 'Symkevi': ('Immediate-release FDC tablet','Tezacaftor 100 mg / ivacaftor 150 mg'),
 'Delstrigo': ('Immediate-release bilayer FDC tablet','Doravirine 100 mg / lamivudine 300 mg / TDF 300 mg'),
 'Pifeltro': ('Immediate-release film-coated tablet','100 mg'),
 'Erleada': ('Immediate-release film-coated tablet','60 mg'),
 'Kaftrio': ('Immediate-release FDC tablet','Ivacaftor 75 mg / tezacaftor 50 mg / elexacaftor 100 mg'),
 'Tukysa': ('Immediate-release film-coated tablet','50, 150 mg'),
 'Gavreto': ('Immediate-release hard capsule','100 mg'),
 'Qinlock': ('Immediate-release uncoated tablet','50 mg'),
 'Tavneos': ('Immediate-release hard capsule','10 mg'),
 'Paxlovid': ('Co-packaged immediate-release tablets','Nirmatrelvir 150 mg; ritonavir 100 mg (separate tablets)'),
 'Zokinvy': ('Immediate-release hard capsule','50, 75 mg'),
 'Sunlenca': ('Immediate-release film-coated oral tablet','300 mg lenacapavir'),
 'Sotyktu': ('Immediate-release film-coated tablet','6 mg'),
 'Tibsovo': ('Film-coated oral tablet','250 mg'),
 'Aquipta': ('Immediate-release tablet','10, 60 mg'),
 'Jaypirca': ('Immediate-release film-coated tablet','50, 100 mg'),
 'Vanflyta': ('Immediate-release film-coated tablet','17.7, 26.5 mg quizartinib'),
 'Voydeya': ('Immediate-release film-coated tablet','50, 100 mg'),
 'Welireg': ('Immediate-release film-coated tablet','40 mg'),
 'Alyftrek': ('Immediate-release FDC tablet','D-IVA / TEZ / VNZ: 50 / 20 / 4 mg or 125 / 50 / 10 mg'),
 'Yeytuo': ('Immediate-release film-coated oral tablet','300 mg lenacapavir'),
 'Ojemda': ('Film-coated tablet; powder for oral suspension','Tablet: 100 mg; suspension: 25 mg/mL (300 mg delivered per bottle)'),
 'Palsonify': ('Immediate-release film-coated tablet','20, 30 mg paltusotine'),
}

def ingredient(p):
    # Correct obvious metadata spelling using the saved component records.
    if p['product']=='Harvoni':return 'ledipasvir / sofosbuvir'
    if p['product']=='Vosevi':return 'sofosbuvir / velpatasvir / voxilaprevir'
    return (p['metadata'].get('inn') or p['metadata'].get('active_substance','')).replace(';',' / ')

def entity_name(value):
    return ENTITY_NAMES.get(value, value or '')

def assessment(p):
    if p['product']=='Evotaz':return 'Insufficient evidence'
    if p['product'] in RECLASSIFIED:return RECLASSIFIED[p['product']]
    return {'ASD':'ASD','Likely ASD':'ASD','Non-ASD':'Non-ASD',
            'Likely non-ASD':'Non-ASD','Inorganic adsorbate':'Non-ASD',
            'Unresolved':'Insufficient evidence','Source unavailable':'Insufficient evidence'}[p['working_label']]

def rationale(p):
    if p['product'] in REASONS:return REASONS[p['product']]
    if not p['fields']:return 'No public CMC source is available in this snapshot; no formulation conclusion can be made.'
    if p['working_label']=='Inorganic adsorbate':
        return 'Cobicistat is an amorphous silica adsorbate. It is excluded from the ASD category used here, which covers drug dispersions in an organic carrier matrix. This does not mean cobicistat is crystalline.'
    if assessment(p)=='Insufficient evidence':return 'The saved CMC record does not resolve the final drug/carrier dispersion state. A categorical ASD or non-ASD conclusion is not supported.'
    if assessment(p)=='ASD':return 'The saved formulation evidence supports an ASD assessment. In a combination product this applies to the ASD component(s), not automatically to every API.'
    return 'The saved drug-substance and product-manufacturing evidence supports a non-ASD assessment for the reviewed formulation. This is a review conclusion, not a claim about every subsequent formulation.'

def basis(p):
    if assessment(p)=='Insufficient evidence':return 'Evidence gap'
    if any(f['key']=='asd' and f['value']=='ASD' and f['status']=='reported' for f in p['fields']):return 'Explicit CMC description'
    return 'Review interpretation'

def english_value(p,f):
    """Preserve English structured values; never pretend source quotes are translations."""
    override=OVERRIDES.get((p['product'],f['key']))
    if override:return override,'English summary'
    value=flat_value(f['value'])
    if f['status']=='not_applicable':return 'Not applicable',''
    if f['value'] is None:return 'Not reported',''
    if not CJK.search(value):return value,'Extracted value'
    quotes=list(dict.fromkeys(e.get('quote','').strip() for e in f.get('evidence',[]) if e.get('quote','').strip()))
    if quotes and not any(CJK.search(q) for q in quotes):
        return ' / '.join(quotes),'Source wording'
    raise ValueError('Missing English presentation: '+p['product']+' / '+f['key'])

def field_text(p,key):
    fs=[f for f in p['fields'] if f['key']==key]
    if not fs:return 'Not available' if not p['fields'] else 'Not reported'
    values=list(dict.fromkeys(english_value(p,f)[0] for f in fs))
    if len(values)==1:return values[0]
    vals=[]
    for f in fs:
        value,origin=english_value(p,f)
        if value=='Not applicable':continue
        ent=entity_name(f.get('entity',''))
        text=(ent+': ' if ent and len(fs)>1 else '')+value
        if text not in vals:vals.append(text)
    return '; '.join(vals) or 'Not applicable'

def product_row(p):
    m=p['metadata']
    return {'Product':p['product'],'Active ingredient':ingredient(p),
            'Year':int(m['first_approval_date'][:4]),'Company':m.get('holder',''),
            'ASD assessment':assessment(p),'Dosage form':SHORT_DP[p['product']][0] if p['product'] in SHORT_DP else field_text(p,'dp_form')}

def formulation_row(p):
    r=product_row(p)
    _,process=FORMULATION[p['product']]
    r.update({'Strength':SHORT_DP[p['product']][1],**carrier_review(p),'ASD preparation':process,
              'DP manufacturing':field_text(p,'dp_process'),'Excipients':field_text(p,'excipients'),
              'API : carrier ratio':field_text(p,'drug_carrier_ratio'),
              'API fraction in ASD':field_text(p,'api_fraction_asd'),
              'API fraction in DP':field_text(p,'api_fraction_dp'),
              'Literature note':'Potential literature omission' if p['product'] in OMISSIONS else '',
              'Assessment basis':basis(p)})
    return r

def english_fields(p):
    rows=[]
    for f in p['fields']:
        if f['key']=='asd':continue  # One product assessment is presented separately.
        value,origin=english_value(p,f)
        rows.append({'Product':p['product'],'ASD assessment':assessment(p),'Component':entity_name(f.get('entity','')),
          'Field':FIELD_LABELS[f['key']],'Value':value,'Evidence':STATUS.get(f['status'],f['status']),
          'Wording':origin,'CMC pages':', '.join(str(e['page']) for e in f.get('evidence',[])),
          'Source excerpts':'\n'.join(e.get('quote','') for e in f.get('evidence',[])),
          'EMA source':p['metadata']['ema_url']})
    return rows

def comparison_rows(products,benchmark):
    lookup={p['id']:p for p in products};rows=[]
    for r in benchmark['rows']:
        p=lookup[r['ema_id']];decision=assessment(p);listed=bool(r['reference_binary'])
        if p['product'] in MISMATCHES:category='Different formulation reviewed'
        elif listed and decision=='ASD':category='ASD in both'
        elif not listed and decision=='ASD':category='Potential literature omission'
        elif decision=='Insufficient evidence':category='CMC evidence unresolved'
        elif p['product'] in RECLASSIFIED:category='Not listed; reclassified non-ASD'
        elif listed:category='Paper ASD; review non-ASD'
        else:category='Not listed; review non-ASD'
        rows.append({'Product':p['product'],'Paper ASD list':'Listed' if listed else 'Not listed',
          'Our CMC assessment':decision,'Comparison':category,
          'Note':rationale(p) if category not in ['ASD in both','Not listed; review non-ASD'] else
                 ('Formulation-level match to Sunlenca; not the Yeytuo brand name in the paper.' if p['product']=='Yeytuo' else '')})
    return rows
