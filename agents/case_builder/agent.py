import uuid
from typing import Optional, Tuple
from backend.config.llm import GeminiEmbeddingService
from backend.config.storage import StorageService
from backend.contracts.cases import Case
from .contracts import CaseBuilderInput, CaseBuilderOutput
from .policies import (
    SIMILARITY_THRESHOLD,
    build_embedding_text,
    compute_priority_score,
    now_iso
)

class CaseBuilderAgent:

    def __init__(self):
        self.embedder = GeminiEmbeddingService()
        self.storage = StorageService()

    def run(self, data: CaseBuilderInput) -> CaseBuilderOutput:
        enriched = data.enriched_signal
        embedding_text = build_embedding_text(enriched)
        embedding_values = self.embedder.embed_texts([embedding_text])
        embedding = embedding_values[0] if embedding_values else None

        case_match = self._find_best_case_match(embedding) if embedding else None
        signal_match = self._find_best_signal_match(embedding) if embedding else None

        created_new = False
        similarity = 0.0
        matched_case_id = None
        matched_signal_id = None
        matched_signal_embedding = None

        if case_match and case_match[1] >= SIMILARITY_THRESHOLD:
            matched_case_id = case_match[0]
            similarity = case_match[1]
        elif signal_match and signal_match[1] >= SIMILARITY_THRESHOLD:
            matched_signal_id = signal_match[0]
            matched_signal_embedding = signal_match[2]
            similarity = signal_match[1]

        existing_case_payload = None
        if matched_case_id:
            latest = self.storage.get_latest_case(matched_case_id)
            existing_case_payload = latest.get("case_payload") if latest else None

        if not existing_case_payload:
            created_new = True
            case_id = matched_case_id or f"case_{uuid.uuid4().hex}"
            signals = []
            if matched_signal_id:
                signals.append(matched_signal_id)
            signals.append(data.signal_id)

            case_embedding, embedding_count = self._seed_embedding(
                embedding,
                matched_signal_embedding
            ) if embedding else (None, 0)

            case = Case(
                case_id=case_id,
                title=self._build_title(enriched),
                description=f"[{enriched.original_text}] {enriched.description or ''}".strip(),
                signals=signals,
                priority_score=compute_priority_score(enriched.severity or 0.0, len(signals)),
                domain=enriched.domain,
                event_type=enriched.event_type,
                location=(enriched.location or {}).get("neighborhood"),
                embedding=case_embedding,
                embedding_model=self.embedder.model,
                embedding_dim=self.embedder.dim,
                embedding_count=embedding_count,
                created_at=now_iso(),
                updated_at=now_iso(),
                rationale=self._build_rationale(similarity, matched_case_id, matched_signal_id, len(signals))
            )
            previous_priority = None
        else:
            case_id = existing_case_payload.get("case_id")
            signals = list(existing_case_payload.get("signals", []))
            if data.signal_id not in signals:
                signals.append(data.signal_id)

            previous_priority = existing_case_payload.get("priority_score")
            updated_priority = compute_priority_score(enriched.severity or 0.0, len(signals))

            case_embedding, embedding_count = self._update_embedding(
                embedding,
                existing_case_payload
            ) if embedding else (existing_case_payload.get("embedding"), existing_case_payload.get("embedding_count", 0))

            case = Case(
                case_id=case_id,
                title=existing_case_payload.get("title") or self._build_title(enriched),
                description=f"[{enriched.original_text}] {existing_case_payload.get('description') or enriched.description or ''}".strip(),
                assigned_to=existing_case_payload.get("assigned_to"),
                status=existing_case_payload.get("status", "open"),
                events=existing_case_payload.get("events", []),
                signals=signals,
                priority_score=updated_priority,
                domain=existing_case_payload.get("domain") or enriched.domain,
                event_type=existing_case_payload.get("event_type") or enriched.event_type,
                location=existing_case_payload.get("location") or (enriched.location or {}).get("neighborhood"),
                embedding=case_embedding,
                embedding_model=self.embedder.model,
                embedding_dim=self.embedder.dim,
                embedding_count=embedding_count,
                created_at=existing_case_payload.get("created_at"),
                updated_at=now_iso(),
                rationale=self._build_rationale(similarity, case_id, matched_signal_id, len(signals))
            )

        case_path = self.storage.save_case(case)
        priority_delta = None
        if previous_priority is not None:
            priority_delta = case.priority_score - previous_priority

        confidence = similarity if similarity > 0 else 0.5

        embedding_model = self.embedder.model if embedding else None
        embedding_dim = self.embedder.dim if embedding else None

        return CaseBuilderOutput(
            signal_id=data.signal_id,
            case_id=case.case_id,
            created_new=created_new,
            similarity=similarity,
            priority_score=case.priority_score or 0.0,
            previous_priority_score=previous_priority,
            priority_delta=priority_delta,
            case=case,
            case_path=case_path,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
            confidence=confidence,
            rationale=case.rationale
        )

    def _find_best_case_match(self, embedding: list[float]) -> Optional[Tuple[str, float]]:
        cases = self.storage.list_cases()
        scored = []
        for item in cases:
            payload = item.get("case_payload", {})
            case_embedding = payload.get("embedding")
            if not case_embedding:
                continue
            similarity = self._cosine_similarity(embedding, case_embedding)
            scored.append((payload.get("case_id"), similarity))

        scored.sort(key=lambda item: item[1], reverse=True)
        if not scored:
            return None

        best_case_id, best_similarity = scored[0]
        if best_case_id is None:
            return None
        return best_case_id, best_similarity

    def _find_best_signal_match(self, embedding: list[float]) -> Optional[Tuple[str, float, list[float]]]:
        signals = self.storage.list_signals()
        scored = []
        for item in signals:
            enriched = item.get("enriched_payload", {})
            metadata = enriched.get("metadata", {})
            signal_embedding = metadata.get("embedding")
            if not signal_embedding:
                continue
            similarity = self._cosine_similarity(embedding, signal_embedding)
            scored.append((enriched.get("signal_id"), similarity, signal_embedding))

        scored.sort(key=lambda item: item[1], reverse=True)
        if not scored:
            return None

        best_signal_id, best_similarity, best_embedding = scored[0]
        if best_signal_id is None:
            return None
        return best_signal_id, best_similarity, best_embedding

    def _update_embedding(self, embedding: list[float], case_payload: dict) -> Tuple[list[float], int]:
        existing = case_payload.get("embedding")
        count = int(case_payload.get("embedding_count") or 0)
        if not existing or count == 0:
            return embedding, 1

        combined = [
            (existing[i] * count + embedding[i]) / (count + 1)
            for i in range(min(len(existing), len(embedding)))
        ]
        return combined, count + 1

    def _seed_embedding(self, embedding: list[float], matched_embedding: Optional[list[float]]) -> Tuple[list[float], int]:
        if not matched_embedding:
            return embedding, 1

        length = min(len(embedding), len(matched_embedding))
        combined = [
            (embedding[i] + matched_embedding[i]) / 2
            for i in range(length)
        ]
        return combined, 2

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0

        length = min(len(left), len(right))
        dot = sum(left[i] * right[i] for i in range(length))
        left_norm = sum(left[i] * left[i] for i in range(length)) ** 0.5
        right_norm = sum(right[i] * right[i] for i in range(length)) ** 0.5
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)

    def _build_title(self, enriched) -> str:
        neighborhood = (enriched.location or {}).get("neighborhood", "Gabes")
        event_type = enriched.event_type or "Incident"
        return f"{event_type} in {neighborhood}"

    def _build_rationale(self, similarity: float, case_id: Optional[str], signal_id: Optional[str], volume: int) -> str:
        if case_id:
            return f"Matched existing case {case_id} with similarity {similarity:.2f}; updated volume to {volume}."
        if signal_id:
            return f"Seeded new case from similar signal {signal_id} (similarity {similarity:.2f}); volume {volume}."
        return f"Created new case; volume {volume}."
