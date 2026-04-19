from langgraph.graph import StateGraph
from .state import PipelineState
from .nodes import (
    signal_receiver_node,
    normalizer_node,
    geo_node,
    time_node,
    domain_classifier_node,
    event_type_classifier_node,
    severity_node,
    routing_node,
    case_builder_node
)

def build_graph():
    graph = StateGraph(PipelineState)

    # Add all nodes
    graph.add_node("signal_receiver", signal_receiver_node)
    graph.add_node("normalizer", normalizer_node)
    graph.add_node("geo", geo_node)
    graph.add_node("time", time_node)
    graph.add_node("domain_classifier", domain_classifier_node)
    graph.add_node("event_type_classifier", event_type_classifier_node)
    graph.add_node("severity", severity_node)
    graph.add_node("routing", routing_node)
    graph.add_node("case_builder", case_builder_node)

    # Define edges
    graph.add_edge("signal_receiver", "normalizer")
    graph.add_edge("normalizer", "geo")
    graph.add_edge("geo", "time")
    graph.add_edge("time", "domain_classifier")
    graph.add_edge("domain_classifier", "event_type_classifier")
    graph.add_edge("event_type_classifier", "severity")
    graph.add_edge("severity", "routing")
    graph.add_edge("routing", "case_builder")

    # Entry and Exit
    graph.set_entry_point("signal_receiver")
    graph.set_finish_point("case_builder")

    return graph.compile()
