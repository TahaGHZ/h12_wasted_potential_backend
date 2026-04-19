from pydantic import BaseModel, Field
from typing import List, Optional

class RegionalEvent(BaseModel):
    event_id: str
    event_type: str
    location: str
    description: Optional[str] = None
    severity: Optional[float] = None
    related_signals: List[str] = Field(default_factory=list)
