#!/usr/bin/env python3
"""
Context-Aware Skill Loader

Given a task context (file types, intent keywords), returns the top-N most
relevant skills based on the tier list + keyword matching.
Prevents context bloat by capping active skills.
"""
import sqlite3
import sys
import re
from pathlib import Path
from skill_tracker import DB_PATH

REPO_ROOT = Path(__file__).parent.parent.parent
SKILLS_DIR = REPO_ROOT / ".github" / "skills"
ACTIVE_MANIFEST = REPO_ROOT / ".github" / "skills" / ".active-skills"
TIER_LIST = REPO_ROOT / ".github" / "skills" / "skills-tier-list.md"

# Context → keyword mappings
CONTEXT_KEYWORDS = {
    "python": ["python", "py", "django", "flask", "fastapi", "pytest", "mypy", "pandas", "numpy"],
    "typescript": ["typescript", "ts", "tsx", "node", "react", "nextjs", "vue", "angular"],
    "csharp": ["csharp", "cs", "dotnet", ".net", "unity", "blazor"],
    "security": ["auth", "jwt", "oauth", "password", "encrypt", "xss", "sql-injection", "secret"],
    "database": ["sql", "postgres", "sqlite", "mysql", "mongodb", "prisma", "orm", "clickhouse", "redis"],
    "devops": ["docker", "kubernetes", "k8s", "ci/cd", "github-actions", "terraform", "helm"],
    "testing": ["test", "jest", "pytest", "cypress", "playwright", "unit-test", "e2e"],
    "frontend": ["css", "html", "scss", "tailwind", "ui", "component", "layout", "responsive"],
    "backend": ["api", "rest", "graphql", "server", "microservice", "express", "fastapi"],
    "ai/ml": ["llm", "gpt", "openai", "ollama", "model", "embeddings", "vector", "ml", "tensorflow", "pytorch"],
    "trading": ["k1ng", "macro", "xtiusd", "xauusd", "ctrader", "signal", "grid", "trading", "bot"],
    "infrastructure": ["aws", "gcp", "azure", "cloud", "serverless", "lambda", "s3"],
}


def detect_contexts(file_paths: list[str], intent: str = "") -> list[str]:
    text = " ".join(file_paths).lower() + " " + intent.lower()
    contexts = []
    for ctx, keywords in CONTEXT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            contexts.append(ctx)
    return contexts or ["general"]


def load_skill_metadata(skill_name: str) -> dict:
    skill_md = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_md.exists():
        return {"name": skill_name, "tags": [], "description": ""}
    content = skill_md.read_text(encoding="utf-8", errors="ignore")
    # Parse frontmatter
    meta = {"name": skill_name, "tags": [], "description": ""}
    if content.startswith("---"):
        try:
            fm = content.split("---", 2)[1]
            for line in fm.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip().strip('"').strip("'")
                    if k in ("name", "description"):
                        meta[k] = v
                    elif k == "tags":
                        meta["tags"] = [t.strip().strip('"').strip("'") for t in v.strip("[]").split(",")]
        except Exception:
            pass
    # Also grab first H1 as description if missing
    if not meta["description"]:
        m = re.search(r"^# (.+)$", content, re.MULTILINE)
        if m:
            meta["description"] = m.group(1)
    return meta


def get_ranked_skills(contexts: list[str], top_n: int = 15) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT skill_name, score, tier FROM skill_scores ORDER BY score DESC")
    scored = {name: {"score": score, "tier": tier} for name, score, tier in c.fetchall()}
    conn.close()

    results = []
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith("_") or skill_dir.name.startswith("."):
            continue
        meta = load_skill_metadata(skill_dir.name)
        score_data = scored.get(skill_dir.name, {"score": 0.0, "tier": "UNRANKED"})
        meta["score"] = score_data["score"]
        meta["tier"] = score_data["tier"]

        # Context relevance boost
        relevance = 0
        text = (meta["name"] + " " + meta["description"] + " " + " ".join(meta.get("tags", []))).lower()
        for ctx in contexts:
            kws = CONTEXT_KEYWORDS.get(ctx, [])
            hits = sum(1 for kw in kws if kw in text)
            relevance += hits * 2  # boost per hit

        # Tier boost
        tier_boost = {"S": 50, "A": 30, "B": 15, "C": 5, "ZOMBIE": -100, "UNRANKED": 0}
        final_score = meta["score"] + relevance + tier_boost.get(meta["tier"], 0)
        meta["final_score"] = final_score
        meta["relevance"] = relevance
        results.append(meta)

    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results[:top_n]


def write_active_manifest(skills: list[dict], contexts: list[str]):
    lines = [
        "# Active Skills Manifest",
        f"# Contexts: {', '.join(contexts)}",
        f"# Generated: {__import__('datetime').datetime.now().isoformat()}",
        "",
    ]
    for s in skills:
        lines.append(f"- [{s['tier']}] {s['name']} (score={s['final_score']}, rel={s['relevance']}) # {s['description']}")
    ACTIVE_MANIFEST.write_text("\n".join(lines), encoding="utf-8")
    print(f"[context_loader] Wrote {ACTIVE_MANIFEST} with {len(skills)} skills")


def main():
    if len(sys.argv) < 2:
        print("Usage: context_loader.py <file1,file2,...|intent-string> [top_n]")
        print("Example: context_loader.py 'src/auth.py,tests/test_auth.py' 10")
        sys.exit(1)

    raw = sys.argv[1]
    if "." in raw and "/" in raw:
        files = [p.strip() for p in raw.split(",")]
        intent = ""
    else:
        files = []
        intent = raw

    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    contexts = detect_contexts(files, intent)
    print(f"[context_loader] Detected contexts: {contexts}")
    skills = get_ranked_skills(contexts, top_n)
    write_active_manifest(skills, contexts)
    for s in skills:
        print(f"  [{s['tier']}] {s['name']} -> score={s['final_score']}")


if __name__ == "__main__":
    main()
