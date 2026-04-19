from pydantic import BaseModel
from typing import Optional, Dict, Any

class GeoOutput(BaseModel):
    neighborhood: str
    latitude: float
    longitude: float
    confidence: float
    rationale: str
    geo_risk: Optional[Dict[str, Any]] = None
