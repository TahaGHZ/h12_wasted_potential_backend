from collections import defaultdict
from datetime import datetime
from typing import Any
import os
import json

from fastapi import APIRouter, HTTPException

from backend.config.storage import StorageService

router = APIRouter()
storage = StorageService()
_LOCATIONS_CACHE: dict | None = None

def _load_locations_refs() -> dict:
    global _LOCATIONS_CACHE
    if _LOCATIONS_CACHE is not None:
        return _LOCATIONS_CACHE

    locations_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "locations_refs",
        "locations_refs.json",
    )
    try:
        with open(locations_path, "r", encoding="utf-8") as handle:
            _LOCATIONS_CACHE = json.load(handle)
    except Exception:
        _LOCATIONS_CACHE = {}
    return _LOCATIONS_CACHE


def _safe_iso_to_dt(value: str | None) -> datetime:
    if not value:
        return datetime.min
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min


def _latest_by(items: list[dict], key_fn):
    latest: dict[str, dict] = {}
    for item in items:
        key = key_fn(item)
        if not key:
            continue
        prev = latest.get(key)
        if prev is None or _safe_iso_to_dt(item.get("saved_at")) > _safe_iso_to_dt(prev.get("saved_at")):
            latest[key] = item
    return list(latest.values())


def _heatzone_bucket(signal_doc: dict[str, Any]) -> str:
    enriched = signal_doc.get("enriched_payload", {})
    severity = float(enriched.get("severity") or 0)
    if severity >= 7:
        return "critical"
    if severity >= 4:
        return "high"
    if severity >= 2:
        return "moderate"
    return "low"


def _latest_doc_by_key(items: list[dict], key_fn) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for item in items:
        key = key_fn(item)
        if not key:
            continue
        prev = latest.get(key)
        if prev is None or _safe_iso_to_dt(item.get("saved_at")) > _safe_iso_to_dt(prev.get("saved_at")):
            latest[key] = item
    return latest


@router.get("/dashboard/signals")
def list_signals():
    signal_docs = storage.list_signals()
    latest = _latest_by(signal_docs, lambda doc: doc.get("raw_payload", {}).get("signal_id"))

    items = []
    for doc in sorted(latest, key=lambda d: d.get("saved_at", ""), reverse=True):
        raw_payload = doc.get("raw_payload", {})
        enriched = doc.get("enriched_payload", {})
        location = enriched.get("location") or {}
        metadata = enriched.get("metadata") or {}

        items.append(
            {
                "signal_id": raw_payload.get("signal_id"),
                "source_type": raw_payload.get("source_type"),
                "raw_text": raw_payload.get("raw_text"),
                "location_text": raw_payload.get("location_text"),
                "reported_at": raw_payload.get("reported_at"),
                "timestamp": enriched.get("timestamp"),
                "saved_at": doc.get("saved_at"),
                "domain": enriched.get("domain"),
                "event_type": enriched.get("event_type"),
                "severity": enriched.get("severity"),
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
                "neighborhood": location.get("neighborhood"),
                "target_department": metadata.get("target_department"),
                "case_id": metadata.get("case_id"),
                "heat_level": _heatzone_bucket(doc),
            }
        )

    return {"count": len(items), "items": items}


@router.get("/dashboard/cases")
def list_cases():
    case_docs = storage.list_cases()
    latest = _latest_by(case_docs, lambda doc: doc.get("case_payload", {}).get("case_id"))

    items = []
    for doc in sorted(latest, key=lambda d: d.get("saved_at", ""), reverse=True):
        payload = doc.get("case_payload", {})
        items.append(
            {
                "case_id": payload.get("case_id"),
                "title": payload.get("title"),
                "description": payload.get("description"),
                "status": payload.get("status"),
                "domain": payload.get("domain"),
                "event_type": payload.get("event_type"),
                "location": payload.get("location"),
                "priority_score": payload.get("priority_score"),
                "signals_count": len(payload.get("signals") or []),
                "embedding_count": payload.get("embedding_count") or 0,
                "updated_at": payload.get("updated_at"),
                "saved_at": doc.get("saved_at"),
                "signals": payload.get("signals") or [],
                "embedding": payload.get("embedding") or [],
            }
        )

    return {"count": len(items), "items": items}


