import os
from dotenv import load_dotenv
from supabase import create_client, Client

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    print("Creating bucket 'reports'...")
    supabase.storage.create_bucket("reports", options={"public": True})
    print("Bucket created.")
except Exception as e:
    print("Bucket might exist:", e)

# Test upload
with open("test.txt", "w") as f:
    f.write("test")

with open("test.txt", "rb") as f:
    res = supabase.storage.from_("reports").upload("test.txt", f)
    print("Upload result:", res)

public_url = supabase.storage.from_("reports").get_public_url("test.txt")
print("Public URL:", public_url)
