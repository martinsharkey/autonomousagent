import sqlite3
import json
from pathlib import Path

# Check evolution DB
db_path = Path("autonomous_loops/evolution.db")
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    print("=== Evolution Database Tables ===")
    for t in tables:
        print(f"  {t[0]}")

    # Check mutations table
    for t in tables:
        if "mutation" in t[0].lower():
            c.execute(f"PRAGMA table_info([{t[0]}])")
            cols = c.fetchall()
            print(f"\n  Schema for {t[0]}:")
            for col in cols:
                print(f"    {col}")
            c.execute(f"SELECT COUNT(*) FROM [{t[0]}]")
            count = c.fetchone()[0]
            print(f"    Total rows: {count}")

            # Show all mutations
            c.execute(f"SELECT * FROM [{t[0]}] ORDER BY id DESC LIMIT 15")
            rows = c.fetchall()
            print(f"\n  Latest mutations:")
            for row in rows:
                print(f"    {row}")
    conn.close()
else:
    print(f"DB not found at {db_path}")
    # Check for other DB files
    for f in Path(".").glob("**/*.db"):
        print(f"  Found: {f}")

# Also check the audit log DB
audit_db = Path("audit_logs/audit.db")
if audit_db.exists():
    conn = sqlite3.connect(str(audit_db))
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    print(f"\n=== Audit Log DB Tables ===")
    for t in tables:
        print(f"  {t[0]}")
    conn.close()

# Read evolution.py Mutation class and voting
print("\n=== Evolution Engine Summary ===")
evo_file = Path("core/evolution.py")
if evo_file.exists():
    content = evo_file.read_text()
    # Find propose_mutation function
    idx = content.find("def propose_mutation")
    if idx >= 0:
        print(content[idx:idx+500])
