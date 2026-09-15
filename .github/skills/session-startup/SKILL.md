# Session Startup — Auto-Load Registry

## Description
Automatically merge both `.github` registries (base + extra) into the persistent SQLite database at session start, then display all registered agents, skills, MCP servers, plugins and models.  No duplicates — extra overrides base on name collision.

## Files
- `database.db` — persistent SQLite database (cross-session, repo root)
- `.github/scripts/merge_registries.py` — merge filesystem + YAML → DB (run automatically at startup)
- `.github/scripts/show_registry.py` — display DB contents (run automatically after merge)

## Automatic Startup Flow
When a new Copilot CLI session starts, Copilot should run:
```powershell
python "D:\brain\Documents\Ollama-Agent\Mark-XXXIX-OR\.github\scripts\merge_registries.py"
python "D:\brain\Documents\Ollama-Agent\Mark-XXXIX-OR\.github\scripts\show_registry.py"
```

## Manual (inside Copilot session)
Just ask:
```
show registry
zeige alle Ressourcen
what agents and skills are available?
```
Copilot will run `show_registry.py` and display the current state.

## Current Registry Content (merged from ALL .github directories)
- **Agents:** 43 (merged, duplicates removed)
- **Skills:** 79 (merged, duplicates removed)
- **Plugins:** 20 (awesome-copilot)
- **Models:** 19 (Ollama Cloud)
- **MCP Servers:** 5 (sqlite, playwright, python-execution, web-search, github)
- **Tools:** 54 (awesome-copilot)
