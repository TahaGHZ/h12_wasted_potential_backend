from pydantic import BaseModel
from typing import Optional

class TimeOutput(BaseModel):
    normalized_timestamp: str # ISO 8601 format
    confidence: float
    rationale: str
