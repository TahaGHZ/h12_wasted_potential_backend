# Event Type Classifier Agent

## Purpose
The Event Type Classifier Agent identifies the specific type of incident within a given domain (e.g., "Chemical Leak" within "Environment").

## Capabilities
- **Granular Classification**: Moves beyond broad domains to specific event labels.
- **Context-Aware**: Uses the domain assigned by the Domain Classifier to narrow down possibilities.

## Pipeline Position
- Runs before severity and routing.
- Event type is included in case embedding text for clustering and case title generation.

## Schema

### Input
- `normalized_text`: Cleaned report text.
- `domain`: The domain assigned in the previous step.

### Output (`EventTypeOutput`)
- `event_type`: Specific incident label (e.g., "Water Main Break", "Illegal Dumping").
- `confidence`: Classification confidence.
- `rationale`: Explanation for the selected event type.
