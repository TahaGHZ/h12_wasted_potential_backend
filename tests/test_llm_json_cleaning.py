import json
import pytest
from unittest.mock import Mock, patch
from backend.config.llm import LLMService

@pytest.fixture
def llm_service():
    """Create LLMService with mocked OpenAI client."""
    with patch('backend.config.llm.OpenAI'):
        with patch('backend.config.llm.TOKEN_FACTORY_KEY', 'mock-key'):
            service = LLMService()
            return service

class TestCleanJsonOutput:
    """Test _clean_json_output handles various LLM response formats."""

    def test_clean_json_basic(self, llm_service):
        content = '{"key": "value"}'
        result = llm_service._clean_json_output(content)
        assert json.loads(result) == {"key": "value"}

    def test_clean_json_with_markdown(self, llm_service):
        content = '```json\n{"key": "value"}\n```'
        result = llm_service._clean_json_output(content)
        assert json.loads(result) == {"key": "value"}

    def test_clean_json_with_conversational_text(self, llm_service):
        content = 'Here is the extracted data: {"key": "value"} I hope this helps!'
        result = llm_service._clean_json_output(content)
        assert json.loads(result) == {"key": "value"}

    def test_clean_json_with_leading_explanation(self, llm_service):
        content = 'Based on the analysis:\n{"status": "success", "count": 5}'
        result = llm_service._clean_json_output(content)
        assert json.loads(result) == {"status": "success", "count": 5}

    def test_clean_json_array(self, llm_service):
        content = 'The results are: [{"id": 1}, {"id": 2}] Thank you!'
        result = llm_service._clean_json_output(content)
        assert json.loads(result) == [{"id": 1}, {"id": 2}]

    def test_clean_json_nested_objects(self, llm_service):
        content = 'Please find: {"user": {"name": "John", "age": 30}} below.'
        result = llm_service._clean_json_output(content)
        data = json.loads(result)
        assert data["user"]["name"] == "John"
        assert data["user"]["age"] == 30

    def test_clean_json_with_escaped_quotes_in_strings(self, llm_service):
        content = 'Result: {"message": "He said \\"hello\\""}!'
        result = llm_service._clean_json_output(content)
        data = json.loads(result)
        assert 'hello' in data["message"]

    def test_clean_json_with_underscore_escaping(self, llm_service):
        content = '{"field\\_name": "value"}'
        result = llm_service._clean_json_output(content)
        data = json.loads(result)
        assert "field_name" in data

    def test_clean_json_markdown_and_conversational(self, llm_service):
        content = 'Here is the result:\n```json\n{"status": "ok"}\n```\nLet me know if you need more.'
        result = llm_service._clean_json_output(content)
        assert json.loads(result) == {"status": "ok"}



    def test_clean_json_whitespace(self, llm_service):
        content = '   {"key": "value"}   \n'
        result = llm_service._clean_json_output(content)
        assert json.loads(result) == {"key": "value"}