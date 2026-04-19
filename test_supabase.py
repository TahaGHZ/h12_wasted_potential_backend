import os
import json
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# Ensure .env is loaded
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Missing SUPABASE_URL or SUPABASE_KEY in .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_insert_and_fetch():
    print("Testing Supabase connectivity...")
    
    # Check cases table by attempting to fetch
    try:
        res = supabase.table("cases").select("*").limit(1).execute()
        print("[SUCCESS] Table 'cases' exists. Content snippet:", res.data)
    except Exception as e:
        print("[FAIL] Error fetching 'cases':", e)

    # Check signals table
    try:
        res = supabase.table("signals").select("*").limit(1).execute()
        print("[SUCCESS] Table 'signals' exists. Content snippet:", res.data)
    except Exception as e:
        print("[FAIL] Error fetching 'signals':", e)

    print("\nReminder: To create the tables, go to your Supabase Dashboard -> SQL Editor and run the queries inside 'supabase_schema.sql'")

if __name__ == "__main__":
    test_insert_and_fetch()
