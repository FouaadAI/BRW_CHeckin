#!/usr/bin/env python3
"""
Auto Optimize — Session/Task Start Wrapper

Runs automatically at the beginning of every task/session to:
1. Detect task context from CWD + files + user intent
2. Load top-N relevant skills via context_loader
3. Optimize MCP servers via mcp_optimizer
4. Seed the tracker with expected skills for this session
5. Write a session-ready manifest

Usage:
    python .github/scripts/auto_optimize.py "<intent>" [top_n]
    python .github/scripts/auto_optimize.py --auto-detect
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

SCRIPTS = Path(__file__).parent
REPO_ROOT = SCRIPTS.parent.parent
sys.path.insert(0, str(SCRIPTS))

from skill_tracker import log_skill, log_mcp, DB_PATH
from context_loader import detect_contexts, get_ranked_skills, write_active_manifest
from mcp_optimizer import optimize_servers, read_mcp_config

SESSION_ID = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def detect_files_from_cwd():
    """Scan current working directory for file types to infer context."""
    cwd = Path.cwd()
    files = []
    exts = set()
    for p in cwd.rglob("*"):
        if p.is_file() and len(p.relative_to(cwd).parts) <= 3:
            files.append(str(p.relative_to(cwd)))
            exts.add(p.suffix.lower())
            if len(files) >= 20:
                break
    return files, exts


def guess_intent_from_argv():
    """Try to read user intent from recent shell history or environment."""
    intent = os.environ.get("COPILOT_TASK_INTENT", "")
    if not intent:
        # Try to read from a temp file written by hook
        intent_file = REPO_ROOT / ".github" / ".last_intent"
        if intent_file.exists():
            intent = intent_file.read_text(encoding="utf-8").strip()
    return intent


def run_optimizer(intent: str = "", top_n: int = 15):
    files, exts = detect_files_from_cwd()
    contexts = detect_contexts(files, intent)
    print(f"[auto_optimize] Session={SESSION_ID} | Contexts={contexts}")

    # 1. Load ranked skills
    skills = get_ranked_skills(contexts, top_n)
    write_active_manifest(skills, contexts)

    # 2. Seed tracker for expected skills
    for s in skills:
        log_skill(
            skill_name=s["name"],
            context=",".join(contexts),
            file_type=",".join(exts) or "general",
            triggered_by="auto_optimize",
            session_id=SESSION_ID,
            success_score=0.5,  # neutral until proven
        )

    # 3. Optimize MCP servers
    active_servers = optimize_servers(set(contexts), dry_run=False)
    for srv in active_servers:
        log_mcp(server_name=srv, tool_called="activate", session_id=SESSION_ID)

    # 4. Write session state
    state = {
        "session_id": SESSION_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "contexts": contexts,
        "active_skills": [s["name"] for s in skills],
        "active_mcp_servers": list(active_servers),
        "cwd": str(Path.cwd()),
    }
    state_file = REPO_ROOT / ".github" / ".session_state.json"
    state_file.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")

    print(f"[auto_optimize] Active skills: {len(skills)} | MCP servers: {len(active_servers)}")
    print(f"[auto_optimize] Manifest: .github/skills/.active-skills")
    print(f"[auto_optimize] State: .github/.session_state.json")
    return state


def finalize_session(success: bool = True):
    """Call at session end to update success scores and refresh tier list."""
    print("[auto_optimize] Finalizing session...")
    # Update success scores for logged skills
    from skill_tracker import compute_scores
    compute_scores()
    # Regenerate tier list
    subprocess.run([sys.executable, str(SCRIPTS / "skill_ranker.py"), "generate"], cwd=REPO_ROOT)
    print("[auto_optimize] Session finalized. Tier list refreshed.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--finalize":
        finalize_session()
        sys.exit(0)

    intent = sys.argv[1] if len(sys.argv) > 1 else guess_intent_from_argv()
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    run_optimizer(intent, top_n)
