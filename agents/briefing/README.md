# Briefing Agent

## Purpose
Generates an executive-ready summary for a case after creation or significant priority change.

## Input
`BriefingInput`

- `case_id`: Case identifier.
- `case`: Full `Case` payload (title, description, domain, event type, location, priority, signals).

## Output
`BriefingOutput`

- `title`: Brief title.
- `summary`: Concise executive narrative.
- `key_facts`: Core bullet facts.
- `priority_score`: Priority included for quick ranking.
- `confidence`: Model confidence.
- `rationale`: Explainability note.

## Notes

- Uses `LLMService` JSON generation with prompt constraints.
- Includes fallback behavior if model output is invalid.
- Output is persisted by the executive brief pipeline.
