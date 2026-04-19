# Severity Agent

## Purpose
The Severity Agent assesses the urgency and impact of a reported signal on a scale of 0 to 10.

## Capabilities
- **Holistic Assessment**: Uses context from previous agents (Domain, Geo, Time) to evaluate impact.
- **Priority Scoring**: Assigns a numeric priority score (0-10).
- **Justification**: Provides a detailed rationale for the assigned score.

## Pipeline Position
- Runs before routing and case building.
- Severity contributes directly to case priority updates in the case builder.

## Schema

### Input
- `normalized_text`: Cleaned report text.
- `domain`: Classified domain.
- `key_entities`: Extracted entities.
- `extra_context`: Aggregated rationale from previous pipeline steps.

### Output (`SeverityOutput`)
- `priority_score`: Integer from 0 to 10.
- `rationale`: Detailed reasoning for the score.
- `confidence`: Assessment confidence.
