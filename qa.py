"""Question routing: exhaustive data queries, missing-data answers, grounded explanations."""
import json
import re
import retrieval
import generation
import catalogue


def prepare(question, products, product=None, method='hybrid'):
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
