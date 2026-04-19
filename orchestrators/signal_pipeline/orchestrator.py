import json
import logging
from .graph import build_graph
from backend.contracts.signals import RawSignal

# Configure logger
logger = logging.getLogger("signal_pipeline")
logger.setLevel(logging.INFO)

class SignalPipelineOrchestrator:

    def __init__(self):
        self.graph = build_graph()


    async def astream_run(self, raw_signal: RawSignal):
        """
        Streams updates from the graph using astream.
        Yields trace messages when nodes finish and the final result.
        """
        logger.info(f"Starting pipeline execution for signal: {raw_signal.signal_id}")
        yield {"type": "trace", "message": "Signal Pipeline: Starting Graph Execution..."}
        
        initial_state = {
            "signal": raw_signal.model_dump(),
            "enriched": {},
            "result": None
        }

        try:
            # Friendly display names mapping back from node finishes
            display_names = {
                "signal_receiver": "Signal validated and received.",
                "normalizer": "AI processing artifacts & translating...",
                "geo": "Spatial intelligence mapping neighborhood...",
                "time": "Normalizing reported time context...",
                "domain_classifier": "Categorizing domain & audit rationale...",
                "event_type_classifier": "Refining event sub-type...",
                "severity": "Calculating priority (0-10 scale)...",
                "routing": "Determining target department...",
                "case_builder": "Finalizing and saving to vault..."
            }

            async for update in self.graph.astream(initial_state, stream_mode="updates"):
                # update is a dict: {node_name: node_output}
                for node_name, output in update.items():
                    logger.info(f"Node complete: {node_name}")
                    
                    # 1. Send specific trace based on node completion
                    msg = display_names.get(node_name, f"Completed {node_name}.")
                    
                    # Enrich with data if available (e.g. for Geo or Severity)
                    enriched = output.get("enriched", {})
                    if node_name == "severity":
                        msg = f"Severity set to {enriched.get('severity', '?')}/10."
                    elif node_name == "geo":
                        loc = enriched.get("location", {})
                        msg = f"Located at {loc.get('neighborhood', 'Gabès')}."
                    elif node_name == "domain_classifier":
                        msg = f"Targeting {enriched.get('domain', 'Unknown')} sector."
                    
                    yield {"type": "trace", "message": msg}

                    enriched = output.get("enriched", {})
                    metrics = enriched.get("metrics", {})
                    debug_frame = {
                        "type": "debug",
                        "node": node_name,
                        "message": msg,
                        "timing_ms": (metrics.get("timings_ms") or {}).get(node_name),
                        "tokens": (metrics.get("tokens") or {}).get(node_name),
                        "model": (metrics.get("models") or {}).get(node_name),
                        "scores": metrics.get("scores") or {},
                    }
                    yield debug_frame

                # 2. Finally, yield the total result if the graph is done
                # Note: astream with mode="updates" yields only the updates.
                # The final result can be gathered from the last seen state if needed,
                # but case_builder_node already computes the final 'result'.
                if "case_builder" in update:
                    yield {"type": "result", "data": update["case_builder"].get("result", {})}

        except Exception as e:
            logger.error(f"Critical error in pipeline: {str(e)}", exc_info=True)
            yield {"type": "error", "message": str(e)}
