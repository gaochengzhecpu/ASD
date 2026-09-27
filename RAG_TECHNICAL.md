# CMC research assistant: technical design and evaluation

Snapshot: 20 September 2026. Engineering update: 26 September 2026.

## Two question paths

1. **Structured cohort queries.** A conservative parser produces an allowlisted query plan.
   Python scans the complete saved cohort, applies explicit property/date filters and
   counts distinct products. The UI shows the plan, denominator, matching names, evidence
   and unresolved/special cases. No LLM writes or executes SQL or calculates these totals.
2. **Evidence-grounded explanations.** Resolve product names/INNs and requested fields;
   combine keyword and semantic retrieval; attach saved source-linked fields and review
   interpretations; send the bounded evidence to GLM-5.3-Flash through OpenCode Go.
   Missing-value/document responses are deterministic when possible.

```mermaid
flowchart TD
  Q[Question] --> R{Supported cohort query?}
  R -->|Yes| C[Complete structured scan]
  C --> T[Count + denominator + product list + uncertainty]
  R -->|No| P[Product and field routing]
  P --> B[SQLite FTS5 / BM25]
  P --> V[Local BGE vectors / cosine similarity]
  B --> F[Reciprocal rank fusion]
  V --> F
  F --> E[Source pages + extraction records + saved review]
  E --> G[GLM-5.3-Flash]
  G --> A[Citation validation + answer + inspectable sources]
```

## Reproducible retrieval details

- Corpus: 350 CMC documents; 2,434 pages; 6,348 overlapping text chunks; 9,254 fields.
  The 351-product cohort includes one product without a public CMC source.
- Chunking: page-bounded, approximately 1,700 **characters**, 250-character overlap,
  preferring sentence/newline boundaries. This is not a 1,700-token window.
- Embedding: `BAAI/bge-small-en-v1.5`, Qdrant quantized ONNX conversion,
  revision `aa8f8b060edb00e03bfdd08813a2949946c8ba55`, 384 dimensions, 512-token input limit.
  Product names prefix indexed chunks. `passage_embed` and `query_embed` use the same model.
- Storage/search: SQLite retains text and provenance; NumPy stores normalized vectors.
  Exact cosine search is practical for 6,348 chunks, avoiding a separate vector database service.
  Chroma is not used in the current deployment. No learned reranker is implemented.
- Fusion: equal-weight reciprocal rank fusion, score = sum(1/(60 + rank)).
  The raw BM25 and cosine scores are never averaged. Known products constrain both retrievers.
- Context: deduplicate source pages; verified field-linked pages retain full text. Other
  hits retain their chunk text. Page excerpts are not claimed to be complete documents.
  Supply at most eight source passages / 22,000 source characters and 24 field records.
  Round-robin by product prevents one side of a comparison using the whole budget.
- Provenance: `:pN` is a CMC **crop** page; `:fN` is a saved extraction record;
  `:r1` is the current saved-review interpretation. These have different evidence status.
  Corpus and vector hashes prevent accidentally pairing mismatched indexes.
- Runtime: embeddings execute locally on the Streamlit server CPU. No embedding key or
  external embedding service is used. If the local semantic service fails, BM25 remains
  available and the result explicitly identifies the fallback.

## Structured-query scope

Supported filters include ASD review status, salt/non-salt, ASD carrier, polymer as an
excipient, spray drying/HME, dosage form, BCS class, pKa availability and first-authorisation
dates. Unsupported predicates (for example FDA approval, oncology or unsupported negation)
request clarification rather than silently dropping conditions. The literature comparison
is a separate dataset/view and is not used as hidden CMC evidence.

One row is one product, not one molecule. In a combination, different filters may refer
to different API components. Carrier queries include labelled saved inferences by default;
`reported only` narrows that basis. Original extraction records are not overwritten.

Salt status is normalized from the saved salt fields, not inferred from every occurrence
of the word “salt”. Any definite salt API qualifies a product. Excipient salts and covalent
halogens do not qualify. Under the current saved-record rule, the cohort partitions into:

| Status | Products |
|---|---:|
| Salt | 146 |
| Non-salt | 187 |
| Stage-dependent | 3 |
| Coordination / inorganic complex | 5 |
| Unknown | 7 |
| Not applicable | 3 |

Olysio, Qtern and Zontivity have DS/DP conversion issues and are reported separately.
Bylvay has conflicting saved terminology; Voranigo's co-component does not establish
salt versus co-crystal. These are research counting conventions requiring scientist review,
not an EMA-issued “salt drugs” statistic. Raw fields and normalized assignments are inspectable.

## Evaluation performed

Twenty fixed English development/regression questions use the same corpus, product filtering
and known reference pages for BM25, dense and hybrid retrieval. Raw-rank metrics below exclude
the extra source-linked fields; final context coverage includes them. No LLM judges or paid
embedding calls were used. The semantic model was not fine-tuned.

| Method | Known-page hit @5 | Mean known-page recall @8 | Reference coverage in final context |
|---|---:|---:|---:|
| BM25 | 90% | 90% | 95% |
| Dense | 85% | 90% | 90% |
| Hybrid RRF | 85% | 95% | 95% |

The result supports complementarity, **not universal hybrid superiority**. Hybrid improved
recall at eight but did not improve hit rate at five or final context coverage over BM25.
The paraphrase subset had mean page recall @8 of 83.3% / 100% / 100% respectively.
One question describing two nucleosides and the sachet strengths did not retrieve the selected
strength reference page with any method. The failure is retained in `evaluation/results.json`.

Known reference pages were selected by the same assistant that implemented the system.
They are not exhaustive relevance annotations; some other pages may also contain useful evidence.
Questions participated in development. The six “no brand name” questions can still contain
INNs, which may trigger product routing. There is no independent blinded answer-quality score,
and no controlled old-Gemini-versus-new-GLM comparison. Latency includes model warm-up and
is not a cloud SLA. Do not present these results as 95% answer accuracy.

Engineering tests cover counting without an API, negation/unsupported filters, date boundaries,
salt/hydrate distinctions, compound scope, missing pKa, missing documents, comparison context,
citations, English presentation and Streamlit interactions. Provider responses are mocked.

## Remaining limitations and scientific review

- Counts inherit extraction/review quality and the declared normalization policy.
- BGE-small is an English embedding model; arbitrary Chinese semantic questions are not validated.
- Numeric/descriptive cross-product questions and unrecognized synonyms can miss evidence.
- Top-k retrieval remains incomplete. It must not supply a cohort denominator.
- Citation validation checks that IDs were supplied, not that every claim is scientifically entailed.
- A single turn is supported; conversational follow-up memory is not implemented.
- The CMC snapshot can cover an earlier formulation (notably Xtandi/Lynparza); later formulations
  cannot be inferred from those documents.
- Next independent validation: a scientist chooses unseen questions and labels acceptable evidence,
  then reviews correctness, unsupported claims, refusal quality and retrieval coverage separately.

## Interview description

“I built a CMC research assistant with two paths: deterministic analysis of structured records
for complete cohort questions, and retrieval-augmented explanations for source-based questions.
The retrieval combines BM25 with local dense embeddings using reciprocal rank fusion, plus
drug-specific routing and source-linked fields. Answers preserve reported facts versus review
inferences and expose their source pages. I evaluated retrieval methods on the same corpus;
hybrid improved recall at eight on my development set, but I do not claim independently validated
answer accuracy. An important lesson was that counting retrieved passages is not database analysis.”

Official implementation references: [FastEmbed](https://qdrant.github.io/fastembed/Getting%20Started/),
[quantized model](https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q).
