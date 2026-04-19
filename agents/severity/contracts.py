from pydantic import BaseModel, Field
from typing import Optional

class SeverityOutput(BaseModel):
    priority_score: int = Field(ge=0, le=10)
    rationale: str
    confidence: float
