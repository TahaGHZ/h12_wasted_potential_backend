import json
from typing import List, Any

import pytest
from fastapi.testclient import TestClient

import backend.api.listener as listener
from backend.main import app


def _sample_payload() -> dict:
    return {
        "signal_id": "sig-123",
        "source_type": "unit-test",
        "raw_text": "Smoke near the port.",
        "location_text": "Gabes port",
        "reported_at": "2026-04-18T10:00:00Z",
        "image_urls": [],
        "attachments": [],
        "metadata": {"test": True},
    }


def _parse_ndjson(lines: List[Any]) -> List[dict]:
    parsed = []
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        if line:
            parsed.append(json.loads(line))
    return parsed


class _FakePipeline:
    async def astream_run(self, signal):
        yield {"type": "trace", "message": "ok"}
        yield {"type": "result", "data": {"case_id": "case-1"}}


class _ErrorPipeline:
    async def astream_run(self, signal):
        raise RuntimeError("boom")
        yield  # pragma: no cover


@pytest.fixture(autouse=True)
def _reset_pipeline(monkeypatch):
    monkeypatch.setattr(listener, "pipeline", _FakePipeline())


def test_report_streams_ndjson():
    client = TestClient(app)
    with client.stream("POST", "/api/v1/report", json=_sample_payload()) as response:
        assert response.status_code == 200
        chunks = _parse_ndjson(list(response.iter_lines()))

    assert chunks[0]["type"] == "trace"
    assert chunks[1]["type"] == "result"
    assert chunks[1]["data"]["case_id"] == "case-1"


def test_report_streams_error_chunk(monkeypatch):
    monkeypatch.setattr(listener, "pipeline", _ErrorPipeline())

    client = TestClient(app)
    with client.stream("POST", "/api/v1/report", json=_sample_payload()) as response:
        assert response.status_code == 200
        chunks = _parse_ndjson(list(response.iter_lines()))

    assert chunks[0]["type"] == "error"
    assert "boom" in chunks[0]["message"]
