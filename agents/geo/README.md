# Geo Agent

## Purpose
The Geo Agent is responsible for resolving textual location descriptions into geographic coordinates (latitude/longitude) and identified neighborhoods within the Gabès region.

## Capabilities
1.  **Semantic Extraction**: Uses LLM to extract a clean "search address" and neighborhood name from raw signal text.
2.  **Geocoding**: Interfaces with **OpenRouteService (Pelias)** to find precise coordinates.
3.  **Intelligent Fallback**: If geocoding fails, it uses LLM-based estimation grounded in regional knowledge.

## Schema

### Input (Function Arguments)
- `raw_text`: The full text of the report.
- `location_text`: Specific location clues provided in the report.

### Output (`GeoOutput`)
- `neighborhood`: Recognized neighborhood name.
- `latitude`: WGS84 latitude.
- `longitude`: WGS84 longitude.
- `confidence`: Score from 0.0 to 1.0 (higher if ORS verified).
- `rationale`: Explanation of the geocoding source and logic.

## Dependencies
- `OpenRouteService` (requires `OPENROUTE_API_KEY`)
- `LLMService` (for extraction and fallback)

## Pipeline Position
- Runs before case clustering.
- The resolved neighborhood becomes part of the embedding text used by case matching.
