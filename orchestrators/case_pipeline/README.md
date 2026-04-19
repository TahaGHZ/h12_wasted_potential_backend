# Case Pipeline Orchestrator

## Purpose
Runs case clustering and prioritization for a single enriched signal in incremental mode.

## Nodes
- `case_builder`: Calls `CaseBuilderAgent` to match or create a case and persist the result.

## I/O
### Input
- A signal-shaped payload containing fields required to build `EnrichedSignal`.

### Output
- `result` with `CaseBuilderOutput` data, including `case_id`, `created_new`, `similarity`, `priority_score`, and `case_path`.
