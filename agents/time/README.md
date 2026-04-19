# Time Agent

## Purpose
The Time Agent normalizes diverse time expressions into standardized ISO 8601 timestamps.

## Capabilities
- **Relative Time Resolution**: Converts "yesterday", "two hours ago", etc., into absolute times using the report's creation timestamp as a reference.
- **Extraction**: Identifies time-related expressions in raw text.

## Pipeline Position
- Runs before classification and severity.
- Normalized timestamps improve case chronology and downstream operational context.

## Schema

### Input
- `raw_text`: The raw report content.
- `reference_time`: The timestamp when the report was received.

### Output (`TimeOutput`)
- `normalized_timestamp`: Standardized ISO 8601 string.
- `confidence`: Extraction confidence.
- `rationale`: Explanation of how the time was resolved.
