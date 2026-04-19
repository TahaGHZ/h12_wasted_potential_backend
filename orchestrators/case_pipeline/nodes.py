from backend.contracts.signals import EnrichedSignal
from backend.agents.case_builder.agent import CaseBuilderAgent
from backend.agents.case_builder.contracts import CaseBuilderInput

def case_builder_node(state):
    enriched_signal = EnrichedSignal(**state["signal"])
    output = CaseBuilderAgent().run(
        CaseBuilderInput(
            signal_id=enriched_signal.signal_id,
            enriched_signal=enriched_signal
        )
    )
    return {"result": output.model_dump()}
