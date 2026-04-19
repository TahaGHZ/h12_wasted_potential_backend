from typing import TypedDict, Optional, Dict, Any

class PipelineState(TypedDict):
    signal: Dict[str, Any]
    enriched: Dict[str, Any]
    result: Optional[Dict[str, Any]]
