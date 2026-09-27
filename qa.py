"""Question routing: exhaustive data queries, missing-data answers, grounded explanations."""
import json
import re
import retrieval
import generation
import catalogue


def prepare_routed(question, products, decision, method='hybrid'):
    """Execute the model's validated plan directly, without re-parsing its English."""
    import router
    from presentation import assessment, carrier_review, english_value, entity_name, STATUS
    from data_access import FIELD_LABELS
    d=router.validate(decision,products)
    routing={'route':d['route'],'operation':d['operation'],
             'interpreted_question':d['normalized_question'],'corrections':d['corrections']}
    if d['route']=='clarify':
        return {'kind':'clarification','message':d['clarification'],'routing':routing}
    if d['route']=='database':
        selected=[p for p in products if not d['product_names'] or p['product'] in d['product_names']]
        if d['operation']!='lookup':
            plan=catalogue.Plan(kind='catalogue',question=question,filters=d['filters'],
                                start=d['start'],end=d['end'],reported_only=d['reported_only'])
            result=catalogue.execute(plan,selected)
            if d['operation']=='percentage' and result['denominator'] and '%' not in result['answer']:
                result['answer']+=f" Matching products are {len(result['matched'])/result['denominator']:.1%} of this scope."
            result['method']='Structured database query · Code counts the complete saved records; no model-generated totals.'
            result['routing']=routing
            if d['product_names']:result['scope']+=' Product scope: '+', '.join(d['product_names'])+'.'
            return result
        records=[];lines=[]
        with retrieval.connect() as conn:
            for p in selected:
                prefix=p['id'].rsplit('/',1)[-1]
                if not p['fields']:
                    lines.append(p['product']+': no public CMC document is available in this dataset snapshot.');continue
                facts=[retrieval.fact_out(f) for f in conn.execute('SELECT * FROM facts WHERE product_id=?',(p['id'],))]
                for key in d['fields']:
                    if key=='asd' or (key=='asd_carrier' and assessment(p)=='ASD'):
                        if key=='asd':value=assessment(p);status='Saved review interpretation'
                        else:
                            review=carrier_review(p);value=review['ASD carrier'];status=review['Carrier basis']
                        ident=prefix+':r1'
                        records.append({'id':ident,'product':p['product'],'kind':'Saved review interpretation',
                                        'field':key,'value':value,'status':status})
                        lines.append(f"**{p['product']} — {FIELD_LABELS[key]}:** {value} ({status}) [{ident}].")
                        continue
                    found=[f for f in facts if f['key']==key]
                    if not found:
                        lines.append(f"**{p['product']} — {FIELD_LABELS[key]}:** no saved value is available.");continue
                    for f in found:
                        original=next(x for x in p['fields'] if x['key']==key and x.get('entity','')==f.get('entity',''))
                        value,origin=english_value(p,original)
                        component=entity_name(f.get('entity',''))
                        if f['status']=='not_reported':value='Not reported in the saved CMC extraction'
                        elif f['status']=='not_applicable':value='Not applicable in the saved CMC extraction'
                        record={'id':f['id'],'product':p['product'],'kind':'Saved extraction','field':key,
                                'component':component,'value':value,'status':f['status'],
                                'source_ids':[e['page_id'] for e in f.get('evidence',[]) if e.get('quote_verified')]}
                        records.append(record)
                        label=p['product']+(' · '+component if component else '')
                        status=STATUS.get(f['status'],f['status'])+('; Source wording' if origin=='Source wording' else '')
                        lines.append(f"**{label} — {FIELD_LABELS[key]}:** {value} ({status}) [{f['id']}].")
        return {'kind':'direct','question':question,'answer':'\n\n'.join(lines),'records':records,
                'method':'Structured record lookup · No answer-generation call.',
                'scope':'Saved CMC records and current review. Not reported does not mean absent from every public source.',
                'routing':routing}
    result=retrieval.query(d['normalized_question'],fields=d['fields'] or None,
                           product_names=d['product_names'] or None,method=method)
    if result['target_products'] and all(p['status']!='completed' for p in result['target_products']) and not result['contexts']:
        return {'kind':'direct','question':question,'answer':'No public CMC source is available for '+', '.join(p['product'] for p in result['target_products'])+' in this snapshot.',
                'records':[],'method':'Source availability check · No answer-generation call.','routing':routing}
    pack=generation.evidence_pack(result,products);pack['original_question']=question
    return {'kind':'evidence','question':question,'pack':pack,'result':result,'routing':routing}


