from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import re
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.config.llm import (
    GEMINI_EMBEDDING_MODEL,
    LLM_TEXT_MODEL,
    LLM_VISION_MODEL,
    GeminiEmbeddingService,
)
from backend.config.storage import StorageService

router = APIRouter()
storage = StorageService()
embedder = GeminiEmbeddingService()

EXPECTED_NODES = [
    "signal_receiver",
    "normalizer",
    "geo",
    "time",
    "domain_classifier",
    "event_type_classifier",
    "severity",
    "routing",
    "case_builder",
]


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


def _cosine_similarity(left: list[float], right: list[float]) -> float | None:
    if not left or not right:
        return None
    length = min(len(left), len(right))
    dot = sum(left[i] * right[i] for i in range(length))
    left_norm = sum(left[i] * left[i] for i in range(length)) ** 0.5
    right_norm = sum(right[i] * right[i] for i in range(length)) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return None
    return dot / (left_norm * right_norm)


def _lexical_similarity(left: str, right: str) -> float:
    tokens_left = set(re.findall(r"\w+", (left or "").lower()))
    tokens_right = set(re.findall(r"\w+", (right or "").lower()))
    if not tokens_left or not tokens_right:
        return 0.0
    return len(tokens_left & tokens_right) / len(tokens_left | tokens_right)


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def _compute_drift(signal_embedding: list[float] | None, case_embedding: list[float] | None) -> float | None:
    if not signal_embedding or not case_embedding:
        return None
    similarity = _cosine_similarity(signal_embedding, case_embedding)
    if similarity is None:
        return None
    return round(1 - similarity, 4)


def _build_trace(explainability: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"step": step, "rationale": rationale} for step, rationale in explainability.items()]


def _compute_semantic_similarity(raw_text: str, rationale_text: str) -> dict[str, Any]:
    if embedder.enabled:
        vectors = embedder.embed_texts([raw_text or "", rationale_text or ""])
        if len(vectors) == 2:
            similarity = _cosine_similarity(vectors[0], vectors[1])
            if similarity is not None:
                return {
                    "value": round(similarity, 4),
                    "method": "embedding",
                    "model": GEMINI_EMBEDDING_MODEL,
                }
    return {
        "value": round(_lexical_similarity(raw_text or "", rationale_text or ""), 4),
        "method": "lexical",
        "model": None,
    }


def _coverage(explainability: dict[str, Any]) -> dict[str, Any]:
    total = len(EXPECTED_NODES)
    hits = sum(1 for node in EXPECTED_NODES if node in explainability)
    return {
        "completed": hits,
        "expected": total,
        "ratio": round(hits / total, 3) if total else 0.0,
    }


def _build_signal_debug(signal_doc: dict, case_embedding: list[float] | None) -> dict[str, Any]:
    raw = signal_doc.get("raw_payload", {})
    enriched = signal_doc.get("enriched_payload", {})
    explainability = enriched.get("explainability") or {}
    metrics = enriched.get("metrics") or {}
    timings = metrics.get("timings_ms") or {}
    metadata = enriched.get("metadata") or {}

    rationale_text = " ".join(str(value) for value in explainability.values())
    semantic_similarity = _compute_semantic_similarity(raw.get("raw_text", ""), rationale_text)

    drift = _compute_drift(metadata.get("embedding"), case_embedding)

    return {
        "signal_id": raw.get("signal_id"),
        "reported_at": raw.get("reported_at"),
        "raw_text": raw.get("raw_text"),
        "location_text": raw.get("location_text"),
        "domain": enriched.get("domain"),
        "event_type": enriched.get("event_type"),
        "severity": enriched.get("severity"),
        "location": enriched.get("location") or {},
        "target_department": (metadata or {}).get("target_department"),
        "trace": _build_trace(explainability),
        "metrics": metrics,
        "timing_total_ms": round(sum(timings.values()), 2) if timings else None,
        "coverage": _coverage(explainability),
        "semantic_similarity": semantic_similarity,
        "drift_score": drift,
    }


