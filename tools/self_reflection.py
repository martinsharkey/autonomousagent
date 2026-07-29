#!/usr/bin/env python3
"""Self-reflection tool: analyzes recent failures and extracts learning patterns."""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("data/reflection.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS failures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        tool_name TEXT,
        error_type TEXT,
        context TEXT,
        pattern TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS learnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        pattern TEXT,
        recommendation TEXT,
        applied INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

def record_failure(tool_name: str, error_type: str, context: str):
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        "INSERT INTO failures (timestamp, tool_name, error_type, context) VALUES (?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), tool_name, error_type, context)
    )
    conn.commit()
    conn.close()

def analyze_failures() -> list:
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    c.execute(
        "SELECT tool_name, error_type, context FROM failures WHERE timestamp > ?",
        (cutoff,)
    )
    rows = c.fetchall()
    conn.close()
    
    patterns = {}
    for tool, err, ctx in rows:
        key = f"{tool}:{err}"
        if key not in patterns:
            patterns[key] = {"tool": tool, "error": err, "count": 0, "contexts": []}
        patterns[key]["count"] += 1
        patterns[key]["contexts"].append(ctx)
    
    recommendations = []
    for key, data in patterns.items():
        if data["count"] >= 2:
            rec = {
                "pattern": key,
                "frequency": data["count"],
                "recommendation": f"Recurring {data['error']} in {data['tool']}: consider adding retry logic or input validation.",
                "contexts": data["contexts"][:3]
            }
            recommendations.append(rec)
    return recommendations

def store_learning(pattern: str, recommendation: str):
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        "INSERT INTO learnings (timestamp, pattern, recommendation) VALUES (?, ?, ?)",
        (datetime.utcnow().isoformat(), pattern, recommendation)
    )
    conn.commit()
    conn.close()

def get_learnings() -> list:
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT pattern, recommendation, applied FROM learnings ORDER BY timestamp DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return [{"pattern": r[0], "recommendation": r[1], "applied": bool(r[2])} for r in rows]

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: self_reflection.py <record|analyze|learnings> [args...]")
        return
    
    command = sys.argv[1]
    if command == "record":
        if len(sys.argv) < 5:
            print("Usage: self_reflection.py record <tool_name> <error_type> <context>")
            return
        record_failure(sys.argv[2], sys.argv[3], sys.argv[4])
        print(json.dumps({"status": "recorded"}))
    elif command == "analyze":
        recs = analyze_failures()
        print(json.dumps({"recommendations": recs}, indent=2))
    elif command == "learnings":
        learnings = get_learnings()
        print(json.dumps({"learnings": learnings}, indent=2))
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
