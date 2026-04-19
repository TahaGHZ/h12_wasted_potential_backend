from pydantic import BaseModel, Field
from typing import Optional, List
from backend.contracts.cases import Case

class BriefingInput(BaseModel):
    case_id: str
    case: Case

class BriefingOutput(BaseModel):
    case_id: str
    title: str
    summary: str
    key_facts: List[str] = Field(default_factory=list)
    priority_score: Optional[float] = None
    confidence: float
    rationale: Optional[str]