@router.get("/debug/overview")
def debug_overview():
    signal_docs = storage.list_signals()
    case_docs = storage.list_cases()

    latest_signals = _latest_by(signal_docs, lambda doc: doc.get("raw_payload", {}).get("signal_id"))
    latest_cases = _latest_by(case_docs, lambda doc: doc.get("case_payload", {}).get("case_id"))

    case_by_id = {c.get("case_payload", {}).get("case_id"): c.get("case_payload", {}) for c in latest_cases}

    timings_by_node: dict[str, list[float]] = defaultdict(list)
    coverage_counts: dict[str, int] = defaultdict(int)
    similarity_samples: list[float] = []
    drift_samples: list[float] = []
    latency_samples: list[float] = []

    signals = []

    for doc in sorted(latest_signals, key=lambda d: d.get("saved_at", ""), reverse=True):
        raw = doc.get("raw_payload", {})
        enriched = doc.get("enriched_payload", {})
        explainability = enriched.get("explainability") or {}
        metrics = enriched.get("metrics") or {}
        timings = metrics.get("timings_ms") or {}
        metadata = enriched.get("metadata") or {}
        case_id = metadata.get("case_id")

        for node, value in timings.items():
            try:
                timings_by_node[node].append(float(value))
            except (TypeError, ValueError):
                continue

        for node in EXPECTED_NODES:
            if node in explainability:
                coverage_counts[node] += 1

        score_block = metrics.get("scores") or {}
        case_similarity = score_block.get("case_similarity")
        if isinstance(case_similarity, (int, float)):
            similarity_samples.append(float(case_similarity))

        drift = _compute_drift(metadata.get("embedding"), (case_by_id.get(case_id) or {}).get("embedding"))
        if drift is not None:
            drift_samples.append(drift)

        timing_total = round(sum(timings.values()), 2) if timings else None
        if isinstance(timing_total, (int, float)):
            latency_samples.append(float(timing_total))

        signals.append(
            {
                "signal_id": raw.get("signal_id"),
                "saved_at": doc.get("saved_at"),
                "domain": enriched.get("domain"),
                "event_type": enriched.get("event_type"),
                "severity": enriched.get("severity"),
                "case_id": case_id,
                "timing_total_ms": timing_total,
                "case_similarity": case_similarity,
                "drift_score": drift,
                "explainability_steps": len(explainability),
            }
        )

    coverage = {
        node: round((coverage_counts.get(node, 0) / len(latest_signals)), 3) if latest_signals else 0.0
        for node in EXPECTED_NODES
    }

    average_timings = {node: _avg(values) for node, values in timings_by_node.items()}
    avg_latency = _avg(latency_samples)

    return {
        "kpi": {
            "signals_total": len(latest_signals),
            "cases_total": len(latest_cases),
            "avg_latency_ms": avg_latency,
            "avg_case_similarity": _avg(similarity_samples) if similarity_samples else None,
            "avg_drift": _avg(drift_samples) if drift_samples else None,
        },
        "coverage": coverage,
        "timings_ms": average_timings,
        "nodes": EXPECTED_NODES,
        "models": {
            "text": LLM_TEXT_MODEL,
            "vision": LLM_VISION_MODEL,
            "embedding": GEMINI_EMBEDDING_MODEL,
        },
        "benchmarks": {
            "perplexity": {
                "status": "unavailable",
                "reason": "Perplexity requires logits; current provider does not expose them.",
            },
            "token_usage": {
                "status": "partial",
                "reason": "Token usage is captured only when provider returns usage metadata.",
            },
        },
        "signals": signals[:50],
    }


@router.get("/debug/case/{case_id}")
def debug_case(case_id: str):
    case_docs = _latest_by(storage.list_cases(), lambda doc: doc.get("case_payload", {}).get("case_id"))
    case_doc = next((doc for doc in case_docs if doc.get("case_payload", {}).get("case_id") == case_id), None)
    if not case_doc:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    case_payload = case_doc.get("case_payload", {})
    case_embedding = case_payload.get("embedding")
    signal_ids = case_payload.get("signals") or []

    signal_docs = _latest_by(storage.list_signals(), lambda doc: doc.get("raw_payload", {}).get("signal_id"))
    signal_by_id = {doc.get("raw_payload", {}).get("signal_id"): doc for doc in signal_docs}

    signals = []
    similarity_samples = []
    latency_samples = []
    drift_samples = []

    for signal_id in signal_ids:
        doc = signal_by_id.get(signal_id)
        if not doc:
            continue
        signal_debug = _build_signal_debug(doc, case_embedding)
        signals.append(signal_debug)

        similarity = (signal_debug.get("semantic_similarity") or {}).get("value")
        if isinstance(similarity, (int, float)):
            similarity_samples.append(float(similarity))

        latency = signal_debug.get("timing_total_ms")
        if isinstance(latency, (int, float)):
            latency_samples.append(float(latency))

        drift = signal_debug.get("drift_score")
        if isinstance(drift, (int, float)):
            drift_samples.append(float(drift))

    return {
        "case": case_payload,
        "signals": signals,
        "summary": {
            "signals_count": len(signals),
            "avg_semantic_similarity": _avg(similarity_samples) if similarity_samples else None,
            "avg_latency_ms": _avg(latency_samples) if latency_samples else None,
            "avg_drift": _avg(drift_samples) if drift_samples else None,
        },
        "models": {
            "text": LLM_TEXT_MODEL,
            "vision": LLM_VISION_MODEL,
            "embedding": GEMINI_EMBEDDING_MODEL,
        },
    }


@router.get("/debug/signal/{signal_id}")
def debug_signal(signal_id: str):
    signal_docs = _latest_by(storage.list_signals(), lambda doc: doc.get("raw_payload", {}).get("signal_id"))
    doc = next((item for item in signal_docs if item.get("raw_payload", {}).get("signal_id") == signal_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Signal '{signal_id}' not found")

    enriched = doc.get("enriched_payload", {})
    metadata = enriched.get("metadata") or {}
    case_embedding = None
    if metadata.get("case_id"):
        case_doc = storage.get_latest_case(metadata.get("case_id")) or {}
        case_embedding = (case_doc.get("case_payload") or {}).get("embedding")

    return {
        "signal": _build_signal_debug(doc, case_embedding),
        "models": {
            "text": LLM_TEXT_MODEL,
            "vision": LLM_VISION_MODEL,
            "embedding": GEMINI_EMBEDDING_MODEL,
        },
    }
