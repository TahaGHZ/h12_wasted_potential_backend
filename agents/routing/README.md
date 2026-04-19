# Routing Agent

## Purpose
The Routing Agent determines which department or agency is responsible for responding to the reported incident.

## Capabilities
- **Department Mapping**: Maps event types and severity levels to specific response teams.
- **Gabès Regional Actors**: Knowledgeable about the specific agencies operating in Gabès.

## Pipeline Position
- Runs immediately before case building.
- Selected department is persisted in signal metadata and can inform downstream briefs and plans.

## Schema

### Input
- `domain`: Classified domain.
- `event_type`: Classified event type.
- `severity`: Assessed priority score.

### Output (`RoutingOutput`)
- `department`: The target department (e.g., "Regional Environment Agency").
- `confidence`: Routing confidence.
- `rationale`: Explanation of why this department was selected.
