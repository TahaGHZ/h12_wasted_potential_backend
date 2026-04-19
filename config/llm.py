import logging
import os
import httpx
from openai import OpenAI
from dotenv import load_dotenv

# Ensure .env is loaded from the backend root regardless of where the app is started
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=env_path)

TOKEN_FACTORY_KEY = os.getenv("TOKEN_FACTORY_KEY")
TOKEN_FACTORY_BASE_URL = os.getenv("TOKEN_FACTORY_BASE_URL")
LLM_TEXT_MODEL = os.getenv("LLM_TEXT_MODEL", "hosted_vllm/Llama-3.1-70B-Instruct")
LLM_VISION_MODEL = os.getenv("LLM_VISION_MODEL", "hosted_vllm/llava-1.5-7b-hf")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
GEMINI_EMBEDDING_DIM = int(os.getenv("GEMINI_EMBEDDING_DIM", "768"))
GEMINI_EMBEDDING_TASK = os.getenv("GEMINI_EMBEDDING_TASK", "CLUSTERING")
LLM_HTTP_TIMEOUT = float(os.getenv("LLM_HTTP_TIMEOUT", "30"))
TOKEN_FACTORY_TLS_VERIFY = os.getenv("TOKEN_FACTORY_TLS_VERIFY", "true").lower() == "true"

logger = logging.getLogger("signal_pipeline")

class LLMService:
    def __init__(self):
        self.last_model = None
        self.last_usage = None
        custom_http_client = httpx.Client(
            verify=TOKEN_FACTORY_TLS_VERIFY,
            timeout=httpx.Timeout(LLM_HTTP_TIMEOUT)
        )
        
        if not TOKEN_FACTORY_KEY:
            raise ValueError(f"TOKEN_FACTORY_KEY not found in .env (path checked: {env_path})")
            
        self.client = OpenAI(
            api_key=TOKEN_FACTORY_KEY,
            base_url=TOKEN_FACTORY_BASE_URL,
            http_client=custom_http_client
        )

    def generate_json(self, system_prompt: str, user_prompt: str, image_urls: list[str] = None, temperature: float = 0.2, response_model=None) -> str:
        """
        Generates a JSON response from the LLM, supporting multimodal inputs.
        Automatically switches between Text and Vision models based on input content.
        If `response_model` (a Pydantic BaseModel) is provided, its schema is appended
        to the prompt and the out is parsed and validated using it.
        """
        # Determine which model to use
        is_vision_task = bool(image_urls and len(image_urls) > 0)
        selected_model = LLM_VISION_MODEL if is_vision_task else LLM_TEXT_MODEL
        
        logger.info(
            "LLM routing: %s mode using %s",
            "VISION" if is_vision_task else "TEXT",
            selected_model
        )

        # Inject Pydantic schema enforcement if a model is provided
        if response_model is not None:
            schema_json = response_model.schema_json() if hasattr(response_model, 'schema_json') else response_model.model_json_schema()
            system_prompt += f"\n\nYou MUST return a JSON object that perfectly matches this schema:\n{schema_json}"

        # Build content
        if is_vision_task:
            # Multimodal format for vision-capable models
            content = [{"type": "text", "text": user_prompt}]
            for url in image_urls:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
        else:
            # Standard text format for better compatibility with high-reasoning models
            content = user_prompt

        response = self.client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            temperature=temperature,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        self.last_model = selected_model
        self.last_usage = getattr(response, "usage", None)
        content_str = response.choices[0].message.content
        cleaned = self._clean_json_output(content_str)
        
        if response_model is not None:
            # Use Pydantic to validate the cleaned string and return it back as a dict or the model instance
            # To avoid breaking existing codebase that expects a string, we can return the validated json dumped 
            # or return the model instance if the caller wants it. We will return the raw validated string.
            import json
            validated_obj = response_model.parse_raw(cleaned) if hasattr(response_model, 'parse_raw') else response_model.model_validate_json(cleaned)
            return validated_obj.model_dump_json() if hasattr(validated_obj, 'model_dump_json') else validated_obj.json()
            
        return cleaned

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 800) -> str:
        selected_model = LLM_TEXT_MODEL

        response = self.client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.last_model = selected_model
        self.last_usage = getattr(response, "usage", None)
        return response.choices[0].message.content.strip()

    def _clean_json_output(self, content: str) -> str:
        """
        Extracts JSON from conversational text and sanitizes it for parsing.
        Handles markdown blocks, conversational text before/after JSON,
        and LLM escaping quirks.
        """
        import re
        
        content = content.strip()
        
        # 1. Strip Markdown blocks
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        # 2. Extract JSON from conversational text using bracket matching
        # Find the first '{' or '[' that indicates start of JSON
        start_idx = -1
        for i, char in enumerate(content):
            if char in ('{', '['):
                start_idx = i
                break
        
        if start_idx >= 0:
            # Extract from first bracket, matching to its closing pair
            opening_char = content[start_idx]
            closing_char = '}' if opening_char == '{' else ']'
            bracket_count = 0
            end_idx = -1
            in_string = False
            escape_next = False
            
            for i in range(start_idx, len(content)):
                char = content[i]
                
                # Handle string context (don't count brackets inside strings)
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == opening_char:
                        bracket_count += 1
                    elif char == closing_char:
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = i + 1
                            break
            
            if end_idx > 0:
                content = content[start_idx:end_idx]

        # 3. Fix AI "over-escaping" underscores (LLaMa/Llava common quirk)
        content = content.replace(r'\_', '_')

        # 4. Fix other unescaped backslashes (NOT followed by valid JSON escape chars)
        content = re.sub(r'\\(?![/"\\bfnrtu])', r'\\\\', content)

        return content


class GeminiEmbeddingService:
    def __init__(self):
        self.enabled = True
        self.model = GEMINI_EMBEDDING_MODEL
        self.dim = GEMINI_EMBEDDING_DIM
        self.task = GEMINI_EMBEDDING_TASK

        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not found; embeddings are disabled.")
            self.enabled = False
            self.client = None
            self._types = None
            return

        try:
            from google import genai
            from google.genai import types
        except Exception as exc:
            logger.warning("google-genai not available; embeddings are disabled: %s", exc)
            self.enabled = False
            self.client = None
            self._types = None
            return

        self._types = types
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def embed_texts(self, contents: list[str]) -> list[list[float]]:
        if not self.enabled:
            return []
        if not contents:
            return []

        safe_contents = [text if text and text.strip() else "none" for text in contents]

        config = None
        if self.model.startswith("gemini-embedding-001"):
            config = self._types.EmbedContentConfig(
                task_type=self.task,
                output_dimensionality=self.dim
            )
        else:
            config = self._types.EmbedContentConfig(
                output_dimensionality=self.dim
            )

        try:
            result = self.client.models.embed_content(
                model=self.model,
                contents=safe_contents,
                config=config
            )
        except Exception as exc:
            logger.exception("Gemini embedding failed: %s", exc)
            return []

        embeddings = [embedding.values for embedding in result.embeddings]
        if self.dim < 3072:
            embeddings = [self._normalize(vec) for vec in embeddings]

        return embeddings

    def _normalize(self, vector: list[float]) -> list[float]:
        if not vector:
            return vector
        magnitude = sum(value * value for value in vector) ** 0.5
        if magnitude == 0:
            return vector
        return [value / magnitude for value in vector]
