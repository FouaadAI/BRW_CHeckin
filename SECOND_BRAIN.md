# 🧠 Second Brain – BRW Check-in

> **Lebendiges Projektwissen.** Diese Datei wird bei jeder relevanten Änderung aktualisiert. Sie dient als zentrale Wahrheitsquelle für Architektur, Sicherheit, Deployment und Entscheidungen.

---

## 1. Projekt-Identität

| Eigenschaft | Wert |
|---|---|
| **Name** | BRW Check-in |
| **Zweck** | Serverlose Zeiterfassung/Check-in für BRW-Mitarbeiter an Berliner U-Bahn-Stationen |
| **Repository** | `FouaadAI/BRW_CHeckin` (public) |
| **Hosting** | GitHub Pages (Frontend) + Cloudflare Worker (Proxy) + GitHub Actions (Backend) |
| **Datenbank** | Google Sheets |
| **Benachrichtigung** | Telegram Bot |
| **Sprache** | Deutsch |
| **Stand** | Sicherheitsrefactor mit Proxy abgeschlossen, 98/98 Tests, ~94 % Coverage |

---

## 2. Architektur-Übersicht

```
┌─────────────────┐      HTTPS       ┌──────────────────┐      HTTPS       ┌─────────────────┐
│  GitHub Pages   │ ───────────────> │  Cloudflare      │ ───────────────> │  GitHub Actions │
│  index.html     │   PROXY_URL      │  Worker (Proxy)  │   Dispatch API   │  checkin.yml    │
│  app.js         │                  │  - APP_PIN       │                  │  monthly_report │
│  config.js      │                  │  - GH_PAT        │                  │  .yml            │
│  (nur URL)      │                  │  - DISPATCH_SEC  │                  │                  │
└─────────────────┘                  │  - EMPLOYEES     │                  └────────┬────────┘
                                       └──────────────────┘                           │
                                                                                      ▼
                                                                             ┌─────────────────┐
                                                                             │  Google Sheets  │
                                                                             │  Telegram Bot │
                                                                             └─────────────────┘
```

### Warum diese Architektur?

Das statische Frontend darf **keine Secrets** enthalten. Daher leitet ein Cloudflare Worker alle sicherheitskritischen Operationen (PIN-Prüfung, Geofencing, Dispatch-Autorisierung) serverseitig weiter. GitHub Actions verarbeitet nur noch authentifizierte Events vom bekannten Worker.

---

## 3. Nicht-verhandelbare Regeln

### Sicherheit (Top-Priorität)

1. **Keine Secrets im Repository.** Nie. Nirgends. Keine Ausnahme.
   - Verboten: `GH_PAT`, `APP_PIN`, `DISPATCH_SECRET`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `service_account.json`, echte `employees.json`.
2. **Frontend (`config.js`)** enthält ausschließlich die öffentliche `PROXY_URL`.
3. **Alle Geheimnisse** werden nur in Cloudflare Worker Secrets oder GitHub Repository Secrets gespeichert.
4. **Mitarbeiter-Whitelist** liegt nicht mehr im öffentlichen Repository, sondern als `EMPLOYEES_JSON` im Worker.
5. **Eingaben werden dreifach validiert:** Client (UX), Worker (authoritativ), GitHub Actions (Persistenz).
6. **Rate-Limiting:** 10 Sekunden Client-Cooldown, 5 Minuten serverseitige Deduplizierung pro Mitarbeiter.
7. **HTML-Escaping** für alle benutzerkontrollierten Werte in Telegram-Nachrichten.
8. **Geofencing:** 200 m Radius, Haversine-Formel, client- und serverseitig.

### Code-Qualität

