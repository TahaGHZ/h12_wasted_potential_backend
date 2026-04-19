import traceback
import json
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.contracts.signals import RawSignal
from backend.orchestrators.signal_pipeline.orchestrator import SignalPipelineOrchestrator

router = APIRouter()
pipeline = SignalPipelineOrchestrator()

@router.post("/report")
async def receive_report(signal: RawSignal):
    """
    Accepts inbound reports and streams the pipeline processing trace.
    Returns a sequence of JSON chunks.
    """
    logging.getLogger("signal_pipeline").info("API RECEIVER: Handling report %s", signal.signal_id)
    async def event_generator():
        try:
            async for chunk in pipeline.astream_run(signal):
                # Standard NDJSON format (Newline Delimited JSON)
                yield json.dumps(chunk) + "\n"
        except Exception as e:
            error_trace = traceback.format_exc()
            logging.getLogger("signal_pipeline").error("PIPELINE CRASH: %s", error_trace)
            yield json.dumps({"type": "error", "message": str(e), "trace": error_trace}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
