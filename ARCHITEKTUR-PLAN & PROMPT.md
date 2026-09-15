# ARCHITEKTUR-PLAN 

1. Data & Configuration Layer (stations.json, employees.json & Secrets)
 * Public Geodaten & Stammdaten:
   * stations.json: Enthält Stationsnamen und GPS-Koordinaten.
   * employees.json: Enthält die vordefinierte Liste der 13 zugelassenen Mitarbeiter.
 * Privatsphäre & Security Layer:
   * Keine API-Keys, Telegram-Tokens oder Google-Credentials im Quellcode.
   * GitHub Secrets: Verwaltung aller vertraulichen Zugangsdaten (GH_PAT, GOOGLE_SERVICE_ACCOUNT_JSON, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, APP_PIN).
2. Frontend Layer (GitHub Pages – index.html & app.js)
 * Integrierte PIN-Sperre (Screen 1): PIN-Eingabemaske blockiert den Zugriff auf das Formular vor der Authentifizierung.
 * Formular & Geofencing (Screen 2 – nach PIN-Eingabe):
   * Name (Suchbares Dropdown): Befüllt aus employees.json (z. B. via HTML5 <datalist> oder <select>). Freie Texteingabe ist deaktiviert, um Tippfehler und abweichende Schreibweisen zu verhindern.
   * Station (Suchbares Dropdown): Befüllt aus stations.json.
   * Schicht: Auswahl [Früh, Spät, Nacht].
   * GPS-Erfassung & Haversine 200m-Prüfung: Blockiert das Absenden strikt bei deaktiviertem GPS oder einer Distanz > 200 Meter.
 * Serverloser POST-Trigger: Übermittlung per Dispatch API an GitHub Actions.
3. Real-Time Backend Layer & Monthly Reporting Layer
(Unverändert: Verifizierung der PIN, Buchen von 7.0 Std. in Google Sheets, Telegram-Push und monatlicher Excel-Export).


# PROMPT FÜR DIE UMSETZUNG

Erstelle eine vollständige, professionelle und serverlose Web-Anwendung für Zeiterfassung/Check-in mit PIN-Schutz, Geofencing (200m-Sperre), GitHub Pages, GitHub Actions, Google Sheets API und Telegram Bot API.

Achte strikt darauf, dass KEINE Passwörter, API-Keys oder Tokens im Code stehen. Alle sensiblen Daten MÜSSEN über GitHub Secrets geladen werden.

### 1. DATENBANKEN (JSON-Dateien)
- `stations.json`: JSON-Datei mit Namen und GPS-Koordinaten (lat, lng) aller Berliner U-Bahnhöfe (U1-U9).
- `employees.json`: JSON-Datei mit einem Array von 13 vordefinierten Mitarbeiter-Namen (z. B. ["Max Mustermann", "Erika Musterfrau", ...]).

### 2. FRONTEND (index.html & app.js auf GitHub Pages)
- PIN-Schutz / Gatekeeper (Screen 1):
  - Standardmäßig wird NUR ein PIN-Eingabefeld angezeigt.
  - Erst nach Eingabe der korrekten PIN öffnet sich das Check-in-Formular.
- Check-in Formular (Screen 2):
  1. Name: Suchbares Dropdown-Menü (z. B. HTML5 <datalist> mit Eingabefeld oder Bootstrap/Select2), dynamisch befüllt aus `employees.json`. Freier Text darf NICHT eingegeben werden – die Auswahl MUSS strikt aus der Liste erfolgen, um abweichende Schreibweisen zu vermeiden.
  2. Station: Suchbares Menü, befüllt aus `stations.json`.
  3. Schicht: Dropdown [Früh, Spät, Nacht].
- Geolocation & Geofencing (200m-Sperre):
  - Beim Klick auf "Absenden" wird GPS abgefragt (`navigator.geolocation`).
  - Wenn GPS aus/abgelehnt -> ABSENDEN BLOCKIEREN.
  - Berechne mittels Haversine-Formel die Distanz zur ausgewählten U-Bahn-Station.
  - Wenn Distanz > 200m -> ABSENDEN BLOCKIEREN und Fehlermeldung ("Du bist X Meter entfernt") anzeigen.
- Absenden:
  - HTTPS POST-Request an GitHub Repository Dispatch API (`https://api.github.com/repos/{owner}/{repo}/dispatches`) mit Action `checkin_event` und Payload: `pin`, `name`, `station`, `shift`, `latitude`, `longitude`, `distance_m`, `timestamp`.

### 3. CHECK-IN WORKFLOW (.github/workflows/checkin.yml & checkin.py)
- Reagiert auf `checkin_event`.
- Liest Secrets aus GitHub Secrets: `APP_PIN`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
- Bricht sofort ab, wenn übermittelte PIN nicht mit `APP_PIN` übereinstimmt.
- Bucht automatisch 7.0 Arbeitsstunden pro Schicht.
- Google Sheets API (gspread):
  1. Mitarbeiter-Blatt `{Name}_{MM_YYYY}`: Zeile anhängen [Datum/Uhrzeit, Station, Schicht, Arbeitsstunden (7.0), Abweichung (m), GPS Lat, GPS Long, Google Maps Link] und Summe der Monatsstunden aktualisieren.
  2. Stationen-Blatt `{Station}_{MM_YYYY}`: Zeile anhängen [Datum/Uhrzeit, Name, Schicht, Arbeitsstunden (7.0), Abweichung (m), GPS Lat, GPS Long, Google Maps Link].
- Telegram Bot API:
  - Sendet Sofort-Nachricht an den Chef mit Name, Station, Schicht, Distanz in Metern und Google Maps Link.

### 4. MONATSABSCHLUSS WORKFLOW (.github/workflows/monthly_report.yml & generate_excel.py)
- Cronjob-Trigger: Läuft am 1. des Monats um 07:00 UTC.
- Skript:
  - Lädt alle Blätter des Vormonats aus Google Sheets herunter.
  - Erstellt mit `pandas` / `openpyxl` EINE EINZELNE Excel-Datei (`Monatsbericht_{MM_YYYY}.xlsx`), bei der jedes Mitarbeiter- und Stationen-Blatt als eigener TAB abgelegt ist.
  - Sendet die `.xlsx`-Datei als Anhang per Telegram Bot an den Chef.

Erstelle den vollständigen, produktionsreifen HTML-, JavaScript-, Python- und YAML-Code für alle Dateien.