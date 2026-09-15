#!/usr/bin/env python3
"""
Skill Auto-Updater

Checks the antigravity-awesome-skills repo for new/updated skills.
Compares against local install. Highlights must-have additions.
"""
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).parent.parent.parent
LOCAL_SKILLS = REPO_ROOT / ".github" / "skills"
REMOTE_URL = "https://api.github.com/repos/sickn33/antigravity-awesome-skills/releases/latest"
CLONE_DIR = REPO_ROOT / ".github" / ".remote-skills-cache"
MUST_HAVE_TAGS = {"security", "python", "testing", "mcp", "devops", "ai", "backend", "frontend"}


def fetch_remote_release():
    try:
        import urllib.request
        req = urllib.request.Request(REMOTE_URL, headers={"Accept": "application/vnd.github.v3+json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return data.get("tag_name"), data.get("published_at"), data.get("body", "")
    except Exception as e:
        print(f"[skill_updater] API error: {e}")
        return None, None, ""


def clone_or_update_remote():
    if CLONE_DIR.exists():
        subprocess.run(["git", "-C", str(CLONE_DIR), "pull", "--depth", "1"], capture_output=True)
    else:
        subprocess.run(
            ["git", "clone", "--depth", "1", "https://github.com/sickn33/antigravity-awesome-skills.git", str(CLONE_DIR)],
            capture_output=True,
        )
    remote_skills = CLONE_DIR / "skills"
    return remote_skills if remote_skills.exists() else None


def scan_skill_metadata(skills_dir: Path):
    meta = {}
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        tags = []
        desc = ""
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8", errors="ignore")
            if content.startswith("---"):
                try:
                    fm = content.split("---", 2)[1]
                    for line in fm.splitlines():
                        if line.strip().lower().startswith("tags:"):
                            tag_str = line.split(":", 1)[1].strip().strip("[]")
                            tags = [t.strip().strip('"').strip("'") for t in tag_str.split(",")]
                        if line.strip().lower().startswith("description:"):
                            desc = line.split(":", 1)[1].strip().strip('"').strip("'")
                except Exception:
                    pass
        meta[skill_dir.name] = {"tags": tags, "description": desc, "mtime": skill_dir.stat().st_mtime}
    return meta


def compare_and_report(dry_run=True):
    tag_name, published, release_body = fetch_remote_release()
    print(f"[skill_updater] Remote release: {tag_name} ({published})")

    remote_skills_dir = clone_or_update_remote()
    if not remote_skills_dir:
        print("[skill_updater] Failed to fetch remote skills.")
        return

    local_meta = scan_skill_metadata(LOCAL_SKILLS)
    remote_meta = scan_skill_metadata(remote_skills_dir)

    local_names = set(local_meta.keys())
    remote_names = set(remote_meta.keys())

    new_skills = remote_names - local_names
    removed_skills = local_names - remote_names
    existing = local_names & remote_names
    updated = []
    for name in existing:
        if remote_meta[name]["mtime"] > local_meta[name]["mtime"]:
            updated.append(name)

    must_have = []
    for name in new_skills:
        if any(t in MUST_HAVE_TAGS for t in remote_meta[name]["tags"]):
            must_have.append(name)

    print(f"\n[skill_updater] Report ({datetime.now(timezone.utc).isoformat()})")
    print(f"  New skills:      {len(new_skills)}")
    print(f"  Must-have:       {len(must_have)}")
    print(f"  Updated skills:  {len(updated)}")
    print(f"  Removed skills:  {len(removed_skills)}")

    if must_have:
        print(f"\n  ⭐ Must-have new skills:")
        for name in must_have:
            print(f"    - {name}: {remote_meta[name]['description']}")

    if not dry_run:
        print("\n[skill_updater] Applying updates...")
        for name in new_skills:
            src = remote_skills_dir / name
            dst = LOCAL_SKILLS / name
            if not dst.exists():
                import shutil
                shutil.copytree(src, dst)
                print(f"  + {name}")
        for name in updated:
            src = remote_skills_dir / name
            dst = LOCAL_SKILLS / name
            if dst.exists():
                import shutil
                shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"  ~ {name}")
        if removed_skills:
            archive = LOCAL_SKILLS / "_archive"
            archive.mkdir(exist_ok=True)
            for name in removed_skills:
                src = LOCAL_SKILLS / name
                dst = archive / name
                if src.exists():
                    src.rename(dst)
                    print(f"  - {name} (archived)")

    # Write report
    report_path = REPO_ROOT / ".github" / "skills" / ".update-report.md"
    lines = [
        "# Skill Update Report",
        f"- Remote: {tag_name} ({published})",
        f"- Checked: {datetime.now(timezone.utc).isoformat()}",
        f"- New: {len(new_skills)} | Updated: {len(updated)} | Removed: {len(removed_skills)} | Must-Have: {len(must_have)}",
        "",
        "## Must-Have New Skills",
    ]
    for name in must_have:
        lines.append(f"- **{name}**: {remote_meta[name]['description']} (tags: {', '.join(remote_meta[name]['tags'])})")
    lines.append("")
    lines.append("## All New Skills")
    for name in sorted(new_skills):
        lines.append(f"- {name}: {remote_meta[name]['description']}")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[skill_updater] Report written to {report_path}")


if __name__ == "__main__":
    dry = "--apply" not in sys.argv
    if dry:
        print("[skill_updater] DRY RUN mode. Use --apply to install changes.\n")
    compare_and_report(dry_run=dry)
