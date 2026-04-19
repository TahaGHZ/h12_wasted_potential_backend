from pydantic import BaseModel, Field
from typing import List

class Insight(BaseModel):
    insight_id: str
    summary: str
    confidence: float
    
class Plan(BaseModel):
    plan_id: str
    title: str
    action_items: List[str] = Field(default_factory=list)
    related_cases: List[str] = Field(default_factory=list)
