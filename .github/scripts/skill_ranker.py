#!/usr/bin/env python3
"""
Skill Ranker & Pruner

Generates a tier list of all skills based on usage tracking data.
Produces skills-tier-list.md for human review and .prune-list for automation.
"""
import sqlite3
import sys
from pathlib import Path
from skill_tracker import DB_PATH, compute_scores

REPO_ROOT = Path(__file__).parent.parent.parent
SKILLS_DIR = REPO_ROOT / ".github" / "skills"
TIER_LIST_PATH = REPO_ROOT / ".github" / "skills" / "skills-tier-list.md"
PRUNE_LIST_PATH = REPO_ROOT / ".github" / "skills" / ".prune-list"


def generate_tier_list():
    compute_scores()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT skill_name, total_uses, last_used, score, tier FROM skill_scores ORDER BY score DESC")
    rows = c.fetchall()
    conn.close()

    tiers = {"S": [], "A": [], "B": [], "C": [], "ZOMBIE": [], "UNRANKED": []}
    for name, uses, last_used, score, tier in rows:
        tiers.get(tier, tiers["UNRANKED"]).append((name, uses, last_used, round(score, 2)))

    # Also scan filesystem for skills not yet in DB
    existing_names = {r[0] for r in rows}
    for skill_dir in SKILLS_DIR.iterdir():
        if skill_dir.is_dir() and skill_dir.name not in existing_names:
            tiers["UNRANKED"].append((skill_dir.name, 0, "never", 0.0))

    lines = [
        "# Skill Tier List (Auto-Generated)",
        "",
        "> Based on usage tracking data. Re-run: `python .github/scripts/skill_ranker.py`",
        "",
        "## Legend",
        "- **S-Tier**: Top 5% most used / highest impact skills. Keep active always.",
        "- **A-Tier**: Top 20%. Strong candidates for most contexts.",
        "- **B-Tier**: Top 50%. Good, context-specific skills.",
        "- **C-Tier**: Bottom 30%. Rarely used, consider archiving.",
        "- **Zombie**: Bottom 20%. No usage in 30+ days. Safe to prune.",
        "- **Unranked**: Newly installed, not yet used.",
        "",
    ]

    for tier_name, emoji in [("S", "🌟"), ("A", "🔥"), ("B", "✅"), ("C", "⚠️"), ("ZOMBIE", "🧟"), ("UNRANKED", "❓")]:
        items = tiers.get(tier_name, [])
        lines.append(f"## {emoji} {tier_name}-Tier ({len(items)} skills)")
        if not items:
            lines.append("_None_")
        else:
            lines.append("| Skill | Uses | Last Used | Score |")
            lines.append("|-------|------|-----------|-------|")
            for name, uses, last_used, score in items:
                lines.append(f"| {name} | {uses} | {last_used or 'never'} | {score} |")
        lines.append("")

    TIER_LIST_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"[skill_ranker] Wrote {TIER_LIST_PATH}")

    # Prune list
    prune = [name for name, _, _, _ in tiers.get("ZOMBIE", [])]
    PRUNE_LIST_PATH.write_text("\n".join(prune), encoding="utf-8")
    print(f"[skill_ranker] Wrote {PRUNE_LIST_PATH} with {len(prune)} zombies")


def prune_zombies(dry_run=True):
    if not PRUNE_LIST_PATH.exists():
        print("[skill_ranker] No .prune-list found. Run generate first.")
        return
    zombies = PRUNE_LIST_PATH.read_text(encoding="utf-8").strip().splitlines()
    print(f"[skill_ranker] {'Would archive' if dry_run else 'Archiving'} {len(zombies)} zombie skills...")
    archive_dir = SKILLS_DIR / "_archive"
    archive_dir.mkdir(exist_ok=True)
    for z in zombies:
        src = SKILLS_DIR / z
        dst = archive_dir / z
        if src.exists():
            if not dry_run:
                src.rename(dst)
            print(f"  {'[dry-run]' if dry_run else ''} {z} -> _archive/")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "generate"
    if cmd == "generate":
        generate_tier_list()
    elif cmd == "prune":
        prune_zombies(dry_run="--force" not in sys.argv)
    else:
        print("Usage: skill_ranker.py [generate|prune [--force]]")