1. **Keine Änderung ohne Test.** Zielabdeckung: mindestens 80 %, aktuell ~94 %.
2. **Keine Änderung ohne `pytest` durchlaufen.**
3. **Keine Änderung ohne `git status`-Prüfung** auf `config.js`, `service_account.json`, `employees.json`.
4. **Conventional Commits:** `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `ci:`.
5. **Co-authored-by Trailer** bei Git-Commits.
6. **Sicherheitsreview** nach jeder größeren Änderung.

---

## 4. Verantwortlichkeiten der Dateien

| Datei / Ordner | Aufgabe | Sensitivität |
|---|---|---|
| `index.html` | PIN-Eingabe, Check-in-UI, Mitarbeiter-/Stations-Auswahl | Öffentlich |
| `app.js` | Frontend-Logik, Geolocation, Aufruf des Proxies | Öffentlich |
| `config.js` | Nur `window.PROXY_URL` | Öffentlich, aber `.gitignore` |
| `config.example.js` | Template für `config.js` | Öffentlich |
| `proxy/worker.js` | PIN, Geofencing, Dispatch-Secret, Mitarbeiterliste, GitHub Dispatch | **Kritisch – hält Secrets** |
| `stations.json` | Berliner U-Bahnhöfe mit GPS | Öffentlich |
| `employees.example.json` | Beispiel-Whitelist | Öffentlich |
| `employees.json` | Echte Whitelist (lokal, nicht committet) | **Nicht im Repo** |
| `checkin.py` | Repository-Dispatch-Handler, schreibt Sheets & Telegram | Serverseitig |
| `generate_excel.py` | Monatlicher Excel-Export | Serverseitig |
| `src/` | Python-Helper: Haversine, Sheets, Validator, Telegram | Öffentlich |
| `tests/` | pytest-Tests | Öffentlich |
| `.github/workflows/checkin.yml` | Trigger für Check-in Events | Serverseitig |
| `.github/workflows/monthly_report.yml` | Cron-Export am 1. des Monats | Serverseitig |
| `SECRETS_INSTRUCTIONS.md` | Schritt-für-Schritt-Anleitung für Secrets | Öffentlich, nur Platzhalter |
| `README.md` | Projekt-Dokumentation | Öffentlich |
| `SECOND_BRAIN.md` | Diese Datei | Öffentlich |

---

## 5. Secrets-Inventar

### Cloudflare Worker Secrets / Environment Variables

| Name | Typ | Zweck |
|---|---|---|
| `APP_PIN` | Secret | 6-stelliger Mitarbeiter-PIN |
| `GH_PAT` | Secret | GitHub Personal Access Token für Dispatch |
| `DISPATCH_SECRET` | Secret | Shared Secret Worker ↔ GitHub Actions |
| `EMPLOYEES_JSON` | Secret | JSON-Array aller Mitarbeiternamen |
| `REPO_OWNER` | Plain | GitHub Owner (`FouaadAI`) |
| `REPO_NAME` | Plain | Repository-Name (`BRW_CHeckin`) |
| `ALLOWED_ORIGIN` | Plain | GitHub Pages-Domain |
| `MAX_DISTANCE_METERS` | Plain | Geofencing-Radius (Standard: `200`) |

### GitHub Repository Secrets

| Name | Zweck |
|---|---|
| `DISPATCH_SECRET` | Gleicher Wert wie im Worker |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Inhalt der Google Service-Account-JSON |
| `GOOGLE_SPREADSHEET_ID` | Google Sheets-ID |
| `TELEGRAM_BOT_TOKEN` | Telegram-Bot-Token |
| `TELEGRAM_CHAT_ID` | Empfänger-Chat-ID |

### Frontend-Config

| Name | Ort | Wert |
|---|---|---|
| `PROXY_URL` | `config.js` | Öffentliche Worker-URL |

> **Wichtig:** Details und Erstellungsanleitungen stehen in `SECRETS_INSTRUCTIONS.md`.

---

## 6. Entscheidungs-Log (Decision Log)

| Datum | Entscheidung | Begründung | Status |
|---|---|---|---|
| 2026-09-15 | Cloudflare Worker als Proxy einführen | Client-seitige Secrets (GH_PAT, APP_PIN) eliminieren | ✅ Aktiv |
| 2026-09-15 | `APP_PIN` aus GitHub Actions entfernen, `DISPATCH_SECRET` einführen | Workflow muss nur noch Worker-Events vertrauen | ✅ Aktiv |
| 2026-09-15 | `employees.json` aus Repo entfernen, als Worker-Secret speichern | Klarname-Schutz, keine öffentliche Mitarbeiterliste | ✅ Aktiv |
| 2026-09-15 | `config.js` behält nur `PROXY_URL` | Öffentliche URL ist unbedenklich, alles andere ist Secret | ✅ Aktiv |
| 2026-09-15 | 10s Client-Cooldown + 5min Server-Deduplizierung | Rate-Limiting gegen Missbrauch | ✅ Aktiv |
| 2026-09-15 | HTML-Escaping in Telegram-Nachrichten | Verhindert HTML-Injection | ✅ Aktiv |
| 2026-09-15 | Haversine client- und serverseitig | Schnelles UX-Feedback + autoritative Prüfung | ✅ Aktiv |

---

## 7. Änderungs-Log (Change Log)

> Jede relevante Code-, Config- oder Architekturänderung wird hier mit Datum, Beschreibung und Commit/PR vermerkt.

| Datum | Änderung | Dateien betroffen | Autor |
|---|---|---|---|
| 2026-09-15 | Initialer Second Brain erstellt | `SECOND_BRAIN.md` | Copilot |
| 2026-09-15 | Security-Refactor mit Cloudflare Worker Proxy | `proxy/worker.js`, `app.js`, `checkin.py`, `.github/workflows/checkin.yml`, `tests/test_checkin.py`, `README.md`, `SECRETS_INSTRUCTIONS.md`, `.github/copilot-instructions.md` | Copilot |
| 2026-09-15 | `employees.json` aus Repo entfernt, `employees.example.json` hinzugefügt | `employees.json`, `employees.example.json`, `.gitignore` | Copilot |
| 2026-09-15 | `config.example.js` auf `PROXY_URL` reduziert | `config.example.js` | Copilot |

---

## 8. Test- & Qualitäts-Gates

```bash
# Alle Tests
pytest

