# Case Builder Agent

## Purpose
Clusters new enriched signals into existing cases (or creates new ones), then computes case priority for operational triage.

## Input
`CaseBuilderInput`

- `signal_id`: Current signal identifier.
- `enriched_signal`: Full `EnrichedSignal` object from the signal pipeline.

## Output
`CaseBuilderOutput`

- `case_id`: Target case id.
- `created_new`: Whether a new case was created.
- `similarity`: Best cosine similarity score used for matching.
- `priority_score`: Updated case priority.
- `priority_delta`: Change in priority versus previous case snapshot.
- `case`: Full updated `Case` object.
- `embedding`: Signal embedding used for matching.
- `rationale`: Explainable decision text.

## Matching Strategy

1. Build embedding text from normalized summary + domain + event type + neighborhood.
2. Generate Gemini embedding (`gemini-embedding-001` by default).
3. Compare against stored case embeddings and stored signal embeddings using cosine similarity.
4. Attach to best case if score >= configured threshold, else create a new case.

## Priority Strategy

- Current formula: `priority = min(10, severity + volume_weight * signal_count)`.
- Designed for incremental updates on each new signal.

## Storage

- Reads historical snapshots from `StorageService`.
- Persists updated case snapshots as `case_<case_id>_<timestamp>.json`.
