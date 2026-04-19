from pydantic import BaseModel
from typing import Optional

class RoutingOutput(BaseModel):
    department: str # e.g. "Public Health Department", "Regional Environment Agency"
    confidence: float
    rationale: str
