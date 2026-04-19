import json
import logging
from backend.agents.severity.contracts import SeverityOutput
from backend.agents.severity.prompts import SEVERITY_SYSTEM_PROMPT, build_severity_user_prompt
from backend.config.llm import LLMService

class SeverityAgent:
    def __init__(self):
        self.llm = LLMService()
        self.logger = logging.getLogger("signal_pipeline")

    def run(self, normalized_text: str, domain: str, key_entities: list, extra_context: str = "") -> SeverityOutput:
        """
        Assesses severity/priority using Llama 70B for maximum reasoning reliability.
        Includes context from previous agents for holistic impact assessment.
        """
        user_prompt = build_severity_user_prompt(normalized_text, domain, key_entities, extra_context)

        try:
            json_response = self.llm.generate_json(
                system_prompt=SEVERITY_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1
            )
            
            data = json.loads(json_response)
            return SeverityOutput(**data)
            
        except Exception as e:
            self.logger.exception("SeverityAgent error: %s", e)
            return SeverityOutput(
                priority_score=1,
                rationale=f"Fallback due to assessment error: {str(e)}",
                confidence=0.0
            )
