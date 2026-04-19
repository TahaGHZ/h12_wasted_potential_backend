from langgraph.graph import StateGraph
from .state import PipelineState
from .nodes import briefing_node

def build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("briefing", briefing_node)

    graph.set_entry_point("briefing")

    graph.set_finish_point("briefing")

    return graph.compile()
