# SmartPlan Agent

## Purpose
Generates a structured, actionable response plan for a prioritized case.

## Input
`SmartPlanInput`

- `case_id`: Case identifier.
- `case`: Full `Case` payload with context and priority.

## Output
`SmartPlanOutput`

- `plan_id`: Plan identifier.
- `title`: Plan title.
- `action_items`: Ordered actions for operations teams.
- `related_cases`: Linked cases if relevant.
- `confidence`: Model confidence.
- `rationale`: Explainability note.

## Notes

- Uses `LLMService` JSON generation with strict output schema.
- Has fallback defaults when generation fails.
- Output is persisted by the smart plan pipeline.
