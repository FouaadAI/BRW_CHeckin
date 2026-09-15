# BRW Check-in

Serverlose Zeiterfassungs-App für BRW-Mitarbeiter mit PIN-Schutz, GPS-Geofencing (200 m) und automatischer Buchung in Google Sheets.

Die App läuft als statische GitHub Pages-Seite. Check-ins werden an einen **Cloudflare Worker** gesendet, der PIN, Mitarbeiter, Station und Geofencing serverseitig validiert und das Event sicher an die GitHub Repository Dispatch API weiterleitet. Ein GitHub Actions Workflow schreibt die Daten in Google Sheets und sendet eine Telegram-Nachricht. Am Monatsersten wird automatisch ein Excel-Monatsbericht erstellt.

Vollständige Architektur- und Anforderungsdetails stehen in [`ARCHITEKTUR-PLAN & PROMPT.md`](./ARCHITEKTUR-PLAN%20%26%20PROMPT.md).

## Funktionen

- PIN-geschütztes Check-in-Formular
- Auswahl aus Mitarbeiter- und Stations-Whitelist
- Geofencing per Haversine-Formel (max. 200 m zur U-Bahn-Station) – client- und serverseitig
- Automatische Anlage monatlicher Google-Sheets-Tabs pro Mitarbeiter und Station
- Telegram-Sofortbenachrichtigung an den Chef
- Monatlicher Excel-Export per Cron-Workflow

## Repository-Struktur

```
.
├── .github/workflows/
│   ├── checkin.yml             # Check-in Repository-Dispatch Handler
│   └── monthly_report.yml      # Monatlicher Excel-Export (Cron)
├── proxy/
│   └── worker.js               # Cloudflare Worker mit serverseitigen Secrets
├── src/                        # Wiederverwendbare Python-Helper
│   ├── haversine.py            # Distanzberechnung
│   ├── sheets_helpers.py       # Tabellen-Namen, Zeilenformatierung
│   ├── payload_validator.py    # Payload-Validierung
│   └── telegram_notifier.py    # Telegram API-Wrapper
├── tests/                      # pytest-Tests
├── stations.json               # Berliner U-Bahnhöfe mit GPS-Koordinaten
├── employees.example.json      # Beispiel-Whitelist (echte Liste im Worker Secret)
├── index.html                  # Frontend (GitHub Pages)
├── app.js                      # Frontend-Logik
├── config.example.js           # Beispiel-Konfiguration für Frontend
├── config.js                   # Lokale Frontend-Konfiguration (nicht committen!)
├── checkin.py                  # Check-in Workflow-Skript
├── generate_excel.py           # Monatsbericht Workflow-Skript
├── SECRETS_INSTRUCTIONS.md     # Schritt-für-Schritt-Anleitung für alle Secrets
└── README.md                   # Diese Datei
```

## Sicherheitsarchitektur

- **Frontend (`config.js`)**: Enthält ausschließlich die öffentliche URL des Cloudflare Workers. Keine Tokens, PINs oder Schlüssel.
- **Cloudflare Worker**: Hält `APP_PIN`, `GH_PAT`, `DISPATCH_SECRET` und die Mitarbeiterliste (`EMPLOYEES_JSON`) als Secrets. Validiert PIN und Geofencing und leitet an GitHub Dispatch weiter.
- **GitHub Actions**: Validiert das gemeinsame `DISPATCH_SECRET` und schreibt in Google Sheets / Telegram.
- **GitHub Repository Secrets**: `DISPATCH_SECRET`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_SPREADSHEET_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

Die vollständige Liste aller Secrets und deren Einrichtung findest du in [`SECRETS_INSTRUCTIONS.md`](./SECRETS_INSTRUCTIONS.md).

## Erforderliche GitHub Repository Secrets

Im Repository müssen folgende Secrets hinterlegt werden (`Settings → Secrets and variables → Actions`):

| Secret | Zweck |
|--------|-------|
| `DISPATCH_SECRET` | Gemeinsames Geheimnis mit dem Cloudflare Worker, um gefälschte Dispatch-Events zu verhindern |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | JSON-String des Google Service-Account-Keys |
| `GOOGLE_SPREADSHEET_ID` | ID des Google Sheets für Zeiterfassung |
| `TELEGRAM_BOT_TOKEN` | Token des Telegram-Bots |
| `TELEGRAM_CHAT_ID` | Chat-ID des Empfängers (Chef) |

## Cloudflare Worker einrichten

1. Öffne [https://dash.cloudflare.com](https://dash.cloudflare.com) und lege einen neuen Worker an.
2. Kopiere den Code aus `proxy/worker.js` in den Editor.
3. Hinterlege die Worker Secrets/Variablen gemäß [`SECRETS_INSTRUCTIONS.md`](./SECRETS_INSTRUCTIONS.md).
4. Notiere die Worker-URL – diese wird als `PROXY_URL` in `config.js` eingetragen.

## Lokale Einrichtung

1. Python-Abhängigkeiten installieren:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   # source .venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```

2. `config.js` aus `config.example.js` kopieren und nur die Worker-URL eintragen:

   ```bash
   copy config.example.js config.js
   ```

3. `service_account.json` lokal ablegen (wird aus Git ausgeschlossen) – nur für lokale Tests/Entwicklung nötig.

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
2. Sicherstellen, dass `config.js`, `service_account.json` und `employees.json` nicht im Repository liegen (siehe `.gitignore`).
3. Nach dem ersten Deploy ist die App unter `https://{owner}.github.io/{repo}/` erreichbar.
4. Erstelle lokal die Datei `config.js` aus `config.example.js` mit der Worker-URL. Da `config.js` in `.gitignore` steht, wird sie nicht committet, muss aber vor dem Pages-Build im Root vorhanden sein.

## Sicherheit

- `config.js`, `service_account.json` und `employees.json` dürfen **niemals** committet werden.
- Alle Secrets werden ausschließlich über Cloudflare Worker Secrets bzw. GitHub Repository Secrets geladen.
- Eingaben werden clientseitig, im Worker und im Workflow validiert.
- **Rate-Limiting**: Der Absenden-Button ist nach einem Check-in 10 Sekunden lang deaktiviert. Der Worker verweigert Anfragen ohne gültige PIN. Der Workflow verweigert einen erneuten Check-in desselben Mitarbeiters innerhalb von 5 Minuten.
- **HTML-Escaping**: Benutzerkontrollierte Werte in Telegram-Nachrichten werden escaped, um HTML-Injection zu vermeiden.
- **Dispatch-Secret**: Jede Anfrage vom Worker an GitHub enthält ein Shared Secret, das der Workflow prüft. So können keine Dispatch-Events von außen direkt ausgelöst werden.
- Keine API-Keys, Tokens oder PINs im Quellcode hinterlegen.

## Mitwirken

Änderungen am Code sollten mit pytest-Tests und einem Coverage-Bericht von mindestens 80 % einhergehen. Siehe `.github/instructions/testing.instructions.md`.
