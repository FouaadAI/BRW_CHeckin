#!/usr/bin/env python3
"""
Skill Optimizer Master

One-command entry point to run the full skill optimization pipeline:
1. Init DB (if needed)
2. Compute scores
3. Generate tier list
4. Load context-aware active skills
5. Optimize MCP servers
6. Report status
"""
import sys
import subprocess
from pathlib import Path

SCRIPTS = Path(__file__).parent
REPO_ROOT = SCRIPTS.parent.parent


def run(script_name, *args):
    cmd = [sys.executable, str(SCRIPTS / script_name), *args]
    print(f"\n{'='*60}")
    print(f"Running: {script_name} {' '.join(args)}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    return result.returncode == 0


def main():
    if "--help" in sys.argv:
        print("Usage: skill_optimizer_master.py [--init|--refresh|--report|--full]")
        print("  --init    : Initialize DB only")
        print("  --refresh : Recompute scores + tier list + active manifest")
        print("  --report  : Show usage reports")
        print("  --full    : Run everything (default)")
        return

    full = "--full" in sys.argv or len(sys.argv) == 1
    init_only = "--init" in sys.argv
    refresh = "--refresh" in sys.argv
    report = "--report" in sys.argv

    if init_only:
        run("skill_tracker.py", "init")
        return

    if full or refresh:
        run("skill_tracker.py", "compute")
        run("skill_ranker.py", "generate")
        # Detect context from CWD or argv
        ctx = sys.argv[-1] if sys.argv[-1].startswith(".") or "/" in sys.argv[-1] else "."
        run("context_loader.py", ctx, "15")
        run("mcp_optimizer.py", "optimize")

    if full or report:
        run("mcp_optimizer.py", "report")
        run("skill_tracker.py", "stats")

    print("\n" + "="*60)
    print("Skill Optimizer complete.")
    print("="*60)


if __name__ == "__main__":
    main()
