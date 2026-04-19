import os
import json
import logging
import math
import openrouteservice
from backend.agents.geo.contracts import GeoOutput
from backend.agents.geo.prompts import GEO_AGENT_SYSTEM_PROMPT, build_geo_user_prompt
from backend.config.llm import LLMService

LOCATIONS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "locations_refs",
    "locations_refs.json",
)
_LOCATIONS_CACHE = None

_PRIORITY_WEIGHT = {
    "CRITICAL": 3.0,
    "HIGH": 2.0,
    "MEDIUM": 1.0,
    "LOW": 0.5,
}

_INDUSTRY_KEYWORDS = (
    "gct",
    "chemical",
    "factory",
    "industrial",
    "phosphate",
    "ghannouch",
)


def _load_locations_refs() -> dict:
    global _LOCATIONS_CACHE
    if _LOCATIONS_CACHE is not None:
        return _LOCATIONS_CACHE

    try:
        with open(LOCATIONS_PATH, "r", encoding="utf-8") as handle:
            _LOCATIONS_CACHE = json.load(handle)
    except Exception:
        _LOCATIONS_CACHE = {}
    return _LOCATIONS_CACHE


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(min(1.0, math.sqrt(a)))
    return radius_km * c


def _distance_weight(distance_km: float) -> float:
    if distance_km <= 0.75:
        return 2.0
    if distance_km <= 1.5:
        return 1.5
    if distance_km <= 3.0:
        return 1.0
    if distance_km <= 6.0:
        return 0.5
    return 0.0


def _risk_level(score: float) -> str:
    if score >= 4.5:
        return "critical"
    if score >= 3.0:
        return "high"
    if score >= 2.0:
        return "moderate"
    return "low"


def _contains_industry_hint(raw_text: str, location_text: str) -> bool:
    content = f"{raw_text} {location_text}".lower()
    return any(keyword in content for keyword in _INDUSTRY_KEYWORDS)


def _compute_geo_risk(raw_text: str, location_text: str, lat: float, lon: float) -> dict | None:
    refs = _load_locations_refs()
    if not refs:
        return None

    hazard = refs.get("hazard_source") or {}
    zones = refs.get("zones") or []

    hazard_distance = None
    hazard_score = 0.0
    correlation_flags = []

    if hazard.get("latitude") is not None and hazard.get("longitude") is not None:
        hazard_distance = _haversine_km(lat, lon, hazard["latitude"], hazard["longitude"])
        hazard_score = _PRIORITY_WEIGHT.get(hazard.get("priority", "CRITICAL"), 3.0) + _distance_weight(hazard_distance)
        if hazard_distance <= 3.0:
            correlation_flags.append("near_hazard_source")

    if _contains_industry_hint(raw_text, location_text):
        correlation_flags.append("reported_industry_mention")

    enriched_zones = []
    for zone in zones:
        if zone.get("latitude") is None or zone.get("longitude") is None:
            continue
        distance = _haversine_km(lat, lon, zone["latitude"], zone["longitude"])
        enriched_zones.append(
            {
                **zone,
                "distance_km": round(distance, 3),
            }
        )

    nearest_sensitive = None
    zone_score = 0.0
    if enriched_zones:
        nearest_sensitive = min(enriched_zones, key=lambda z: z["distance_km"])
        priority_weight = _PRIORITY_WEIGHT.get(nearest_sensitive.get("priority", "LOW"), 0.5)
        zone_score = priority_weight + _distance_weight(nearest_sensitive["distance_km"])

    nearby_sensitive = [z for z in enriched_zones if z.get("distance_km", 999) <= 3.0]
    nearby_sensitive.sort(key=lambda z: z["distance_km"])
    nearby_sensitive = nearby_sensitive[:5]

    risk_score = max(hazard_score, zone_score)
    if correlation_flags and risk_score < 2.0:
        risk_score = 2.0

    return {
        "hazard_source": {
            "name": hazard.get("name"),
            "type": hazard.get("type"),
            "priority": hazard.get("priority"),
            "risk_factor": hazard.get("risk_factor"),
            "distance_km": round(hazard_distance, 3) if hazard_distance is not None else None,
        },
        "nearest_sensitive": nearest_sensitive,
        "nearby_sensitive": nearby_sensitive,
        "risk_score": round(risk_score, 2),
        "risk_level": _risk_level(risk_score),
        "correlation_flags": correlation_flags,
    }

