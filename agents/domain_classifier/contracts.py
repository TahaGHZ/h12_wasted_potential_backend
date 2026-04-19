from pydantic import BaseModel
from typing import Optional, Literal

class DomainClassifierOutput(BaseModel):
    domain: Literal["Health", "Environment", "Urban services", "Livelihoods"]
    confidence: float
    rationale: str
