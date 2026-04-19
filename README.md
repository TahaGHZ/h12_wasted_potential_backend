# Gabès Copilot Backend

The intelligent core of the Gabès Copilot system, designed for high-precision event detection, classification, and routing in the Gabès region.

## Quick Start

### Prerequisites
- Python 3.10+
- Environment variables configured in `backend/.env`:
	- `TOKEN_FACTORY_KEY`
	- `TOKEN_FACTORY_BASE_URL`
	- `LLM_TEXT_MODEL`
	- `LLM_VISION_MODEL`
	- `OPENROUTE_API_KEY`
	- `GEMINI_API_KEY`
	- `GEMINI_EMBEDDING_MODEL` (default `gemini-embedding-001`)
	- `GEMINI_EMBEDDING_DIM` (default `768`)
	- `GEMINI_EMBEDDING_TASK` (default `CLUSTERING`)
- Python package: `google-genai` (required for Gemini embeddings)

### Run the Server
```bash
uvicorn backend.main:app --reload
```
The API will be available at `http://localhost:8000`. Full documentation at `/docs`.

## Architecture & Responsibility Boundaries

To maintain a clean and reliable architecture, strictly observe these layer boundaries:

- **API (Listeners)**: Expose the system over HTTP (`backend/api`). They act as pure data receivers, validating input against **Contracts** before delegating to **Orchestrators**.
- **Orchestrators**: Managed via **LangGraph** (`backend/orchestrators`). They sequence agents, manage state, and route data through processing pipelines.
- **Agents**: Specialized reasoning units (`backend/agents`). Each agent solves one specific task (e.g., geocoding, severity assessment). They are stateless and never call other agents directly.
- **Contracts**: Canonical Pydantic schemas (`backend/contracts`). They define the "truth" for data structures shared across all layers.
- **Services**: I/O and external integrations (`backend/services`). Only services should perform database operations or third-party API calls.
- **Config**: System-wide configuration and service initializers (`backend/config`).

## Core Pipelines

1. **Signal Pipeline**: The primary ingestion flow. Normalizes raw reports, extracts geo/time data, classifies domain/type, assesses severity, routes to the appropriate department, clusters into cases, and persists artifacts.
2. **Case Pipeline**: Groups related signals into actionable cases using Gemini embeddings.
3. **Executive Brief Pipeline**: Generates executive summaries from case snapshots.
4. **Smart Plan Pipeline**: Generates actionable plans from case snapshots.

## Trigger Rules

- Case clustering runs incrementally for each incoming signal.
- Brief and smart plan generation are triggered when:
	- a new case is created, or
	- case priority changes beyond the configured threshold.

## Development Principles

- **Contracts First**: Define your data schema in `backend/contracts` before implementing logic.
- **Stateless Agents**: Agents should not store state. Context is passed through the Orchestrator's State object.
- **Explainability**: Every agent must provide a `rationale` in its output, which is aggregated in the `EnrichedSignal` for transparency.
