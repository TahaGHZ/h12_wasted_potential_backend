from pydantic import BaseModel
from typing import Optional

class EventTypeOutput(BaseModel):
    event_type: str # e.g. "Chemical Leak", "Water Main Break", "Illegal Dumping"
    confidence: float
    rationale: str
