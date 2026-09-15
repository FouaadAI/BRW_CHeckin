# BRW Check-in — Copilot Instructions

Project language/domain: German (Berlin U-Bahn station check-ins). UI labels, sheet names, and Telegram messages are in German.

## Project Overview

Serverless time-tracking/check-in web application for Berlin subway stations. A GitHub Pages frontend collects a PIN, employee name, station, and shift; a GitHub Actions workflow validates the PIN and records 7.0 working hours per shift in Google Sheets, then sends a Telegram notification. A monthly cron workflow exports the previous month's sheets as a single multi-tab Excel file and sends it via Telegram.

The canonical architecture description is in `ARCHITEKTUR-PLAN & PROMPT.md` at the repository root.

## Repository Layout

- Root files: the actual BRW Check-in application.
  - `ARCHITEKTUR-PLAN & PROMPT.md` — full architecture and prompt used to generate the app.
  - `Station_json_generator.py` — utility that fetches Berlin U-Bahn stations from OpenStreetMap/Overpass and writes `stations.json`.
  - `stations.json` — generated list of stations with `name`, `lat`, `lng`.
  - `service_account.json` — Google service-account credentials. Must stay local/uncommitted; load from `GOOGLE_SERVICE_ACCOUNT_JSON` GitHub Secret in workflows.
- `.github/instructions/` — project-wide rules for coding style, patterns, testing, security, git workflow, and agent usage. These apply automatically to matching file types.
- `.github/agents/` and `.github/skills/` — shared agent/skill library. Most files under `.github/skills/` are reference implementations for unrelated technologies; do not treat them as project code.

## Architecture

1. **Data layer**
   - `stations.json`: public station master data (name + GPS coordinates).
   - `employees.json`: public list of 13 allowed employees (not yet present at root; create when implementing the frontend).
   - GitHub Secrets: `APP_PIN`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GH_PAT` (or equivalent token for repository dispatch).

2. **Frontend (GitHub Pages)**
   - `index.html` + `app.js` (not yet present).
   - Screen 1: PIN gatekeeper. Blocks access until the correct `APP_PIN` is entered.
   - Screen 2: check-in form with searchable dropdowns for employee and station, plus shift selection `[Früh, Spät, Nacht]`.
   - Geofencing: use `navigator.geolocation` and Haversine distance to the selected station. Block submission if GPS is disabled or distance exceeds the allowed radius.
   - Submit via HTTPS POST to the GitHub Repository Dispatch API (`/repos/{owner}/{repo}/dispatches`) with event type `checkin_event` and payload: `pin`, `name`, `station`, `shift`, `latitude`, `longitude`, `distance_m`, `timestamp`.

3. **Check-in workflow (`.github/workflows/checkin.yml` + `checkin.py`)**
   - Triggered by `checkin_event`.
   - Verify submitted PIN against `APP_PIN`; abort on mismatch.
   - Append one row per check-in to Google Sheets:
     - Employee sheet `{Name}_{MM_YYYY}`: [Date/Time, Station, Shift, Hours (7.0), Deviation (m), GPS Lat, GPS Long, Google Maps Link].
     - Station sheet `{Station}_{MM_YYYY}`: [Date/Time, Name, Shift, Hours (7.0), Deviation (m), GPS Lat, GPS Long, Google Maps Link].
   - Update monthly hour totals in the employee sheet.
   - Send Telegram message with name, station, shift, deviation, and map link.

4. **Monthly-report workflow (`.github/workflows/monthly_report.yml` + `generate_excel.py`)**
   - Cron trigger: 1st of the month at 07:00 UTC.
   - Download previous month's employee and station sheets.
   - Generate `Monatsbericht_{MM_YYYY}.xlsx` with one tab per original sheet.
   - Send the file as a Telegram attachment.

## Build, Test, and Lint

No formal build system, test runner, or linter is currently configured for the root project. The only executable artifact right now is:

```bash
python Station_json_generator.py
```

This regenerates `stations.json` from Overpass. It requires `requests` (`pip install requests`).

When the app is fully implemented, you will likely add:

- `requirements.txt` / `pyproject.toml` for Python dependencies (`gspread`, `pandas`, `openpyxl`, `requests`, `python-telegram-bot` or `requests`).
- A Python test runner such as `pytest`.
- A formatter/linter such as `ruff` or `black` + `flake8`.

Use the smallest targeted command that covers the changed behavior; escalate to full-suite runs only when targeted validation shows it is needed.

## Key Conventions

- **Secrets never belong in source code.** All credentials live in GitHub Secrets. Do not commit `service_account.json`, API keys, tokens, or the PIN. If you add local secret files, add them to `.gitignore` immediately.
- **Immutability for data transformations.** In Python helpers (e.g., Haversine, sheet-name formatting), return new values instead of mutating input dicts/lists.
- **Sheet naming.** Employee sheets use `{Name}_{MM_YYYY}` and station sheets use `{Station}_{MM_YYYY}`. Keep this exact pattern so the monthly exporter can find them.
- **Hours per shift are fixed at 7.0.** Do not make this configurable per check-in; it is a business rule.
- **Geofencing radius.** The architecture plan specifies 200 m, while the prompt mentions 100 m. Resolve this ambiguity before implementing the distance check, then use one value consistently in `app.js`, workflow validation, and tests.
- **German domain terms.** Preserve German labels in the UI and notifications: `Früh`, `Spät`, `Nacht`, `Monatsbericht`, sheet names, and Telegram messages.
- **Station name normalization.** `Station_json_generator.py` prefixes names with `U ` when missing (e.g., `Alexanderplatz` → `U Alexanderplatz`). Maintain this convention when matching selected stations against `stations.json` and sheet names.
- **Error handling.** Validate all external inputs (PIN, payload fields, geolocation, API responses). Never leak secrets or internal stack traces to the frontend or Telegram user.
- **No `console.log` in production frontend code.** Use structured error reporting or user-visible messages instead.
- **File size.** Keep files focused and small. Extract utilities (Haversine, sheet helpers, Telegram formatting) rather than creating monolithic workflow scripts.

## Security & Compliance

See `.github/instructions/security.instructions.md` for the full checklist. Critical items for this repo:

- Rotate any secret that has ever been committed (including `service_account.json` if it was previously tracked).
- Parameterize all Google Sheets/HTTP interactions; do not construct strings from unchecked user input.
- Rate-limit or otherwise protect the Repository Dispatch endpoint; the frontend exposes the event type and repository name to any visitor.
- Sanitize Telegram message text to avoid Markdown/HTML injection.

## Agent Usage

The `.github/instructions/agents.instructions.md` file defines the shared agents available in this repository. For BRW Check-in work, use:

- `planner` — before large features or refactoring.
- `tdd-guide` — when adding Python tests or new features.
- `code-reviewer` — after writing or modifying code.
- `security-reviewer` — before any commit that touches secrets, inputs, or API calls.
- `e2e-runner` — once Playwright tests are added for the GitHub Pages frontend.

## Useful Context Files to Read First

- `ARCHITEKTUR-PLAN & PROMPT.md` — architecture and original requirements.
- `stations.json` — sample of the station data shape.
- `.github/instructions/security.instructions.md` — secret handling rules.
- `.github/instructions/testing.instructions.md` — coverage and TDD expectations.