class GeoAgent:
    def __init__(self):
        self.llm = LLMService()
        self.api_key = os.getenv("OPENROUTE_API_KEY")
        self.client = None
        self.logger = logging.getLogger("signal_pipeline")
        
        if self.api_key:
            try:
                self.client = openrouteservice.Client(key=self.api_key)
            except Exception as e:
                self.logger.exception("GeoAgent failed to initialize ORS client: %s", e)

    def run(self, raw_text: str, location_text: str) -> GeoOutput:
        """
        1. Uses LLM to extract semantic location.
        2. Tries to geocode via OpenRouteService.
        3. Falls back to LLM estimation if needed.
        """
        user_prompt = build_geo_user_prompt(raw_text, location_text)

        try:
            # Step 1: LLM Extraction
            json_response = self.llm.generate_json(
                system_prompt=GEO_AGENT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1
            )
            data = json.loads(json_response)
            
            neighborhood = data.get("neighborhood", "Unknown")
            search_address = data.get("search_address", "Gabes, Tunisia")
            llm_lat = data.get("estimated_lat", 33.8815)
            llm_lon = data.get("estimated_lon", 10.0982)
            rationale = data.get("rationale", "")

            # Step 2: ORS Geocoding
            final_lat, final_lon = llm_lat, llm_lon
            geo_source = "LLM Estimation"

            if self.client:
                try:
                    # Logic: Use Pelias search on the specific address
                    # Restrict search to region around Gabes to avoid false positives elsewhere
                    result = self.client.pelias_search(
                        text=search_address,
                        focus_point=[10.0982, 33.8815], # Center of Gabes
                        size=1
                    )
                    
                    if result and result.get('features'):
                        coords = result['features'][0]['geometry']['coordinates']
                        # ORS returns [lon, lat]
                        final_lon, final_lat = coords[0], coords[1]
                        geo_source = "OpenRouteService"
                        self.logger.info("GeoAgent geocoded '%s' via ORS", search_address)
                except Exception as api_err:
                    self.logger.exception("GeoAgent ORS call failed, falling back to LLM: %s", api_err)

            geo_risk = _compute_geo_risk(raw_text, location_text, final_lat, final_lon)
            risk_note_parts = []
            if geo_risk:
                hazard_info = geo_risk.get("hazard_source") or {}
                if hazard_info.get("name") and hazard_info.get("distance_km") is not None:
                    risk_note_parts.append(
                        f"Hazard source {hazard_info['name']} at {hazard_info['distance_km']} km."
                    )
                nearest_sensitive = geo_risk.get("nearest_sensitive") or {}
                if nearest_sensitive.get("name") and nearest_sensitive.get("distance_km") is not None:
                    risk_note_parts.append(
                        f"Nearest sensitive site {nearest_sensitive['name']} at {nearest_sensitive['distance_km']} km."
                    )

            risk_note = " ".join(risk_note_parts)

            return GeoOutput(
                neighborhood=neighborhood,
                latitude=final_lat,
                longitude=final_lon,
                confidence=0.9 if geo_source == "OpenRouteService" else 0.6,
                rationale=f"Source: {geo_source}. {rationale} {risk_note}".strip(),
                geo_risk=geo_risk,
            )

        except Exception as e:
            self.logger.exception("GeoAgent critical error: %s", e)
            return GeoOutput(
                neighborhood="Unknown",
                latitude=33.8815,
                longitude=10.0982,
                confidence=0.0,
                rationale=f"Error in geo processing: {str(e)}"
            )

