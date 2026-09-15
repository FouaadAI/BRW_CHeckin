import json
import sys
import requests

# Auslands- & Turbo-Endpoints, die HTTP 406 vermeiden
endpoints = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
    "https://overpass-api.de/api/interpreter"
]

# Query im vereinfachten Format
overpass_query = """
[out:json][timeout:30];
area["name"="Berlin"]["admin_level"="4"]->.a;
(
  node["station"="subway"](area.a);
  node["railway"="station"]["subway"="yes"](area.a);
);
out body;
"""

print("Lade U-Bahn-Daten von OpenStreetMap...")

# Vollständiger Browser-Header um HTTP 406 (Not Acceptable) zu umgehen
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://overpass-turbo.eu",
    "Referer": "https://overpass-turbo.eu/"
}

session = requests.Session()
session.headers.update(headers)

data = None

for endpoint in endpoints:
    try:
        print(f"Versuche Endpoint: {endpoint} ...")
        res = session.post(endpoint, data={"data": overpass_query}, timeout=30)
        
        if res.status_code == 200:
            data = res.json()
            print(" -> Erfolgreich geladen!")
            break
        else:
            print(f" -> Statuscode: {res.status_code}")
    except Exception as e:
        print(f" -> Verbindungsfehler: {e}")

if not data or "elements" not in data:
    print("\nFehler: Server blockieren weiterhin. Nutze den manuellen Weg 2 unten.")
    sys.exit(1)

stations = []
seen_names = set()

for element in data.get("elements", []):
    name = element.get("tags", {}).get("name")
    if name and name not in seen_names:
        clean_name = name if name.startswith("U ") else f"U {name}"
        stations.append({
            "name": clean_name,
            "lat": round(element["lat"], 6),
            "lng": round(element["lon"], 6)
        })
        seen_names.add(name)

stations = sorted(stations, key=lambda x: x["name"])

with open("stations.json", "w", encoding="utf-8") as f:
    json.dump(stations, f, ensure_ascii=False, indent=2)

print(f"\nFertig! {len(stations)} U-Bahnhöfe wurden in 'stations.json' gespeichert.")