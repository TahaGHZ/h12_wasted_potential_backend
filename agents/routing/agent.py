import json
import logging
from backend.agents.routing.contracts import RoutingOutput
from backend.agents.routing.prompts import ROUTING_SYSTEM_PROMPT, build_routing_user_prompt
from backend.config.llm import LLMService

class RoutingAgent:
    def __init__(self):
        self.llm = LLMService()
        self.logger = logging.getLogger("signal_pipeline")

    def run(self, domain: str, event_type: str, severity: float) -> RoutingOutput:
        """
        Routes the report to the appropriate department using Llama 70B for policy-based dispatch.
        """
        user_prompt = build_routing_user_prompt(domain, event_type, severity)

        try:
            json_response = self.llm.generate_json(
                system_prompt=ROUTING_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1
            )
            
            data = json.loads(json_response)
            return RoutingOutput(**data)
            
        except Exception as e:
            self.logger.exception("RoutingAgent error: %s", e)
            return RoutingOutput(
                department="General Municipal Office",
                confidence=0.0,
                rationale=f"Error in automated routing: {str(e)}"
            )
