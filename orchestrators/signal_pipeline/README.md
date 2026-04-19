# Signal Pipeline Orchestrator

## Purpose
The Signal Pipeline is the primary ingestion and enrichment engine for the Gabes Copilot. It transforms each raw report into an `EnrichedSignal`, clusters it into a case, persists all artifacts, and conditionally triggers downstream briefing and planning.

## Graph Structure
The pipeline uses **LangGraph** to sequence the following nodes:
1.  **Signal Receiver**: Initializes state and enriched signal structure.
2.  **Normalizer**: Cleans text and extracts entities.
3.  **Geo Mapper**: Resolves neighborhood and coordinates.
4.  **Time Normalizer**: Standardizes timestamps.
5.  **Domain Classifier**: Categorizes the incident sector.
6.  **Event Classifier**: Refines the incident type.
7.  **Severity Assessor**: Scores impact from 0-10.
8.  **Router**: Selects the target department.
9.  **Case Builder**: Runs embedding-based case matching/creation, persists signal + case, and triggers brief/plan generation when needed.

## I/O

### Input (`RawSignal`)
- `signal_id`: Unique identifier.
- `raw_text`: User-provided description.
- `location_text`: User-provided location hint.
- `reported_at`: Entry timestamp.

### Output (`EnrichedSignal`)
- Full structured data including `location`, `severity`, `domain`, `event_type`, and a cumulative `explainability` audit trail.
- Metadata now includes:
	- `case_id`
	- `embedding`
	- `embedding_model`
	- `embedding_dim`
	- `case_priority_score`

## Side Effects

- Persists `signal_*.json` via `StorageService.save_signal`.
- Persists `case_*.json` via `CaseBuilderAgent`.
- Optionally persists `brief_*.json` and `plan_*.json` when case creation or priority change triggers downstream generation.
