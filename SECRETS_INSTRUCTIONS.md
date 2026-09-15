# BRW Check-in – Secrets-Anleitung

> **WICHTIG:** Speichere in diesem Repository niemals echte Schlüssel, Tokens, PINs oder Service-Account-Dateien. Alle Werte in dieser Datei sind Platzhalter.

## Übersicht der Secrets

| Secret / Variable | Wo wird es benötigt? | Beschreibung |
|---|---|---|
| `PROXY_URL` | `config.js` im GitHub Pages Frontend | Öffentliche URL deines Cloudflare Workers. |
| `APP_PIN` | Cloudflare Worker Secret | 6-stelliger PIN, den die Mitarbeiter eingeben. |
| `GH_PAT` | Cloudflare Worker Secret | GitHub Personal Access Token für Repository Dispatch. |
| `DISPATCH_SECRET` | Cloudflare Worker Secret **und** GitHub Repository Secret | Gemeinsames Geheimnis, damit nur der Worker GitHub Actions triggern darf. |
| `EMPLOYEES_JSON` | Cloudflare Worker Secret | JSON-Array mit allen Mitarbeiternamen. |
| `REPO_OWNER` | Cloudflare Worker Environment Variable | GitHub-Benutzername oder Organisation. |
| `REPO_NAME` | Cloudflare Worker Environment Variable | Name des GitHub-Repositorys. |
| `ALLOWED_ORIGIN` | Cloudflare Worker Environment Variable | Domain deiner GitHub Pages-Seite. |
| `MAX_DISTANCE_METERS` | Cloudflare Worker Environment Variable (optional) | Geofencing-Radius in Metern, Standard: `200`. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | GitHub Repository Secret | Inhalt der Google Service-Account-JSON-Datei. |
| `GOOGLE_SPREADSHEET_ID` | GitHub Repository Secret | ID des Google Sheets-Dokuments. |
| `TELEGRAM_BOT_TOKEN` | GitHub Repository Secret | Token deines Telegram-Bots. |
| `TELEGRAM_CHAT_ID` | GitHub Repository Secret | Chat-ID des Empfängers (Chef). |

---

## 1. Cloudflare Worker Secrets

Diese Werte werden **nur im Cloudflare Worker** gespeichert. Sie greifen ins Repository, ohne dass Secrets im statischen Frontend liegen.

### Schritt 1: Worker anlegen

