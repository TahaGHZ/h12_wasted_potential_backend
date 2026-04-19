from pydantic import BaseModel
from typing import Optional, List
from backend.contracts.signals import EnrichedSignal
from backend.contracts.cases import Case

class CaseBuilderInput(BaseModel):
    signal_id: str
    enriched_signal: EnrichedSignal

class CaseBuilderOutput(BaseModel):
    signal_id: str
    case_id: str
    created_new: bool
    similarity: float
    priority_score: float
    previous_priority_score: Optional[float] = None
    priority_delta: Optional[float] = None
    case: Case
    case_path: Optional[str] = None
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    embedding_dim: Optional[int] = None
    confidence: float
    rationale: Optional[str]
