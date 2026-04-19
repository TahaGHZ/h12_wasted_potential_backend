import os
import json
import logging
from datetime import datetime
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from backend.contracts.signals import RawSignal, EnrichedSignal
from backend.contracts.cases import Case

# Ensure .env is loaded
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=env_path)

# Move data folder to root to avoid uvicorn reload loop
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class StorageService:
    def __init__(self):
        self.logger = logging.getLogger("signal_pipeline")
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            
        self.supabase: Optional[Client] = None
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                self.logger.info("Supabase client initialized successfully")
            except Exception as e:
                self.logger.error("Failed to initialize Supabase client: %s", e)

    def save_signal(self, raw_signal: RawSignal, enriched_signal: EnrichedSignal):
        """
        Saves the processed signal to a local JSON file to simulate DB persistence.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"signal_{raw_signal.signal_id}_{timestamp}.json"
        filepath = os.path.join(DATA_DIR, filename)

        data = {
            "version": "1.0",
            "saved_at": datetime.now().isoformat(),
            "raw_payload": raw_signal.model_dump(),
            "enriched_payload": enriched_signal.model_dump()
        }

        # Local save (Disabled)
        # with open(filepath, "w", encoding="utf-8") as f:
        #     json.dump(data, f, indent=4, ensure_ascii=False)
            
        # Supabase save
        if self.supabase:
            try:
                # Prepare record according to what Supabase table might expect
                # Assuming table 'signals' exists
                record = {
                    "signal_id": raw_signal.signal_id,
                    "created_at": data["saved_at"],
                    "raw_payload": data["raw_payload"],
                    "enriched_payload": data["enriched_payload"]
                }
                self.supabase.table("signals").upsert(record).execute()
            except Exception as e:
                self.logger.error(f"Failed to save signal {raw_signal.signal_id} to Supabase: {e}")

        return filepath

    def save_case(self, case: Case) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"case_{case.case_id}_{timestamp}.json"
        filepath = os.path.join(DATA_DIR, filename)

        data = {
            "version": "1.0",
            "saved_at": datetime.now().isoformat(),
            "case_payload": case.model_dump()
        }

        # Local storage (Disabled)
        # with open(filepath, "w", encoding="utf-8") as f:
        #     json.dump(data, f, indent=4, ensure_ascii=False)

        # Supabase storage
        if self.supabase:
            try:
                c = data["case_payload"]
                record = {
                    "case_id": c.get("case_id"),
                    "title": c.get("title"),
                    "description": c.get("description"),
                    "assigned_to": c.get("assigned_to"),
                    "status": c.get("status"),
                    "priority_score": c.get("priority_score"),
                    "domain": c.get("domain"),
                    "event_type": c.get("event_type"),
                    "location": c.get("location"),
                    "embedding": c.get("embedding"),
                    "embedding_count": c.get("embedding_count", 0),
                    "signals_count": len(c.get("signals", [])),
                    "payload": c
                }
                self.supabase.table("cases").upsert(record).execute()
            except Exception as e:
                self.logger.error(f"Failed to save case {case.case_id} to Supabase: {e}")

        return filepath

    def save_brief(self, case_id: str, brief_payload: dict) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"brief_{case_id}_{timestamp}.json"
        filepath = os.path.join(DATA_DIR, filename)

        data = {
            "version": "1.0",
            "saved_at": datetime.now().isoformat(),
            "brief_payload": brief_payload
        }

        # Local storage (Disabled)
        # with open(filepath, "w", encoding="utf-8") as f:
        #     json.dump(data, f, indent=4, ensure_ascii=False)

        if self.supabase:
            try:
                record = {
                    "case_id": case_id,
                    "title": brief_payload.get("title"),
                    "summary": brief_payload.get("summary"),
                    "priority_score": brief_payload.get("priority_score"),
                    "payload": brief_payload
                }
                self.supabase.table("briefs").upsert(record).execute()
            except Exception as e:
                self.logger.error(f"Failed to save brief for {case_id} to Supabase: {e}")

        return filepath

    def save_plan(self, case_id: str, plan_payload: dict) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"plan_{case_id}_{timestamp}.json"
        filepath = os.path.join(DATA_DIR, filename)

        data = {
            "version": "1.0",
            "saved_at": datetime.now().isoformat(),
            "plan_payload": plan_payload
        }

        # Local storage (Disabled)
        # with open(filepath, "w", encoding="utf-8") as f:
        #     json.dump(data, f, indent=4, ensure_ascii=False)

        if self.supabase:
            try:
                record = {
                    "case_id": case_id,
                    "plan_id": plan_payload.get("plan_id"),
                    "title": plan_payload.get("title"),
                    "confidence": plan_payload.get("confidence"),
                    "payload": plan_payload
                }
                self.supabase.table("plans").upsert(record).execute()
            except Exception as e:
                self.logger.error(f"Failed to save plan for {case_id} to Supabase: {e}")

        return filepath

    def _use_supabase_read(self) -> bool:
        # Returns True if Supabase is connected AND local JSON fallback is not explicitly enforced
        return self.supabase is not None and os.getenv("USE_LOCAL_JSON", "false").lower() not in ("true", "1", "yes")

    def list_signals(self) -> list[dict]:
        if self._use_supabase_read():
            try:
                response = self.supabase.table("signals").select("*").execute()
                return [{
                    "saved_at": record.get("created_at", ""),
                    "raw_payload": record.get("raw_payload", {}),
                    "enriched_payload": record.get("enriched_payload", {})
                } for record in response.data]
            except Exception as e:
                self.logger.error(f"Failed to read signals from Supabase: {e}")
                # Fallback to local if Supabase query fails
        return self._list_payloads("signal_", "raw_payload", "enriched_payload")

    def list_cases(self) -> list[dict]:
        if self._use_supabase_read():
            try:
                response = self.supabase.table("cases").select("*").execute()
                return [{
                    "saved_at": record.get("created_at", ""),
                    "case_payload": record.get("payload", {})
                } for record in response.data]
            except Exception as e:
                self.logger.error(f"Failed to read cases from Supabase: {e}")
        return self._list_payloads("case_", "case_payload")

    def list_briefs(self) -> list[dict]:
        if self._use_supabase_read():
            try:
                response = self.supabase.table("briefs").select("*").execute()
                return [{
                    "saved_at": record.get("created_at", ""),
                    "brief_payload": record.get("payload", {})
                } for record in response.data]
            except Exception as e:
                self.logger.error(f"Failed to read briefs from Supabase: {e}")
        return self._list_payloads("brief_", "brief_payload")

    def list_plans(self) -> list[dict]:
        if self._use_supabase_read():
            try:
                response = self.supabase.table("plans").select("*").execute()
                return [{
                    "saved_at": record.get("created_at", ""),
                    "plan_payload": record.get("payload", {})
                } for record in response.data]
            except Exception as e:
                self.logger.error(f"Failed to read plans from Supabase: {e}")
        return self._list_payloads("plan_", "plan_payload")

    def get_latest_case(self, case_id: str) -> Optional[dict]:
        cases = [case for case in self.list_cases() if case.get("case_payload", {}).get("case_id") == case_id]
        if not cases:
            return None
        return max(cases, key=lambda item: item.get("saved_at", ""))

    def _list_payloads(self, prefix: str, *payload_keys: str) -> list[dict]:
        if not os.path.exists(DATA_DIR):
            return []

        results = []
        for filename in os.listdir(DATA_DIR):
            if not filename.startswith(prefix) or not filename.endswith(".json"):
                continue

            filepath = os.path.join(DATA_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as exc:
                self.logger.exception("Failed to read storage file %s: %s", filepath, exc)
                continue

            if not any(key in data for key in payload_keys):
                continue
            results.append(data)

        return results

    def save_llm_log(self, signal_id: str, agent_name: str, prompt: str, output: str):
        """
        Optional debugging storage for LLM outputs.
        """
        filename = f"llm_log_{signal_id}_{agent_name}.json"
        filepath = os.path.join(DATA_DIR, filename)
        
        data = {
            "signal_id": signal_id,
            "agent": agent_name,
            "prompt": prompt,
            "output": output
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        return filepath
