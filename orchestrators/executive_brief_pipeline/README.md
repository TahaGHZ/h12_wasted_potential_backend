# Executive Brief Pipeline Orchestrator

## Purpose
Generates and persists an executive briefing for a case.

## Nodes
- `briefing`: Calls `BriefingAgent` and stores output using `StorageService.save_brief`.

## I/O
### Input
- A case payload compatible with `Case`.

### Output
- `result.brief`: Generated `BriefingOutput`.
- `result.brief_path`: Saved brief JSON path.