# Mit Coverage
pytest --cov=.

# HTML-Coverage-Report
pytest --cov=. --cov-report=html
```

### Akzeptanzkriterien vor jedem Push

- [ ] `pytest` läuft erfolgreich (aktuell 98/98 Tests)
- [ ] Coverage ≥ 80 % (aktuell ~94 %)
- [ ] `git status` zeigt keine Secrets (`config.js`, `service_account.json`, `employees.json`)
- [ ] Keine `console.log` im Produktionscode (nur wenn absichtlich für Debugging)
- [ ] Sicherheitsreview bei Änderungen an `proxy/worker.js`, `app.js`, `checkin.py`, Workflows

---

## 9. Deployment-Checkliste

### Einmalig (Initial)

1. Cloudflare Worker anlegen und `proxy/worker.js` deployen.
2. Cloudflare Worker Secrets/Variablen hinterlegen.
3. GitHub Repository Secrets hinterlegen.
4. Lokal `config.js` aus `config.example.js` erstellen und `PROXY_URL` eintragen.
5. Google Sheet anlegen und Service-Account-E-Mail als Editor einladen.
6. GitHub Pages in Repository-Settings aktivieren (`main`, `/(root)`).
7. Telegram-Bot anlegen und Chat-ID konfigurieren.

### Vor jedem Release

- [ ] Tests grün
- [ ] Keine Secrets im Diff
- [ ] README und `SECRETS_INSTRUCTIONS.md` auf aktuellen Stand geprüft
- [ ] `SECOND_BRAIN.md` aktualisiert
- [ ] Cloudflare Worker ggf. neu deployen, wenn `proxy/worker.js` geändert wurde

---

## 10. Bekannte offene Punkte / TODOs

| # | Thema | Priorität | Status |
|---|---|---|---|
| 1 | Google Service-Account-Key rotieren, falls jemals `service_account.json` im Repo lag | 🔴 Hoch | Offen – manuelle Aktion Benutzer |
| 2 | Cloudflare Worker deployen und Secrets konfigurieren | 🔴 Hoch | Offen – manuelle Aktion Benutzer |
| 3 | GitHub Repository Secrets anlegen | 🔴 Hoch | Offen – manuelle Aktion Benutzer |
| 4 | Entscheidung: `config.js` beibehalten oder `PROXY_URL` direkt in `index.html` inlinen | 🟡 Mittel | Diskussion läuft |
| 5 | Produktions-Test mit echtem Gerät (GPS, Distanz, Telegram, Sheets) | 🟡 Mittel | Offen |
| 6 | Dokumentation für Mitarbeiter (Kurzanleitung App-Nutzung) | 🟢 Niedrig | Offen |

---

## 11. Kommunikations- & Arbeitspräferenzen

- **Sprache:** Deutsch (Projekt- und Benutzerkommunikation).
- **Commit-Stil:** Conventional Commits, kurz und präzise.
- **Dokumentation:** Wichtige Änderungen sofort in `README.md`, `SECRETS_INSTRUCTIONS.md` und `SECOND_BRAIN.md` nachziehen.
- **Sicherheit:** Bei Unsicherheit immer „Secure by Default“ wählen und den Benutzer fragen.
- **Tests:** Keine Code-Änderung ohne passenden Test oder explizite Begründung, warum keiner nötig ist.
- **Iterativ arbeiten:** Bei komplexen Aufgaben zuerst Plan, dann Implementierung, dann Review, dann Dokumentation.

---

## 12. Schnellzugriff: Wichtige Befehle

```bash
# Python-Umgebung
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Tests
pytest
pytest --cov=.

# Stations regenerieren
python Station_json_generator.py

# Git-Prüfung vor Commit
git status
git diff --name-only
```

---

## 13. Kontext für zukünftige Agenten / Copilot-Sessions

Wenn diese Datei in einer neuen Session gelesen wird:

1. **Sicherheit hat oberste Priorität.** Prüfe sofort, ob Secrets im Code oder in neuen Dateien auftauchen.
2. **Der Proxy ist zentral.** Änderungen am Frontend oder Workflow müssen mit `proxy/worker.js` kompatibel bleiben.
3. **Secrets gehören niemals in den Client.** Wenn eine Anforderung das erfordert, einen Proxy oder serverseitigen Endpunkt vorschlagen.
4. **Mitarbeiterliste kommt aus `EMPLOYEES_JSON` im Worker**, nicht mehr aus `employees.json` im Repo.
5. **Aktualisiere dieses Second Brain** bei jeder relevanten Änderung.
6. **Frage den Benutzer**, bevor du Architektur- oder Sicherheitsentscheidungen änderst.

---

*Letzte Aktualisierung: 2026-09-15*
*Version: 1.0*
*Status: Aktiv*
