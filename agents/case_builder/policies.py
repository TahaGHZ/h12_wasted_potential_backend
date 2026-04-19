from datetime import datetime

SIMILARITY_THRESHOLD = 0.82
SIMILARITY_TOP_K = 5
PRIORITY_VOLUME_WEIGHT = 0.5
PRIORITY_CHANGE_TRIGGER = 0.75

def build_embedding_text(enriched_signal) -> str:
    normalized = enriched_signal.normalized_data.get("standardized_text", "")
    domain = enriched_signal.domain or "Unknown"
    event_type = enriched_signal.event_type or "Unknown"
    neighborhood = (enriched_signal.location or {}).get("neighborhood", "Unknown")

    return "\n".join([
        f"Domain: {domain}",
        f"Event Type: {event_type}",
        f"Neighborhood: {neighborhood}",
        f"Summary: {normalized}"
    ])

def compute_priority_score(severity: float, volume: int) -> float:
    base = severity if severity is not None else 0.0
    volume_boost = max(0, volume) * PRIORITY_VOLUME_WEIGHT
    return min(10.0, base + volume_boost)

def should_trigger_brief(priority_delta: float, created_new: bool) -> bool:
    if created_new:
        return True
    if priority_delta is None:
        return False
    return abs(priority_delta) >= PRIORITY_CHANGE_TRIGGER

def now_iso() -> str:
    return datetime.now().isoformat()
