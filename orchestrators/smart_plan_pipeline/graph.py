from langgraph.graph import StateGraph
from .state import PipelineState
from .nodes import smart_plan_node

def build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("smart_plan", smart_plan_node)

    graph.set_entry_point("smart_plan")

    graph.set_finish_point("smart_plan")

    return graph.compile()
