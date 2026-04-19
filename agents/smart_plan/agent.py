import json
import logging
import uuid
from backend.config.llm import LLMService
from .contracts import SmartPlanInput, SmartPlanOutput
from .prompts import SYSTEM_PROMPT, build_smart_plan_user_prompt

class SmartPlanAgent:

    def __init__(self):
        self.llm = LLMService()
        self.logger = logging.getLogger("signal_pipeline")

    def run(self, data: SmartPlanInput) -> SmartPlanOutput:
        user_prompt = build_smart_plan_user_prompt(data.case.model_dump())

        try:
            json_response = self.llm.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2
            )
            payload = json.loads(json_response)
            return SmartPlanOutput(
                case_id=data.case_id,
                plan_id=payload.get("plan_id", f"plan_{uuid.uuid4().hex}"),
                title=payload.get("title", f"Action Plan for {data.case.title}"),
                action_items=payload.get("action_items", []),
                related_cases=payload.get("related_cases", [data.case_id]),
                confidence=payload.get("confidence", 0.5),
                rationale=payload.get("rationale")
            )
        except Exception as exc:
            self.logger.exception("SmartPlanAgent error: %s", exc)
            return SmartPlanOutput(
                case_id=data.case_id,
                plan_id=f"plan_{uuid.uuid4().hex}",
                title=f"Action Plan for {data.case.title}",
                action_items=[],
                related_cases=[data.case_id],
                confidence=0.0,
                rationale=f"Fallback plan due to error: {exc}"
            )
