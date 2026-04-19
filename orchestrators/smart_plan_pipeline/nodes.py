from backend.agents.smart_plan.agent import SmartPlanAgent
from backend.agents.smart_plan.contracts import SmartPlanInput
from backend.config.storage import StorageService
from backend.contracts.cases import Case

def smart_plan_node(state):
    case = Case(**state["signal"])
    output = SmartPlanAgent().run(
        SmartPlanInput(
            case_id=case.case_id,
            case=case
        )
    )

    storage = StorageService()
    plan_path = storage.save_plan(case.case_id, output.model_dump())
    return {"result": {"plan_path": plan_path, "plan": output.model_dump()}}
