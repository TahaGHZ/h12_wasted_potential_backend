from pydantic import BaseModel, Field
from typing import Optional, List
from backend.contracts.cases import Case

class SmartPlanInput(BaseModel):
    case_id: str
    case: Case

class SmartPlanOutput(BaseModel):
    case_id: str
    plan_id: str
    title: str
    action_items: List[str] = Field(default_factory=list)
    related_cases: List[str] = Field(default_factory=list)
    confidence: float
    rationale: Optional[str]
