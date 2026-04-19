# Agent's Context Guide — Gabès Copilot Backend

This document provides essential context for AI coding agents to understand, maintain, and extend the Gabès Copilot backend.

## System Architecture

The backend follows a strictly layered, event-driven architecture powered by **LangGraph**:

1.  **Ingestion**: `backend/api/listener.py` receives a `RawSignal`.
2.  **Orchestration**: The `SignalPipelineOrchestrator` triggers a LangGraph state machine.
3.  **Processing**: The graph nodes execute specialized **Agents** in sequence.
4.  **Persistence and Triggering**: The final node (`case_builder`) saves the `EnrichedSignal`, updates or creates a `Case`, and may trigger downstream brief and plan pipelines.

## Core Principles

-   **Stateless Agents**: Agents must not persist state. All context is carried in the `PipelineState` (TypedDict).
-   **Pydantic Contracts**: All data exchange between agents and orchestrators must use Pydantic models defined in `backend/contracts` or the agent's local `contracts.py`.
-   **Explainability**: Every agent MUST return a `rationale` field explaining its decision. This is critical for the human-in-the-loop dashboard.
-   **No Cross-Agent Calls**: Agents are autonomous and specialized. If Agent A needs data from Agent B, the Orchestrator must handle the sequencing.

## Agent Registry & Status

| Agent | Purpose | status | Key Dependencies |
| :--- | :--- | :--- | :--- |
| `normalizer` | Cleans text, extracts basic entities | **Implemented** | `LLMService` |
| `geo` | Resolves location to neighborhood/coords | **Implemented** | `OpenRouteService`, `LLMService` |
| `time` | Standardizes relative/absolute timestamps | **Implemented** | `LLMService` |
| `domain_classifier` | Categorizes (Agriculture, Health, etc.) | **Implemented** | `LLMService` |
| `event_type_classifier`| Refined incident classification | **Implemented** | `LLMService` |
| `severity` | 0-10 priority scoring | **Implemented** | `LLMService` |
| `routing` | Suggests the responsible department | **Implemented** | `LLMService` |
| `briefing` | Generates executive summaries | **Implemented** | `LLMService` |
| `smart_plan` | Generates action plan suggestions | **Implemented** | `LLMService` |
| `case_builder` | Clusters signals into cases | **Implemented** | `GeminiEmbeddingService` |

## Orchestrator Registry

| Pipeline | Entry Point | Status |
| :--- | :--- | :--- |
| `signal_pipeline` | `SignalPipelineOrchestrator` | **Active / Production** |
| `case_pipeline` | `CasePipelineOrchestrator` | **Active** |
| `executive_brief_pipeline` | `ExecutiveBriefPipelineOrchestrator` | **Active** |
| `smart_plan_pipeline` | `SmartPlanPipelineOrchestrator` | **Active** |

## Embeddings Service

The `GeminiEmbeddingService` in `backend/config/llm.py` generates text embeddings for clustering and case matching.
It uses the Gemini API with configurable model, task type, and output dimensionality via `backend/.env`.

## Trigger Behavior

- Briefing and smart-plan pipelines are triggered when a case is newly created or when case priority changes significantly.

## How to Extend

### 1. Adding a New Agent
- Create `backend/agents/<name>/`.
- Define `contracts.py` (Input/Output schemas).
- Implement `agent.py` (Single `run()` method).
- Add `prompts.py` (System/User templates).
- Provide a `README.md` with usage examples.

### 2. Modifying a Pipeline
- Edit `backend/orchestrators/<pipeline>/nodes.py` to add a new node wrapper.
- Update `backend/orchestrators/<pipeline>/graph.py` to integrate the node into the `StateGraph`.
- Update `backend/orchestrators/<pipeline>/state.py` if new state variables are required.

## Common File Patterns

### Agent Implementation Pattern
```python
class MyNewAgent:
    def __init__(self):
        self.llm = LLMService()

    def run(self, data: MyAgentInput) -> MyAgentOutput:
        # 1. Apply deterministic policies (policies.py)
        # 2. Call LLM for reasoning (prompts.py)
        # 3. Return structured model output
```

### Orchestrator Node Pattern
```python
def my_agent_node(state: PipelineState):
    agent = MyNewAgent()
    output = agent.run(state["signal"])
    state["enriched"]["new_field"] = output.value
    state["enriched"]["explainability"]["my_agent"] = output.rationale
    return {"enriched": state["enriched"]}
```
