# EMA ASD & CMC Evidence

Public Streamlit research prototype: https://ema-approved-asd.streamlit.app/

## September 2026 update

- Corpus snapshot: **2026-09-20**, website update: **2026-09-26**.
- **351 selected oral products**, 350 completed CMC extractions; Etcamah lacks a public CMC source in the snapshot.
- **9,254 fields, 2,434 CMC pages, 435 structure images**.
- **39 working ASD products = 28 original extraction labels + 11 later likely-ASD interpretations**. These are not independently confirmed prevalence. Original labels are preserved.
- Frozen 259-product FDA-overlap comparison: 29 paper-mapped ASD positives, 230 assumed negatives. V1/V2/V3 scope and unresolved cases are shown explicitly.
- Local BM25 + structured-field retrieval, complete catalog filters, page-level evidence, and 24 saved Codex answers plus 4 stress cases. No runtime model API, embedding service, credentials or paid calls.

## Run locally

Python 3.11+ with SQLite FTS5:

```sh
pip install -r requirements.txt
streamlit run app.py
python -m unittest discover -s tests -v
```

The app expands `evidence_bundle.zip` into a temporary directory once per server process. It includes all data and structure images (under 25 MB compressed for browser upload). Streamlit Community Cloud can keep its existing `main` branch and `app.py` entry point. No secrets are needed. `gemini_epar_analysis.xlsx` is the historical July artifact, retained for provenance; the updated application does not load it.

## Interview walkthrough (3–4 minutes)

1. **Overview:** explain 351 products and the 28 + 11 label distinction.
2. **CMC database → Palsonify:** inspect DS, DP and ASD separately; open Structures and Source pages. Compare with Rhapsido's retained crystals.
3. **Evidence search:** retrieve `What are the ASD carrier and manufacturing process of Sotyktu?` and inspect the source page.
4. **Complete catalog:** HPMCAS → 14 matches; restrict to `reported` → 7 products. Explain that matching a polymer does not establish its role.
5. **Saved answer examples:** Palsonify pKa demonstrates appropriate abstention. These are recorded Codex answers, not live generation.
6. **Benchmark & validation:** show formulation mismatch and the limits of internal regression testing.

## Evidence and evaluation boundaries

The cohort excludes generics, biosimilars and hybrids; it is not a count of new molecular entities or all EMA approvals. Historic authorisation does not imply current marketing availability. Source crops may describe earlier formulations. Later record-only review is separate from original extraction. Field statuses preserve reported, partly reported, interpreted, not reported and not applicable.

24-question required-field coverage improved from 20/24 to 24/24 during development. This is not answer accuracy or blind validation. The same Codex conversation generated and reviewed saved answers. Independent scientific adjudication and held-out evaluation remain necessary.

Saved regulatory text is evidence, not instructions. The website does not provide clinical dosing advice. Public sources are linked to official EMA product pages; source filenames and hashes are retained without local machine paths.
