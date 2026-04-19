import os
import glob
import sys

# Add root directory to sys.path so we can import backend packages
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config.storage import StorageService, DATA_DIR

def clear_data():
    print(f"Initializing Storage Service...")
    s = StorageService()

    # 1. Clear Supabase Data
    if s.supabase:
        print("Clearing Supabase tables (plans, briefs, cases, signals)...")
        try:
            # Supabase delete requires a filter, we use .neq on primary keys with a dummy value
            s.supabase.table("plans").delete().neq("case_id", "dummy_clear_all").execute()
            print(" - Cleared 'plans' table")
            
            s.supabase.table("briefs").delete().neq("case_id", "dummy_clear_all").execute()
            print(" - Cleared 'briefs' table")
            
            s.supabase.table("cases").delete().neq("case_id", "dummy_clear_all").execute()
            print(" - Cleared 'cases' table")
            
            s.supabase.table("signals").delete().neq("signal_id", "dummy_clear_all").execute()
            print(" - Cleared 'signals' table")
            
            print("Supabase wipe complete.")
        except Exception as e:
            print(f"Error clearing Supabase tables: {e}")
    else:
        print("Supabase is not configured or unreachable via StorageService. Skipping Supabase wipe.")

    # 2. Clear Local JSON Data
    print(f"\nClearing local JSON files in {DATA_DIR}...")
    if os.path.exists(DATA_DIR):
        json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
        count = 0
        for f in json_files:
            try:
                os.remove(f)
                count += 1
            except Exception as e:
                print(f"Failed to delete {f}: {e}")
        print(f"Deleted {count} local JSON files.")
    else:
        print(f"Directory {DATA_DIR} does not exist. Nothing to clear locally.")

    print("\nAll data clearance complete!")

if __name__ == "__main__":
    confirm = input("⚠️ WARNING: This will delete ALL data in Supabase and your local data folder. Type 'YES' to confirm: ")
    if confirm == 'YES':
        clear_data()
    else:
        print("Aborted.")
