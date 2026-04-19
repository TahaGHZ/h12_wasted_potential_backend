import json
import logging
from backend.agents.normalizer.contracts import NormalizerOutput
from backend.agents.normalizer.prompts import NORMALIZER_SYSTEM_PROMPT, build_normalizer_user_prompt
from backend.config.llm import LLMService

class NormalizerAgent:
    def __init__(self):
        self.llm = LLMService()
        self.logger = logging.getLogger("signal_pipeline")

    def run(self, raw_signal: dict) -> NormalizerOutput:
        """
        Takes raw_signal dict, calls the LLM, and returns a verified NormalizerOutput
        """
        user_prompt = build_normalizer_user_prompt(
            raw_text=raw_signal.get("raw_text", ""),
            location_text=raw_signal.get("location_text", ""),
            source_type=raw_signal.get("source_type", "unknown")
        )

        try:
            # 1. Call LLM with images
            json_response = self.llm.generate_json(
                system_prompt=NORMALIZER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                image_urls=raw_signal.get("image_urls", []),
                temperature=0.1
            )
            
            # 2. Parse JSON
            data = json.loads(json_response)
            
            # 3. Validate with Pydantic
            output = NormalizerOutput(**data)
            return output
            
        except Exception as e:
            # Fallback if LLM fails or parsing fails
            self.logger.exception("NormalizerAgent error: %s", e)
            return NormalizerOutput(
                standardized_text=raw_signal.get("raw_text", ""),
                language="Unknown",
                key_entities=[],
                confidence=0.0,
                rationale=f"Error processing: {str(e)}"
            )
