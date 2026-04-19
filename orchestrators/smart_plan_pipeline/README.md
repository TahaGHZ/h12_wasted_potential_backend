# Smart Plan Pipeline Orchestrator

## Purpose
Generates and persists a smart action plan for a case.

## Nodes
- `smart_plan`: Calls `SmartPlanAgent` and stores output using `StorageService.save_plan`.

## I/O
### Input
- A case payload compatible with `Case`.

### Output
- `result.plan`: Generated `SmartPlanOutput`.
- `result.plan_path`: Saved plan JSON path.
