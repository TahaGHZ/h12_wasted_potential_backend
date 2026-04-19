from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class RawSignal(BaseModel):
    signal_id: str
    source_type: str
    raw_text: str
    location_text: str
    reported_at: str
    image_urls: list[str] = Field(default_factory=list)
    voice_transcript: Optional[str] = None
    role_hint: Optional[str] = None
    attachments: list[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
class EnrichedSignal(BaseModel):
    signal_id: str
    original_text: str
    normalized_data: Dict[str, Any] = Field(default_factory=dict)
    location: Optional[Dict[str, Any]] = None
    geo_risk: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None
    domain: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[float] = None # Scale of 0 to 10
    description: Optional[str] = None # Professional summary
    explainability: Dict[str, Any] = Field(default_factory=dict) # Cumulative agent thoughts
    metrics: Dict[str, Any] = Field(default_factory=dict) # Debug metrics and timings
    metadata: Dict[str, Any] = Field(default_factory=dict)
