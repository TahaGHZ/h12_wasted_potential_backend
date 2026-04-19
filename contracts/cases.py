from pydantic import BaseModel, Field
from typing import List, Optional

class Case(BaseModel):
    case_id: str
    title: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    status: str = "open"
    events: List[str] = Field(default_factory=list)
    signals: List[str] = Field(default_factory=list)
    priority_score: Optional[float] = None
    domain: Optional[str] = None
    event_type: Optional[str] = None
    location: Optional[str] = None
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    embedding_dim: Optional[int] = None
    embedding_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    rationale: Optional[str] = None
