from backend.agents.briefing.agent import BriefingAgent
from backend.agents.briefing.contracts import BriefingInput
from backend.config.storage import StorageService
from backend.contracts.cases import Case

def briefing_node(state):
    case = Case(**state["signal"])
    output = BriefingAgent().run(
        BriefingInput(
            case_id=case.case_id,
            case=case
        )
    )

    storage = StorageService()
    brief_path = storage.save_brief(case.case_id, output.model_dump())
    return {"result": {"brief_path": brief_path, "brief": output.model_dump()}}
