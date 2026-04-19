# Domain Classifier Agent

## Purpose
The Domain Classifier Agent categorizes reports into broad sectors like health, environment, or urban services to guide subsequent processing.

## Capabilities
- **Sector Identification**: Assigns a report to exactly one of the supported domains.
- **Support for Gabès Context**: Trained/prompted with regional domain knowledge.

## Pipeline Position
- Runs before event-type classification and severity.
- Domain output is included in case embedding text for clustering.

## Schema

### Input
- `normalized_text`: Cleaned report text.
- `key_entities`: Extracted entities.

### Output (`DomainClassifierOutput`)
- `domain`: One of "Health", "Environment", "Urban services", "Livelihoods".
- `confidence`: Classification confidence.
- `rationale`: Reason for selected domain.
