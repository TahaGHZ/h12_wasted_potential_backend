from .graph import build_graph

class CasePipelineOrchestrator:

    def __init__(self):
        self.graph = build_graph()


    def run(self, input_data: dict):
        """
        TODO:
        - validate input
        - call graph
        """
        return self.graph.invoke({
            "signal": input_data,
            "enriched": {},
            "result": None
        })
