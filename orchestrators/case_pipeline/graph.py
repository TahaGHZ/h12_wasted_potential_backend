from langgraph.graph import StateGraph
from .state import PipelineState
from .nodes import case_builder_node

def build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("case_builder", case_builder_node)

    graph.set_entry_point("case_builder")

    graph.set_finish_point("case_builder")

    return graph.compile()
