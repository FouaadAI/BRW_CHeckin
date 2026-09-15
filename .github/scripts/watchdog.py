#!/usr/bin/env python3
"""
Skill Optimizer Watchdog

Background process that monitors skill usage and refreshes the tier list
periodically. Designed to run as a lightweight daemon.

Features:
- Recomputes skill scores every 30 minutes
- Regenerates tier list
- Checks for zombie skills weekly
- Logs MCP server usage stats
- Can trigger auto-update checks

Usage:
    python watchdog.py [--interval 1800] [--check-updates]
    # Or run in background:
    python watchdog.py &
"""
import os
import sys
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone

SCRIPTS = Path(__file__).parent
REPO_ROOT = SCRIPTS.parent.parent
sys.path.insert(0, str(SCRIPTS))

from skill_tracker import compute_scores, DB_PATH

PID_FILE = REPO_ROOT / ".github" / ".skill_optimizer_watchdog.pid"
LOG_FILE = REPO_ROOT / ".github" / ".skill_optimizer_watchdog.log"


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(script_name, *args):
    cmd = [sys.executable, str(SCRIPTS / script_name), *args]
    try:
        result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def loop(interval_seconds: int = 1800, check_updates: bool = False):
    log("Watchdog started.")
    last_update_check = 0
    UPDATE_INTERVAL = 7 * 24 * 3600  # 7 days

    while True:
        try:
            log("Recomputing skill scores...")
            compute_scores()

            log("Regenerating tier list...")
            ok, out = run("skill_ranker.py", "generate")
            if not ok:
                log(f"Tier list error: {out[:200]}")

            if check_updates:
                now = time.time()
                if now - last_update_check > UPDATE_INTERVAL:
                    log("Checking for skill updates...")
                    ok, out = run("skill_updater.py")
                    log(f"Update check: {'OK' if ok else 'FAIL'}")
                    last_update_check = now

            log("Cycle complete. Sleeping...")
        except Exception as e:
            log(f"ERROR: {e}")

        time.sleep(interval_seconds)


def main():
    parser = argparse.ArgumentParser(description="Skill Optimizer Watchdog")
    parser.add_argument("--interval", type=int, default=1800, help="Seconds between cycles (default: 1800 = 30min)")
    parser.add_argument("--check-updates", action="store_true", help="Enable weekly auto-update checks")
    parser.add_argument("--stop", action="store_true", help="Stop running watchdog")
    args = parser.parse_args()

    if args.stop:
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(pid, 9)
                PID_FILE.unlink()
                log(f"Stopped watchdog PID {pid}")
            except Exception as e:
                print(f"Failed to stop: {e}")
        else:
            print("No PID file found.")
        return

    # Write PID
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    try:
        loop(args.interval, args.check_updates)
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()


if __name__ == "__main__":
    main()