def prepare(question, products, product=None, method='hybrid'):
    """Legacy offline rules for command-line regression comparison; not the AI-answer route."""
    if not question.strip() or len(question)>1500:
        return {'kind':'clarification','message':'Please enter a question of 1–1,500 characters.'}
    with retrieval.connect() as conn:
        entities=conn.execute('SELECT * FROM products ORDER BY ord').fetchall()
        named=retrieval.names_in_query(question,entities)
    plan=catalogue.plan_question(question,named_product=bool(named))
    if plan.kind=='catalogue':
        if product:return {'kind':'clarification','message':'A complete cohort query needs Focus on a product set to Automatic. Please clear the product focus so the denominator is unambiguous.'}
        return catalogue.execute(plan,products)
    if re.search(r'\bfda\b|\bbenchmark\b|\bpaper\b|\bliterature\b',question,re.I):
        return {'kind':'clarification','message':'This question needs the literature/FDA comparison, which is outside the CMC-only answer context. Please use the Literature comparison section for the 259-product comparison, potential omissions and formulation mismatches.'}
    if not named and not product:
        unknown=re.search(r'\b(?:of|for|about)\s+([A-Z][a-zA-Z-]{4,})\b',question)
        if unknown and unknown[1].lower() not in {'hpmcas','hpmc','copovidone','povidone','hypromellose','crystalline','amorphous'}:
            return {'kind':'clarification','message':f'The product name "{unknown[1]}" was not resolved in this cohort. Please select the intended product or confirm its spelling.'}
    if not named and not product and not re.search(r'cmc|formulat|excipient|drug|medicine|polymer|crystal|amorphous|dispersion|manufactur|\basd\b|solub|dissol|salt|pka|tablet|capsule|release|stabili|\bbcs\b|spray|extrusion|carrier|药|工艺|制剂|聚合物|盐|晶|喷干',question,re.I):
        return {'kind':'clarification','message':'Please ask a formulation or CMC question about the selected EMA oral products.'}
    result=retrieval.query(question,product=product,method=method)
    if result['product_suggestions'] and not result['target_products']:
        return {'kind':'clarification','message':'Please confirm the product using Focus on a product. Possible spelling: '+', '.join(result['product_suggestions'])}
    if result['target_products'] and all(not p['status']=='completed' for p in result['target_products']) and not result['facts'] and not result['contexts']:
        names=', '.join(p['product'] for p in result['target_products'])
        return {'kind':'direct','question':question,'answer':f'{names}: no public CMC document is available in this dataset snapshot. The requested property cannot be determined.','records':[],'method':'Source availability check; no model call.'}
    pack=generation.evidence_pack(result,products)
    # Missing-property answers cite an extraction record, not a fabricated primary quotation.
    if result['requested_fields'] and result['facts'] and all(f['status'] in ('not_reported','not_applicable') for f in result['facts']):
        messages=[]
        for item in pack['derived_records']:
            if item['kind']!='Saved extraction':continue
            label='not reported' if item['status']=='not_reported' else 'not applicable'
            messages.append(f"{item['product']} — {item['field']}: {label} in the saved CMC extraction [{item['id']}].")
        return {'kind':'direct','question':question,'answer':'\n\n'.join(messages),
                'records':pack['derived_records'],'method':'Saved missing-value records; no model call.',
                'scope':'Not reported means absent from this extraction/document scope, not proven absent from every public source.'}
    return {'kind':'evidence','question':question,'pack':pack,'result':result}
