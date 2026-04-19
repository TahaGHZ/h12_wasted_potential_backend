import json
import logging
from backend.agents.domain_classifier.contracts import DomainClassifierOutput
from backend.agents.domain_classifier.prompts import DOMAIN_CLASSIFIER_SYSTEM_PROMPT, build_domain_classifier_user_prompt
from backend.config.llm import LLMService

class DomainClassifierAgent:
    def __init__(self):
        self.llm = LLMService()
        self.logger = logging.getLogger("signal_pipeline")

    def run(self, normalized_text: str, key_entities: list) -> DomainClassifierOutput:
        """
        Runs the classification using Llama 70B (automatically chosen by LLMService for text).
        """
        user_prompt = build_domain_classifier_user_prompt(normalized_text, key_entities)

        try:
            json_response = self.llm.generate_json(
                system_prompt=DOMAIN_CLASSIFIER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0 # Strict classification
            )
            
            data = json.loads(json_response)
            return DomainClassifierOutput(**data)
            
        except Exception as e:
            self.logger.exception("DomainClassifierAgent error: %s", e)
            # Fallback to general classification
            return DomainClassifierOutput(
                domain="Environment", 
                confidence=0.0,
                rationale=f"Error in automated classification: {str(e)}"
            )
