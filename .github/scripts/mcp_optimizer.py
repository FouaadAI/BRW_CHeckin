#!/usr/bin/env python3
"""
MCP Server Optimizer

Manages mcp-config.json tiers and auto-enables/disables servers
based on active task context. Ensures no redundant servers run.
"""
import json
import sys
from pathlib import Path
from skill_tracker import DB_PATH, log_mcp
import sqlite3

REPO_ROOT = Path(__file__).parent.parent.parent
MCP_CONFIG = Path.home() / ".copilot" / "mcp-config.json"
ACTIVE_MANIFEST = REPO_ROOT / ".github" / "skills" / ".active-skills"

# Server → contexts mapping
SERVER_CONTEXTS = {
    "playwright": {"general", "web", "frontend", "e2e", "browser", "scraping", "research"},
    "web-search": {"general", "web", "research", "data", "news", "market"},
    "python-execution": {"general", "python", "backend", "ai/ml", "data", "testing"},
    "sqlite": {"general", "database", "backend", "data", "analytics"},
    "github-mcp-server": {"general", "devops", "ci/cd", "git"},
}

DEFAULT_TIER = {
    "playwright": 1,
    "web-search": 2,
    "python-execution": 1,
    "sqlite": 2,
    "github-mcp-server": 3,
}


def read_mcp_config():
    if not MCP_CONFIG.exists():
        return {"mcpServers": {}}
    try:
        return json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[mcp_optimizer] Error reading config: {e}")
        return {"mcpServers": {}}


def write_mcp_config(cfg):
    MCP_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    MCP_CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"[mcp_optimizer] Updated {MCP_CONFIG}")


def get_active_contexts():
    if not ACTIVE_MANIFEST.exists():
        return {"general"}
    content = ACTIVE_MANIFEST.read_text(encoding="utf-8")
    contexts = set()
    for line in content.splitlines():
        if line.startswith("# Contexts:"):
            contexts.update([c.strip() for c in line.replace("# Contexts:", "").split(",")])
    return contexts or {"general"}


def optimize_servers(contexts=None, dry_run=False):
    if contexts is None:
        contexts = get_active_contexts()
    cfg = read_mcp_config()
    servers = cfg.get("mcpServers", {})

    active_servers = set()
    for srv, ctx_set in SERVER_CONTEXTS.items():
        if contexts & ctx_set:
            active_servers.add(srv)

    # Always keep a fallback
    if not active_servers:
        active_servers = {"web-search", "python-execution"}

    changes = []
    for srv in servers:
        if srv in active_servers:
            if servers[srv].get("disabled"):
                changes.append((srv, "enable"))
                if not dry_run:
                    servers[srv]["disabled"] = False
        else:
            if not servers[srv].get("disabled"):
                changes.append((srv, "disable"))
                if not dry_run:
                    servers[srv]["disabled"] = True

    for srv in active_servers:
        if srv not in servers:
            print(f"[mcp_optimizer] WARN: {srv} not in config — add it first")

    if not dry_run and changes:
        write_mcp_config(cfg)
    else:
        print(f"[mcp_optimizer] {'Would change' if dry_run else 'Changed'}: {changes}")

    return active_servers


def report_server_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT server_name, COUNT(*), AVG(duration_ms)
        FROM mcp_usage
        WHERE timestamp > datetime('now', '-7 days')
        GROUP BY server_name
        ORDER BY COUNT(*) DESC
    """)
    rows = c.fetchall()
    conn.close()
    print("[mcp_optimizer] Last 7 days MCP usage:")
    for srv, cnt, avg_ms in rows:
        print(f"  {srv}: {cnt} calls, {round(avg_ms or 0, 0)}ms avg")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "optimize"
    if cmd == "optimize":
        optimize_servers(dry_run="--dry-run" in sys.argv)
    elif cmd == "report":
        report_server_stats()
    else:
        print("Usage: mcp_optimizer.py [optimize [--dry-run]|report]")
