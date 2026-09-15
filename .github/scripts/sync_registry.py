#!/usr/bin/env python3
"""
Sync copilot-registry.yml into a persistent SQLite database.
Run this after registry changes to keep the DB up to date.
"""
import sqlite3
import json
import yaml
from pathlib import Path
from datetime import datetime

# --- Configuration ---
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_YML = REPO_ROOT / ".github" / "copilot-registry.yml"
DB_PATH = REPO_ROOT / "database.db"


def read_registry():
    if not REGISTRY_YML.exists():
        raise FileNotFoundError(f"Registry not found: {REGISTRY_YML}")
    with open(REGISTRY_YML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        path TEXT,
        description TEXT,
        tags TEXT,
        source TEXT,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        path TEXT,
        description TEXT,
        tags TEXT,
        source TEXT,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS external_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT,
        source TEXT,
        url TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS registry_meta (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)
    conn.commit()
    return conn


def to_json(val):
    if val is None:
        return ""
    if isinstance(val, list):
        return json.dumps(val, ensure_ascii=False)
    return str(val)


def sync_table(conn, table, items):
    c = conn.cursor()
    c.execute(f"DELETE FROM {table}")
    for item in (items or []):
        keys = ["name", "path", "description", "tags", "source"]
        vals = [
            item.get("name", ""),
            item.get("path", ""),
            item.get("description", ""),
            to_json(item.get("tags")),
            item.get("source", "local"),
        ]
        cols = ", ".join(keys)
        placeholders = ", ".join(["?"] * len(keys))
        c.execute(f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})", vals)
    conn.commit()


def sync_external(conn, items, type_name):
    c = conn.cursor()
    for item in (items or []):
        url = item.get("path", "")
        if type_name == "mcp_server":
            url = item.get("path", item.get("url", ""))
        elif type_name == "model":
            url = item.get("provider", "")
        c.execute(
            "INSERT INTO external_registry (name, type, source, url, description) VALUES (?, ?, ?, ?, ?)",
            (item.get("name"), type_name, item.get("source", "local"), url, item.get("description", "")),
        )
    conn.commit()


def main():
    print(f"[sync_registry] Reading {REGISTRY_YML}")
    data = read_registry()

    raw_tools = data.get("tools") or []
    # Some entries under 'tools' are actually agents (paths contain 'agents')
    tools = [t for t in raw_tools if "agents" not in (t.get("path") or "")]
    agent_tools = [t for t in raw_tools if "agents" in (t.get("path") or "")]

    # Merge misclassified agents into agents list
    agents = (data.get("agents") or []) + agent_tools

    counts = {
        "agents": len(agents),
        "skills": len(data.get("skills") or []),
        "plugins": len(data.get("plugins") or []),
        "models": len(data.get("models") or []),
        "mcp_servers": len(data.get("mcp_servers") or []),
        "tools": len(tools),
    }
    print(f"[sync_registry] Found {counts['agents']} agents, {counts['skills']} skills, "
          f"{counts['plugins']} plugins, {counts['models']} models, "
          f"{counts['mcp_servers']} mcp_servers, {counts['tools']} tools")

    conn = init_db()
    # Clear external_registry first
    c = conn.cursor()
    c.execute("DELETE FROM external_registry")
    conn.commit()

    sync_table(conn, "agents", agents)
    sync_table(conn, "skills", data.get("skills"))
    sync_external(conn, data.get("plugins"), "plugin")
    sync_external(conn, data.get("mcp_servers"), "mcp_server")
    sync_external(conn, data.get("models"), "model")
    sync_external(conn, tools, "tool")

    # Update meta
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO registry_meta (key, value) VALUES (?, ?)",
              ("last_sync", datetime.now().isoformat()))
    c.execute("INSERT OR REPLACE INTO registry_meta (key, value) VALUES (?, ?)",
              ("version", data.get("meta", {}).get("version", "unknown")))
    conn.commit()
    conn.close()
    print(f"[sync_registry] Saved to {DB_PATH}")
    print("[sync_registry] Done.")


if __name__ == "__main__":
    main()
