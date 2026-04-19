import json
import logging
from backend.config.llm import LLMService
from .contracts import BriefingInput, BriefingOutput
from .prompts import SYSTEM_PROMPT, build_briefing_user_prompt

class BriefingAgent:

    def __init__(self):
        self.llm = LLMService()
        self.logger = logging.getLogger("signal_pipeline")

    def run(self, data: BriefingInput) -> BriefingOutput:
        user_prompt = build_briefing_user_prompt(data.case.model_dump())

        try:
            json_response = self.llm.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2
            )
            payload = json.loads(json_response)
            return BriefingOutput(
                case_id=data.case_id,
                title=payload.get("title", data.case.title),
                summary=payload.get("summary", data.case.description or ""),
                key_facts=payload.get("key_facts", []),
                priority_score=payload.get("priority_score", data.case.priority_score),
                confidence=payload.get("confidence", 0.5),
                rationale=payload.get("rationale")
            )
        except Exception as exc:
            self.logger.exception("BriefingAgent error: %s", exc)
            return BriefingOutput(
                case_id=data.case_id,
                title=data.case.title,
                summary=data.case.description or "",
                key_facts=[],
                priority_score=data.case.priority_score,
                confidence=0.0,
                rationale=f"Fallback briefing due to error: {exc}"
            )
