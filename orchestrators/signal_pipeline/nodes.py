import asyncio
import logging
import time
from typing import Any, Dict
from backend.contracts.signals import RawSignal, EnrichedSignal
from backend.agents.normalizer.agent import NormalizerAgent
from backend.agents.domain_classifier.agent import DomainClassifierAgent
from backend.agents.severity.agent import SeverityAgent
from backend.agents.geo.agent import GeoAgent
from backend.agents.time.agent import TimeAgent
from backend.agents.event_type_classifier.agent import EventTypeClassifierAgent
from backend.agents.routing.agent import RoutingAgent
from backend.agents.case_builder.agent import CaseBuilderAgent
from backend.agents.case_builder.contracts import CaseBuilderInput
from backend.agents.case_builder.policies import should_trigger_brief
from backend.orchestrators.executive_brief_pipeline.orchestrator import ExecutiveBriefPipelineOrchestrator
from backend.orchestrators.smart_plan_pipeline.orchestrator import SmartPlanPipelineOrchestrator
from backend.config.storage import StorageService

logger = logging.getLogger("signal_pipeline")

def _ensure_metrics(enriched: dict) -> dict:
    metrics = enriched.setdefault("metrics", {})
    metrics.setdefault("timings_ms", {})
    metrics.setdefault("node_status", {})
    metrics.setdefault("models", {})
    metrics.setdefault("tokens", {})
    metrics.setdefault("scores", {})
    return metrics

def _record_timing(enriched: dict, node_name: str, started: float) -> None:
    metrics = _ensure_metrics(enriched)
    elapsed_ms = (time.perf_counter() - started) * 1000
    metrics["timings_ms"][node_name] = round(elapsed_ms, 2)
    metrics["node_status"][node_name] = "ok"

def _record_llm_meta(enriched: dict, node_name: str, agent: Any) -> None:
    if not hasattr(agent, "llm"):
        return
    llm = getattr(agent, "llm")
    if getattr(llm, "last_model", None):
        _ensure_metrics(enriched)["models"][node_name] = llm.last_model
    usage = getattr(llm, "last_usage", None)
    if usage:
        _ensure_metrics(enriched)["tokens"][node_name] = {
            "prompt": getattr(usage, "prompt_tokens", None),
            "completion": getattr(usage, "completion_tokens", None),
            "total": getattr(usage, "total_tokens", None),
        }

def _record_score(enriched: dict, node_name: str, output: Any) -> None:
    confidence = getattr(output, "confidence", None)
    if confidence is None:
        return
    _ensure_metrics(enriched)["scores"][node_name] = {"confidence": confidence}

def _geo_severity_adjustment(geo_risk: dict) -> tuple[float, list[str]]:
    if not geo_risk:
        return 0.0, []

    adjustment = 0.0
    reasons = []

    risk_level = geo_risk.get("risk_level")
    if risk_level == "critical":
        adjustment += 2.0
        reasons.append("critical geo risk")
    elif risk_level == "high":
        adjustment += 1.5
        reasons.append("high geo risk")
    elif risk_level == "moderate":
        adjustment += 1.0
        reasons.append("moderate geo risk")

    hazard = geo_risk.get("hazard_source") or {}
    hazard_distance = hazard.get("distance_km")
    if isinstance(hazard_distance, (int, float)):
        if hazard_distance <= 1.0:
            adjustment += 1.0
            reasons.append("hazard source within 1 km")
        elif hazard_distance <= 3.0:
            adjustment += 0.5
            reasons.append("hazard source within 3 km")

    nearest = geo_risk.get("nearest_sensitive") or {}
    nearest_distance = nearest.get("distance_km")
    if isinstance(nearest_distance, (int, float)):
        if nearest_distance <= 0.75:
            adjustment += 0.75
            reasons.append("sensitive site within 750 m")
        elif nearest_distance <= 1.5:
            adjustment += 0.5
            reasons.append("sensitive site within 1.5 km")

    if "near_hazard_source" in (geo_risk.get("correlation_flags") or []):
        adjustment += 0.25
        reasons.append("near hazard correlation")
    if "reported_industry_mention" in (geo_risk.get("correlation_flags") or []):
        adjustment += 0.25
        reasons.append("industry mention")

    return adjustment, reasons

# Helpers for lazy initialization
def get_normalizer():
    return NormalizerAgent()

def get_domain_classifier():
    return DomainClassifierAgent()

def get_severity_assessor():
    return SeverityAgent()

def get_geo_mapper():
    return GeoAgent()

def get_time_normalizer():
    return TimeAgent()

def get_event_classifier():
    return EventTypeClassifierAgent()

def get_router():
    return RoutingAgent()

def get_storage():
    return StorageService()

