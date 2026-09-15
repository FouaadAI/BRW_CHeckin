# BRW Check-in

Serverlose Zeiterfassungs-App für BRW-Mitarbeiter mit PIN-Schutz, GPS-Geofencing (200 m) und automatischer Buchung in Google Sheets.

Die App läuft als statische GitHub Pages-Seite. Check-ins werden per GitHub Repository Dispatch API an einen GitHub Actions Workflow übergeben, der die Daten in Google Sheets schreibt und eine Telegram-Nachricht sendet. Am Monatsersten wird automatisch ein Excel-Monatsbericht erstellt.

Vollständige Architektur- und Anforderungsdetails stehen in [`ARCHITEKTUR-PLAN & PROMPT.md`](./ARCHITEKTUR-PLAN%20%26%20PROMPT.md).

## Funktionen

- PIN-geschütztes Check-in-Formular
- Auswahl aus Mitarbeiter- und Stations-Whitelist
- Geofencing per Haversine-Formel (max. 200 m zur U-Bahn-Station)
- Automatische Anlage monatlicher Google-Sheets-Tabs pro Mitarbeiter und Station
- Telegram-Sofortbenachrichtigung an den Chef
- Monatlicher Excel-Export per Cron-Workflow

## Repository-Struktur

```
.
├── .github/workflows/
│   ├── checkin.yml             # Check-in Repository-Dispatch Handler
│   └── monthly_report.yml      # Monatlicher Excel-Export (Cron)
├── src/                        # Wiederverwendbare Python-Helper
│   ├── haversine.py            # Distanzberechnung
│   ├── sheets_helpers.py       # Tabellen-Namen, Zeilenformatierung
│   ├── payload_validator.py    # Payload-Validierung
│   └── telegram_notifier.py    # Telegram API-Wrapper
├── tests/                      # pytest-Tests
├── employees.json              # Whitelist der 13 Mitarbeiter
├── stations.json               # Berliner U-Bahnhöfe mit GPS-Koordinaten
├── Station_json_generator.py   # Regeneriert stations.json aus OpenStreetMap
├── index.html                  # Frontend (GitHub Pages)
├── app.js                      # Frontend-Logik
├── config.example.js           # Beispiel-Konfiguration für Frontend
├── config.js                   # Lokale Frontend-Konfiguration (nicht committen!)
├── checkin.py                  # Check-in Workflow-Skript
├── generate_excel.py           # Monatsbericht Workflow-Skript
└── README.md                   # Diese Datei
```

## Erforderliche GitHub Secrets

Im Repository müssen folgende Secrets hinterlegt werden (`Settings → Secrets and variables → Actions`):

| Secret | Zweck |
|--------|-------|
| `APP_PIN` | 6-stelliger numerischer PIN für den Check-in-Zugriff |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | JSON-String des Google Service-Account-Keys |
| `GOOGLE_SPREADSHEET_ID` | ID des Google Sheets für Zeiterfassung |
| `TELEGRAM_BOT_TOKEN` | Token des Telegram-Bots |
| `TELEGRAM_CHAT_ID` | Chat-ID des Empfängers (Chef) |
| `GH_PAT` | GitHub Personal Access Token für die Dispatch API (`repo` scope) |

## Lokale Einrichtung

1. Python-Abhängigkeiten installieren:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   # source .venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```

2. `config.js` aus `config.example.js` kopieren und anpassen:

   ```bash
   copy config.example.js config.js
   ```

3. `service_account.json` lokal ablegen (wird aus Git ausgeschlossen).

## Google Sheet einrichten

1. Ein neues Google Sheet anlegen und die Service-Account-E-Mail als Bearbeiter:in einladen.
2. Der Workflow erzeugt pro Monat automatisch Tabs nach dem Muster:
   - `Mitarbeiter Name_MM_YYYY`
   - `U Station_MM_YYYY`
3. Erwartete Spaltenüberschriften (werden bei Erzeugung eines neuen Tabs automatisch geschrieben):

   ```
   Datum/Uhrzeit | Station/Name | Schicht | Arbeitsstunden | Abweichung (m) | GPS Lat | GPS Long | Google Maps Link
   ```

## Tests lokal ausführen

Alle Tests mit pytest:

```bash
pytest
```

Mit Coverage-Bericht:

```bash
pytest --cov=.
```

Ein HTML-Coverage-Report lässt sich erzeugen mit:

```bash
pytest --cov=. --cov-report=html
```

Zielabdeckung: mindestens 80 %.

## `stations.json` regenerieren

Die Liste der Berliner U-Bahnhöfe kann jederzeit neu aus OpenStreetMap geladen werden:

```bash
python Station_json_generator.py
```

Das Skript schreibt das Ergebnis nach `stations.json`.

## Deployment auf GitHub Pages

1. Im Repository unter `Settings → Pages` als Quelle **Deploy from a branch** wählen und **main** / **/(root)** auswählen.
2. Sicherstellen, dass `config.js` und `service_account.json` nicht im Repository liegen (siehe `.gitignore`).
3. Nach dem ersten Deploy ist die App unter `https://{owner}.github.io/{repo}/` erreichbar.
4. Erstelle lokal (oder im CI-Deploy-Schritt) die Datei `config.js` aus `config.example.js` mit den echten Werten. Da `config.js` in `.gitignore` steht, wird sie nicht committet, muss aber vor dem Pages-Build im Root vorhanden sein.

## Sicherheit

- `config.js` (Frontend-Konfiguration) und der Google Service-Account-Key dürfen **niemals** committet werden.
- Alle Secrets werden ausschließlich über GitHub Secrets in die Workflows geladen.
- Eingaben werden server- und clientseitig validiert.
- **Rate-Limiting**: Der Absenden-Button ist nach einem Check-in 10 Sekunden lang deaktiviert. Der Workflow verweigert einen erneuten Check-in desselben Mitarbeiters innerhalb von 5 Minuten, indem er das Mitarbeiter-Blatt prüft.
- **HTML-Escaping**: Benutzerkontrollierte Werte in Telegram-Nachrichten werden escaped, um HTML-Injection zu vermeiden.
- **Wichtiger Hinweis zum Frontend-Token**: Das GitHub Pages-Frontend ist statisch. Damit es Repository-Dispatch-Events auslösen kann, enthält `config.js` einen GitHub PAT (`GH_PAT`), der im Browser lesbar ist. Das ist ein bewusster Kompromiss für den MVP. Erwäge baldmöglichst den Einsatz eines minimalen serverlosen Proxys (z. B. Cloudflare Worker, Vercel Edge Function), der das Token geheim hält und die Anfrage weiterleitet. Bei Verdacht auf eine Kompromittierung des PATs dieses sofort rotieren. Verwende für den PAT möglichst einen Fine-Grained Token mit der kleinstmöglichen Berechtigung auf dieses Repository (z. B. `Actions: write`).
- Keine API-Keys, Tokens oder PINs im Quellcode hinterlegen.

## Mitwirken

Änderungen am Code sollten mit pytest-Tests und einem Coverage-Bericht von mindestens 80 % einhergehen. Siehe `.github/instructions/testing.instructions.md`.
