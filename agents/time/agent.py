import json
import logging
from backend.agents.time.contracts import TimeOutput
from backend.agents.time.prompts import TIME_AGENT_SYSTEM_PROMPT, build_time_user_prompt
from backend.config.llm import LLMService

class TimeAgent:
    def __init__(self):
        self.llm = LLMService()
        self.logger = logging.getLogger("signal_pipeline")

    def run(self, raw_text: str, reference_time: str) -> TimeOutput:
        """
        Calculates normalized time using Llama 70B logic.
        """
        user_prompt = build_time_user_prompt(raw_text, reference_time)

        try:
            json_response = self.llm.generate_json(
                system_prompt=TIME_AGENT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
                response_model=TimeOutput
            )
            
            data = json.loads(json_response)
            return TimeOutput(**data)
            
        except Exception as e:
            self.logger.exception("TimeAgent error: %s", e)
            return TimeOutput(
                normalized_timestamp=reference_time,
                confidence=0.0,
                rationale=f"Error in time normalizing: {str(e)}"
            )