@router.get("/dashboard/briefs")
def list_briefs():
    brief_docs = storage.list_briefs()
    latest = _latest_by(brief_docs, lambda doc: doc.get("brief_payload", {}).get("case_id"))

    items = []
    for doc in sorted(latest, key=lambda d: d.get("saved_at", ""), reverse=True):
        payload = doc.get("brief_payload", {})
        items.append({"saved_at": doc.get("saved_at"), **payload})

    return {"count": len(items), "items": items}


@router.get("/dashboard/plans")
def list_plans():
    plan_docs = storage.list_plans()
    latest = _latest_by(plan_docs, lambda doc: doc.get("plan_payload", {}).get("case_id"))

    items = []
    for doc in sorted(latest, key=lambda d: d.get("saved_at", ""), reverse=True):
        payload = doc.get("plan_payload", {})
        items.append({"saved_at": doc.get("saved_at"), **payload})

    return {"count": len(items), "items": items}


@router.get("/dashboard/overview")
def dashboard_overview():
    signal_docs = storage.list_signals()
    case_docs = storage.list_cases()
    brief_docs = storage.list_briefs()
    plan_docs = storage.list_plans()

    latest_signals = _latest_by(signal_docs, lambda doc: doc.get("raw_payload", {}).get("signal_id"))
    latest_cases = _latest_by(case_docs, lambda doc: doc.get("case_payload", {}).get("case_id"))
    latest_briefs = _latest_by(brief_docs, lambda doc: doc.get("brief_payload", {}).get("case_id"))
    latest_plans = _latest_by(plan_docs, lambda doc: doc.get("plan_payload", {}).get("case_id"))

    severity_buckets = {"critical": 0, "high": 0, "moderate": 0, "low": 0}
    domain_counts: dict[str, int] = defaultdict(int)
    event_type_counts: dict[str, int] = defaultdict(int)
    cluster_points = []
    
    case_title_map = {
        c.get("case_payload", {}).get("case_id"): c.get("case_payload", {}).get("title")
        for c in latest_cases
    }

    for signal_doc in latest_signals:
        enriched = signal_doc.get("enriched_payload", {})
        raw_payload = signal_doc.get("raw_payload", {})
        metadata = enriched.get("metadata") or {}
        location = enriched.get("location") or {}
        level = _heatzone_bucket(signal_doc)
        severity_buckets[level] += 1

        domain = enriched.get("domain") or "Unknown"
        event_type = enriched.get("event_type") or "Unknown"
        domain_counts[domain] += 1
        event_type_counts[event_type] += 1

        lat = location.get("latitude")
        lng = location.get("longitude")
        if lat is None or lng is None:
            continue

        cluster_points.append(
            {
                "signal_id": enriched.get("signal_id"),
                "signal_text": raw_payload.get("raw_text"),
                "case_id": metadata.get("case_id"),
                "case_title": case_title_map.get(metadata.get("case_id")),
                "latitude": lat,
                "longitude": lng,
                "severity": enriched.get("severity"),
                "domain": domain,
                "event_type": event_type,
                "heat_level": level,
                "embedding": metadata.get("embedding") or [],
                "embedding_model": metadata.get("embedding_model"),
                "embedding_dim": metadata.get("embedding_dim"),
            }
        )

    case_cards = []
    for case_doc in sorted(latest_cases, key=lambda d: d.get("saved_at", ""), reverse=True):
        payload = case_doc.get("case_payload", {})
        case_cards.append(
            {
                "case_id": payload.get("case_id"),
                "title": payload.get("title"),
                "status": payload.get("status"),
                "priority_score": payload.get("priority_score"),
                "domain": payload.get("domain"),
                "event_type": payload.get("event_type"),
                "location": payload.get("location"),
                "signals_count": len(payload.get("signals") or []),
                "embedding_count": payload.get("embedding_count") or 0,
            }
        )

    clusters = defaultdict(list)
    for point in cluster_points:
        if point.get("case_id"):
            clusters[point["case_id"]].append(point)

    cluster_summary = []
    for case_id, members in clusters.items():
        avg_severity = 0.0
        if members:
            avg_severity = sum(float(member.get("severity") or 0) for member in members) / len(members)
        cluster_summary.append(
            {
                "case_id": case_id,
                "case_title": case_title_map.get(case_id, "Unknown Claim"),
                "signals_count": len(members),
                "avg_severity": round(avg_severity, 2),
                "top_event_type": max(
                    (member.get("event_type") or "Unknown" for member in members),
                    key=lambda ev: sum(1 for m in members if (m.get("event_type") or "Unknown") == ev),
                    default="Unknown",
                ),
                "center": {
                    "latitude": round(sum(member["latitude"] for member in members) / len(members), 6),
                    "longitude": round(sum(member["longitude"] for member in members) / len(members), 6),
                },
            }
        )

    cluster_summary.sort(key=lambda c: c["signals_count"], reverse=True)

    return {
        "kpi": {
            "signals_total": len(latest_signals),
            "cases_total": len(latest_cases),
            "briefs_total": len(latest_briefs),
            "plans_total": len(latest_plans),
            "open_cases": sum(1 for c in latest_cases if (c.get("case_payload", {}).get("status") or "").lower() == "open"),
        },
        "heatzones": {
            "counts": severity_buckets,
            "points": cluster_points,
        },
        "claims_signals": {
            "domain_counts": dict(sorted(domain_counts.items(), key=lambda item: item[1], reverse=True)),
            "event_type_counts": dict(sorted(event_type_counts.items(), key=lambda item: item[1], reverse=True)),
            "cases": case_cards,
        },
        "embedding_clusters": {
            "points": cluster_points,
            "cluster_count": len({p.get("case_id") for p in cluster_points if p.get("case_id")}),
            "embedding_models": sorted({p.get("embedding_model") for p in cluster_points if p.get("embedding_model")}),
            "embedding_dims": sorted({p.get("embedding_dim") for p in cluster_points if p.get("embedding_dim")}),
            "clusters": cluster_summary,
        },
    }


