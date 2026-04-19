# Normalizer Agent

## Purpose
The Normalizer Agent standardizes raw report text, identifies the source language, and extracts key entities (names, organizations, specific objects).

## Capabilities
- **Text Standardization**: Corrects typos and standardizes phrasing.
- **Language Detection**: Identifies the input language of the report.
- **Entity Extraction**: Pulls essential entities out of the text for downstream use.

## Pipeline Position
- Runs near the start of the signal pipeline.
- Its standardized text is later embedded by the case builder to support clustering.

## Schema

### Input (`RawSignal`)
- `raw_text`: The raw report content.

### Output (`NormalizerOutput`)
- `standardized_text`: Cleaned and standardized version of the input.
- `language`: Detected language (e.g., "ar", "fr", "en").
- `key_entities`: List of extracted entities.
- `confidence`: Extraction confidence score.
- `rationale`: Brief explanation of normalization decisions.