1. Öffne [https://dash.cloudflare.com](https://dash.cloudflare.com).
2. Wähle **Workers & Pages** → **Create application** → **Create Worker**.
3. Benenne den Worker z. B. `brw-checkin-proxy`.
4. Kopiere den Code aus `proxy/worker.js` in den Editor.
5. Klicke auf **Save and deploy**.
6. Notiere dir die Worker-URL (z. B. `https://brw-checkin-proxy.DEIN_BENUTZER.workers.dev`). Diese ist dein `PROXY_URL`.

### Schritt 2: Worker Secrets hinterlegen

Gehe im Worker auf **Settings** → **Variables and Secrets** und lege folgende Werte an:

| Name | Typ | Wert (Platzhalter) |
|---|---|---|
| `APP_PIN` | Secret | `123456` |
| `GH_PAT` | Secret | `ghp_HIER_DEIN_TOKEN_EINFÜGEN` |
| `DISPATCH_SECRET` | Secret | `HIER_EIN_LANGES_ZUFÄLLIGES_PASSWORT_EINFÜGEN` |
| `EMPLOYEES_JSON` | Secret | `["Ahmad Alsheekh","Ayham",...]` |
| `REPO_OWNER` | Plain text | `FouaadAI` |
| `REPO_NAME` | Plain text | `BRW_CHeckin` |
| `ALLOWED_ORIGIN` | Plain text | `https://FouaadAI.github.io` |
| `MAX_DISTANCE_METERS` | Plain text | `200` |

**Hinweis:** Wähle für `DISPATCH_SECRET` mindestens 32 zufällige Zeichen (z. B. mit `openssl rand -hex 32`).

---

## 2. GitHub Repository Secrets

Diese Werte werden in den **GitHub Repository Secrets** gespeichert und von den GitHub Actions-Workflows verwendet.

### Wo findest du die Einstellung?

1. Öffne dein Repository auf GitHub: `https://github.com/FouaadAI/BRW_CHeckin`
2. Gehe zu **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
3. Trage Name und Wert ein und klicke auf **Add secret**.

### Benötigte Secrets

| Name | Beschreibung | Wert (Platzhalter) |
|---|---|---|
| `DISPATCH_SECRET` | Gleicher Wert wie im Worker | `HIER_EIN_LANGES_ZUFÄLLIGES_PASSWORT_EINFÜGEN` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Vollständiger Inhalt der Service-Account-JSON | `{\n  \"type\": \"service_account\",\n  ...\n}` |
| `GOOGLE_SPREADSHEET_ID` | ID aus der URL deines Google Sheets | `1Q5vCkbDWObN8Xd5qIU1x8ZgUXqUF52yGSvEDnFePJJA` |
| `TELEGRAM_BOT_TOKEN` | Token von BotFather | `123456789:ABC...XYZ` |
| `TELEGRAM_CHAT_ID` | Chat-ID des Empfängers | `-1001234567890` oder `123456789` |

### Werte erstellen

#### `GOOGLE_SERVICE_ACCOUNT_JSON` – Google Cloud Console

1. Öffne [https://console.cloud.google.com/](https://console.cloud.google.com/).
2. Wähle oder erstelle ein Projekt.
3. Aktiviere die **Google Sheets API**.
4. Gehe zu **IAM & Admin** → **Service Accounts**.
5. Klicke auf **Create service account**.
6. Wähle **Manage keys** → **Add key** → **Create new key** → **JSON**.
7. Eine `.json`-Datei wird heruntergeladen.
8. Öffne die Datei in einem Texteditor, kopiere den **gesamten Inhalt** und füge ihn als Wert für `GOOGLE_SERVICE_ACCOUNT_JSON` ein.
9. Teile das Service-Account-E-Mail die Berechtigung **Editor** für dein Google Sheet.

#### `GOOGLE_SPREADSHEET_ID`

1. Öffne dein Google Sheet.
2. Die URL sieht so aus: `https://docs.google.com/spreadsheets/d/1Q5v.../edit`.
3. Der Teil zwischen `/d/` und `/edit` ist die Spreadsheet-ID.

#### `TELEGRAM_BOT_TOKEN` – BotFather

1. Öffne Telegram und schreibe mit [@BotFather](https://t.me/BotFather).
2. Sende `/newbot` und folge den Anweisungen.
3. Kopiere den Token, den BotFather dir gibt.

#### `TELEGRAM_CHAT_ID`

1. Schreibe dem Bot oder einer Gruppe eine Nachricht.
2. Rufe auf: `https://api.telegram.org/bot<HIER_BOT_TOKEN>/getUpdates`.
3. Suche nach `chat.id` und kopiere die Zahl.

---

## 3. Frontend-Config (`config.js`)

Die `config.js` enthält **ausschließlich** die öffentliche Worker-URL.

1. Kopiere `config.example.js` zu `config.js`:
   ```bash
   cp config.example.js config.js
   ```
2. Trage deine Worker-URL ein:
   ```javascript
   window.PROXY_URL = 'https://brw-checkin-proxy.DEIN_BENUTZER.workers.dev';
   ```
3. `config.js` ist in `.gitignore` eingetragen und darf **niemals** committed werden.

---

## 4. Wichtige Sicherheitshinweise

- Rotiere `GOOGLE_SERVICE_ACCOUNT_JSON`, falls jemals eine `service_account.json` im Repository lag.
- Verwende für `GH_PAT` einen **fine-grained Personal Access Token** mit Berechtigung **Actions: write** nur für dieses Repository.
- Veröffentliche `DISPATCH_SECRET`, `APP_PIN` und `GH_PAT` niemals.
- Prüfe vor jedem Commit mit `git status`, dass `config.js`, `service_account.json` und `employees.json` nicht vorgemerkt sind.
