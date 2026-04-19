from pydantic import BaseModel
from typing import Optional, List

class NormalizerOutput(BaseModel):
    standardized_text: str
    language: str
    key_entities: List[str]
    confidence: float
    rationale: Optional[str] = None