async def signal_receiver_node(state):
    """
    Initial receiver. Initializes the EnrichedSignal and audit trail.
    """
    started = time.perf_counter()
    raw_data = state["signal"]
    raw_signal = RawSignal(**raw_data)
    
    enriched = EnrichedSignal(
        signal_id=raw_signal.signal_id,
        original_text=raw_signal.raw_text,
        explainability={},
        metrics={
            "timings_ms": {},
            "node_status": {},
            "models": {},
            "tokens": {},
            "scores": {},
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
    )
    
    logger.info(f"Signal {raw_signal.signal_id} received and initialized.")
    enriched_payload = enriched.model_dump()
    enriched_payload["explainability"]["signal_receiver"] = "Signal validated and initialized."
    _record_timing(enriched_payload, "signal_receiver", started)
    return {
        "signal": raw_signal.model_dump(),
        "enriched": enriched_payload
    }

async def normalizer_node(state):
    """
    Standardizes text and extracts entities. Ends with an initial summary.
    """
    raw_signal = state["signal"]
    enriched = state["enriched"]
    
    started = time.perf_counter()
    agent = get_normalizer()
    output = await asyncio.to_thread(agent.run, raw_signal)
    _record_timing(enriched, "normalizer", started)
    _record_llm_meta(enriched, "normalizer", agent)
    _record_score(enriched, "normalizer", output)
    
    enriched["normalized_data"] = output.model_dump()
    enriched["explainability"]["normalizer"] = output.rationale if hasattr(output, 'rationale') else "Normalized raw content."
    
    logger.info("Normalization complete.")
    return {"enriched": enriched}

async def geo_node(state):
    """
    Extracts neighborhood and coordinates. Adds to explainability.
    """
    raw_signal = state["signal"]
    enriched = state["enriched"]
    
    started = time.perf_counter()
    agent = get_geo_mapper()
    output = await asyncio.to_thread(
        agent.run,
        raw_signal.get("raw_text", ""),
        raw_signal.get("location_text", "")
    )
    _record_timing(enriched, "geo", started)
    _record_llm_meta(enriched, "geo", agent)
    _record_score(enriched, "geo", output)
    
    enriched["location"] = {
        "neighborhood": output.neighborhood,
        "latitude": output.latitude,
        "longitude": output.longitude,
        "confidence": output.confidence
    }
    enriched["explainability"]["geo"] = output.rationale
    if getattr(output, "geo_risk", None):
        enriched["geo_risk"] = output.geo_risk
    
    logger.info(f"Location resolved to {output.neighborhood}.")
    return {"enriched": enriched}

async def time_node(state):
    """
    Normalizes time.
    """
    raw_signal = state["signal"]
    enriched = state["enriched"]
    
    started = time.perf_counter()
    agent = get_time_normalizer()
    output = await asyncio.to_thread(
        agent.run,
        raw_signal.get("raw_text", ""),
        raw_signal.get("reported_at", "")
    )
    _record_timing(enriched, "time", started)
    _record_llm_meta(enriched, "time", agent)
    _record_score(enriched, "time", output)
    
    enriched["timestamp"] = output.normalized_timestamp
    enriched["explainability"]["time"] = output.rationale
    
    logger.info(f"Time normalized to {output.normalized_timestamp}.")
    return {"enriched": enriched}

async def domain_classifier_node(state):
    """
    Categorizes domain and adds rationale to explainability.
    """
    enriched = state["enriched"]
    norm_data = enriched.get("normalized_data", {})
    
    started = time.perf_counter()
    agent = get_domain_classifier()
    output = await asyncio.to_thread(
        agent.run,
        norm_data.get("standardized_text", ""),
        norm_data.get("key_entities", [])
    )
    _record_timing(enriched, "domain_classifier", started)
    _record_llm_meta(enriched, "domain_classifier", agent)
    _record_score(enriched, "domain_classifier", output)
    
    enriched["domain"] = output.domain
    enriched["explainability"]["domain_classifier"] = output.rationale
    
    logger.info(f"Domain classified as {output.domain}.")
    return {"enriched": enriched}

async def event_type_classifier_node(state):
    """
    Refines event type.
    """
    enriched = state["enriched"]
    norm_data = enriched.get("normalized_data", {})
    
    started = time.perf_counter()
    agent = get_event_classifier()
    output = await asyncio.to_thread(
        agent.run,
        norm_data.get("standardized_text", ""),
        enriched.get("domain", "Unknown")
    )
    _record_timing(enriched, "event_type_classifier", started)
    _record_llm_meta(enriched, "event_type_classifier", agent)
    _record_score(enriched, "event_type_classifier", output)
    
    enriched["event_type"] = output.event_type
    enriched["explainability"]["event_type_classifier"] = output.rationale
    
    logger.info(f"Event type refined to {output.event_type}.")
    return {"enriched": enriched}

async def severity_node(state):
    """
    Assesses severity and adds to explainability.
    """
    enriched = state["enriched"]
    norm_data = enriched.get("normalized_data", {})
    explainability = enriched.get("explainability", {})
    
    # Context aggregation: Join previous thoughts into a single block
    context_str = "\n".join([f"- {k.title()}: {v}" for k, v in explainability.items()])
    
    started = time.perf_counter()
    agent = get_severity_assessor()
    output = await asyncio.to_thread(
        agent.run,
        norm_data.get("standardized_text", ""),
        enriched.get("domain", "Unknown"),
        norm_data.get("key_entities", []),
        context_str
    )
    _record_timing(enriched, "severity", started)
    _record_llm_meta(enriched, "severity", agent)
    _record_score(enriched, "severity", output)
    
    base_score = float(output.priority_score)
    geo_adjustment, geo_reasons = _geo_severity_adjustment(enriched.get("geo_risk") or {})
    final_score = min(10.0, max(0.0, base_score + geo_adjustment))
    adjustment_note = ""
    if geo_adjustment and geo_reasons:
        adjustment_note = f" Geo adjustment {geo_adjustment:+.2f} due to {', '.join(geo_reasons)}."

    enriched["severity"] = final_score
    enriched["explainability"]["severity"] = f"{output.rationale}{adjustment_note}"
    _ensure_metrics(enriched)["scores"].update(
        {
            "severity_base": round(base_score, 2),
            "severity_adjustment": round(geo_adjustment, 2),
            "severity_final": round(final_score, 2),
        }
    )
    
    logger.info(f"Severity set to {output.priority_score}/10.")
    return {"enriched": enriched}

async def routing_node(state):
    """
    Routes and captures dispatch rationale.
    """
    enriched = state["enriched"]
    enriched.setdefault("metadata", {})
    
    started = time.perf_counter()
    agent = get_router()
    output = await asyncio.to_thread(
        agent.run,
        enriched.get("domain", "Unknown"),
        enriched.get("event_type", "Unknown"),
        enriched.get("severity", 0.0)
    )
    _record_timing(enriched, "routing", started)
    _record_llm_meta(enriched, "routing", agent)
    _record_score(enriched, "routing", output)
    
    enriched["metadata"]["target_department"] = output.department
    enriched["explainability"]["routing"] = output.rationale
    
    logger.info(f"Report routed to {output.department}.")
    return {"enriched": enriched}


async def case_builder_node(state):
    """
    Final step. Consolidates everything and saves to disk.
    """
    raw_signal = RawSignal(**state["signal"])

    enriched_data = state["enriched"]
    enriched_data["description"] = f"Automated report regarding {enriched_data.get('event_type', 'an incident')} in {enriched_data.get('location', {}).get('neighborhood', 'Gabes')}."

    enriched_signal = EnrichedSignal(**enriched_data)
    started = time.perf_counter()
    agent = CaseBuilderAgent()
    case_output = await asyncio.to_thread(
        agent.run,
        CaseBuilderInput(
            signal_id=enriched_signal.signal_id,
            enriched_signal=enriched_signal
        )
    )
    _record_timing(enriched_data, "case_builder", started)
    _record_score(enriched_data, "case_builder", case_output)

    enriched_data.setdefault("metadata", {})
    enriched_data["metadata"]["case_id"] = case_output.case_id
    enriched_data["metadata"]["embedding"] = case_output.embedding
    enriched_data["metadata"]["embedding_model"] = case_output.embedding_model
    enriched_data["metadata"]["embedding_dim"] = case_output.embedding_dim
    enriched_data["metadata"]["case_priority_score"] = case_output.priority_score
    _ensure_metrics(enriched_data)["scores"].update(
        {
            "case_similarity": case_output.similarity,
            "case_confidence": case_output.confidence,
            "priority_score": case_output.priority_score,
            "priority_delta": case_output.priority_delta,
        }
    )

    enriched_signal = EnrichedSignal(**enriched_data)
    filepath = get_storage().save_signal(raw_signal, enriched_signal)

    brief_path = None
    plan_path = None
    if should_trigger_brief(case_output.priority_delta, case_output.created_new):
        case_payload = case_output.case.model_dump()
        brief_result = await asyncio.to_thread(ExecutiveBriefPipelineOrchestrator().run, case_payload)
        plan_result = await asyncio.to_thread(SmartPlanPipelineOrchestrator().run, case_payload)
        brief_path = (brief_result or {}).get("result", {}).get("brief_path")
        plan_path = (plan_result or {}).get("result", {}).get("plan_path")

    logger.info(f"Pipeline Complete. Signal {raw_signal.signal_id} stored at {filepath}")
    return {
        "enriched": enriched_data,
        "result": {
            "status": "saved",
            "path": filepath,
            "case_id": case_output.case_id,
            "case_path": case_output.case_path,
            "brief_path": brief_path,
            "plan_path": plan_path,
            "priority_score": case_output.priority_score
        }
    }
