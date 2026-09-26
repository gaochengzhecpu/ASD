# EMA Oral ASD Formulations

[Public website](https://ema-approved-asd.streamlit.app/) · Chengzhe Gao

A formulation-first explorer of public EMA CMC evidence. The 20 September 2026
snapshot contains 351 selected oral products, 350 CMC records and 435 structure
images. Generics, hybrids and biosimilars are excluded; this is not an NME count.

## Pages

- ASD formulations: 39 review assessments, with dosage form, strength, carrier,
  process, excipients and distinct drug-loading denominators.
- Oral product database: one ASD / Non-ASD / Insufficient evidence assessment, product
  details, source pages and English CSV exports.
- CMC evidence search: BM25 plus product/property retrieval and worked examples.
  This is the retrieval component of RAG, without live generation.
- Literature comparison: 259 FDA-overlap products, 27 ASD agreements, 5 potential
  literature omissions and 2 formulation mismatches.
- About: scope, limitations, acknowledgements and version history.

The single assessment consolidates the completed Codex record review; it is not
an independent or blind evaluation. Carrier assignments are labelled Reported or Inferred. The inferred carrier panel includes saved source excerpts and a rationale; original extraction values are unchanged. Amorphous
silica adsorbates are excluded from the organic-matrix ASD category.

## Evidence and English display

The original evidence bundle is unchanged. presentation.py adds English display
values, formulation summaries and review explanations. Existing English values
are retained. For untranslated Chinese values, the original English CMC quotation
is shown as Source wording. These are excerpts, not asserted translations, and
can be less complete than the original narrative. Original component-level ASD
fields remain archived; the page presents one consolidated product assessment.

Not listed in the paper does not establish non-ASD. The five possible omissions
remain reference disagreements, not automatically corrected ground-truth labels.
First authorisation year does not date every subsequent formulation change.
The website is not a clinical dosing resource.

## Run and test

Python 3.11+ with SQLite FTS5:

    pip install -r requirements.txt
    streamlit run app.py
    python -m unittest discover -s tests -v

The app expands evidence_bundle.zip into a temporary directory. It includes the
public data and structure images. No secrets or model credentials are required.
The old gemini_epar_analysis.xlsx is historical and is not loaded by the app.
Tests cover source consistency, English output, reference discrepancies, missing
data, complete catalog scans and Streamlit interactions.

## Acknowledgements

Thank you to my wife Xiuli Li for her support; Tianyi Li, Yongjian Wang, Fan Meng
and Zoe Wen for brainstorming; Fady Ibrahim for encouragement; and Kevin J.
Edgar, Lynne Taylor and Tze Ning Hiew for inspiring my work on amorphous solid
dispersions. Restored from the earlier website acknowledgements.
