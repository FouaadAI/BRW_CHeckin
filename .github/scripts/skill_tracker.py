#!/usr/bin/env python3
"""
Skill Usage Tracker

Tracks which skills are loaded/used per session, with context metadata.
Stores data in SQLite for ranking and optimization.
"""
import sqlite3
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / ".." / "skill_usage.db"
DB_PATH = DB_PATH.resolve()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            skill_name TEXT NOT NULL,
            context TEXT,
            file_type TEXT,
            triggered_by TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            success_score REAL DEFAULT 1.0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS skill_scores (
            skill_name TEXT PRIMARY KEY,
            total_uses INTEGER DEFAULT 0,
            last_used TEXT,
            avg_success REAL DEFAULT 1.0,
            score REAL DEFAULT 0.0,
            tier TEXT DEFAULT 'UNRANKED'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS mcp_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            server_name TEXT NOT NULL,
            tool_called TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            duration_ms INTEGER
        )
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_usage_skill ON usage_log(skill_name);
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_usage_time ON usage_log(timestamp);
    """)
    conn.commit()
    conn.close()
    print(f"[skill_tracker] DB initialized at {DB_PATH}")


def log_skill(skill_name: str, context: str = "", file_type: str = "", triggered_by: str = "", session_id: str = "", success_score: float = 1.0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ts = datetime.now(timezone.utc).isoformat()
    c.execute("""
        INSERT INTO usage_log (session_id, skill_name, context, file_type, triggered_by, timestamp, success_score)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (session_id, skill_name, context, file_type, triggered_by, ts, success_score))
    c.execute("""
        INSERT INTO skill_scores (skill_name, total_uses, last_used, avg_success)
        VALUES (?, 1, ?, ?)
        ON CONFLICT(skill_name) DO UPDATE SET
            total_uses = total_uses + 1,
            last_used = excluded.last_used,
            avg_success = (avg_success * total_uses + excluded.avg_success) / (total_uses + 1)
    """, (skill_name, ts, success_score))
    conn.commit()
    conn.close()
    print(f"[skill_tracker] Logged: {skill_name} | context={context} | file={file_type}")


def log_mcp(server_name: str, tool_called: str = "", session_id: str = "", duration_ms: int = 0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO mcp_usage (session_id, server_name, tool_called, duration_ms)
        VALUES (?, ?, ?, ?)
    """, (session_id, server_name, tool_called, duration_ms))
    conn.commit()
    conn.close()
    print(f"[skill_tracker] MCP logged: {server_name}/{tool_called}")


def get_stats(skill_name: str = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if skill_name:
        c.execute("SELECT * FROM skill_scores WHERE skill_name = ?", (skill_name,))
        row = c.fetchone()
        conn.close()
        return row
    c.execute("SELECT skill_name, total_uses, last_used, score, tier FROM skill_scores ORDER BY score DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    return rows


def compute_scores():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Recency-weighted score: uses * (1 + days_since_last_use penalty)
    c.execute("""
        UPDATE skill_scores SET score =
            total_uses * (1.0 + avg_success) * MAX(0.1, 1.0 -
                (julianday('now') - julianday(COALESCE(last_used, '1970-01-01'))) / 30.0
            )
    """)
    conn.commit()
    # Assign tiers
    c.execute("SELECT skill_name, score FROM skill_scores ORDER BY score DESC")
    rows = c.fetchall()
    total = len(rows)
    if total == 0:
        conn.close()
        return
    tiers = []
    for i, (name, score) in enumerate(rows):
        pct = i / total
        if pct < 0.05:
            tier = "S"
        elif pct < 0.20:
            tier = "A"
        elif pct < 0.50:
            tier = "B"
        elif pct < 0.80:
            tier = "C"
        else:
            tier = "ZOMBIE"
        tiers.append((tier, name))
    c.executemany("UPDATE skill_scores SET tier = ? WHERE skill_name = ?", tiers)
    conn.commit()
    conn.close()
    print(f"[skill_tracker] Scores computed for {total} skills.")


def export_json(out_path: str = "skill_stats.json"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM skill_scores ORDER BY score DESC")
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, row)) for row in c.fetchall()]
    conn.close()
    out = Path(out_path)
    out.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    print(f"[skill_tracker] Exported to {out}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "init"
    if cmd == "init":
        init_db()
    elif cmd == "compute":
        compute_scores()
    elif cmd == "export":
        export_json(sys.argv[2] if len(sys.argv) > 2 else "skill_stats.json")
    elif cmd == "stats":
        for row in get_stats():
            print(row)
    else:
        print("Usage: skill_tracker.py [init|compute|export [path]|stats]")