@router.get("/dashboard/locations")
def dashboard_locations():
    data = _load_locations_refs()
    return {
        "region": data.get("region"),
        "hazard_source": data.get("hazard_source"),
        "zones": data.get("zones") or [],
        "metadata": data.get("metadata") or {},
    }


@router.get("/dashboard/cases/{case_id}/detail")
def case_detail(case_id: str):
    case_by_id = _latest_doc_by_key(storage.list_cases(), lambda doc: doc.get("case_payload", {}).get("case_id"))
    brief_by_case = _latest_doc_by_key(storage.list_briefs(), lambda doc: doc.get("brief_payload", {}).get("case_id"))
    plan_by_case = _latest_doc_by_key(storage.list_plans(), lambda doc: doc.get("plan_payload", {}).get("case_id"))
    signal_by_id = _latest_doc_by_key(storage.list_signals(), lambda doc: doc.get("raw_payload", {}).get("signal_id"))

    case_doc = case_by_id.get(case_id)
    if not case_doc:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    case_payload = case_doc.get("case_payload", {})
    signal_ids = case_payload.get("signals") or []

    signals = []
    for signal_id in signal_ids:
        doc = signal_by_id.get(signal_id)
        if not doc:
            continue
        raw_payload = doc.get("raw_payload", {})
        enriched = doc.get("enriched_payload", {})
        explainability = enriched.get("explainability") or {}
        trace = [
            {"step": step, "rationale": rationale}
            for step, rationale in explainability.items()
        ]

        signals.append(
            {
                "signal_id": signal_id,
                "reported_at": raw_payload.get("reported_at"),
                "raw_text": raw_payload.get("raw_text"),
                "location_text": raw_payload.get("location_text"),
                "domain": enriched.get("domain"),
                "event_type": enriched.get("event_type"),
                "severity": enriched.get("severity"),
                "location": enriched.get("location") or {},
                "target_department": (enriched.get("metadata") or {}).get("target_department"),
                "trace": trace,
            }
        )

    return {
        "case": {
            "saved_at": case_doc.get("saved_at"),
            **case_payload,
        },
        "brief": (brief_by_case.get(case_id) or {}).get("brief_payload"),
        "plan": (plan_by_case.get(case_id) or {}).get("plan_payload"),
        "signals": signals,
    }
