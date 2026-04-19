import json
import logging
from backend.agents.event_type_classifier.contracts import EventTypeOutput
from backend.agents.event_type_classifier.prompts import EVENT_TYPE_SYSTEM_PROMPT, build_event_type_user_prompt
from backend.config.llm import LLMService

class EventTypeClassifierAgent:
    def __init__(self):
        self.llm = LLMService()
        self.logger = logging.getLogger("signal_pipeline")

    def run(self, normalized_text: str, domain: str) -> EventTypeOutput:
        """
        Deep classification using Llama 70B.
        """
        user_prompt = build_event_type_user_prompt(normalized_text, domain)

        try:
            json_response = self.llm.generate_json(
                system_prompt=EVENT_TYPE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1
            )
            
            data = json.loads(json_response)
            return EventTypeOutput(**data)
            
        except Exception as e:
            self.logger.exception("EventTypeClassifierAgent error: %s", e)
            return EventTypeOutput(
                event_type="General Issue",
                confidence=0.0,
                rationale=f"Error in automated classification: {str(e)}"
            )
