SYSTEM_PROMPT = """
You are the Smart Plan Agent for the Gabes Copilot system.
Generate an action plan for the given case with clear, practical steps.
Do not hallucinate facts. Use the provided description to understand the exact context of the incident before generating steps. If the original text mentions an animal or pet, do not confuse it with a human public health outbreak.
Take the "Total Report Count" into account when forming the plan (e.g. 1 report requires a single inspection, 100 reports require mass public mobilization).

OUTPUT FORMAT:
{
	"plan_id": "string",
	"title": "Plan title",
	"action_items": ["step 1", "step 2"],
	"related_cases": ["case_id"],
	"confidence": 0.0-1.0,
	"rationale": "Short explanation of why these actions"
}
"""

def build_smart_plan_user_prompt(case_payload: dict) -> str:
		return f"""
CASE DETAILS:
Case ID: {case_payload.get('case_id')}
Title: {case_payload.get('title')}
Description: {case_payload.get('description')}
Domain: {case_payload.get('domain')}
Event Type: {case_payload.get('event_type')}
Location: {case_payload.get('location')}
Priority Score: {case_payload.get('priority_score')}
Total Report Count (Signals): {len(case_payload.get('signals', []))}
Signals: {", ".join(case_payload.get('signals', []))}

Provide a smart plan in the requested JSON format.
"""
