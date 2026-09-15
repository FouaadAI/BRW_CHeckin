# Skill: Local Search Server

## Name
local-search-server

## Description
Provides a free, self-hosted search capability for K1NG agents using DuckDuckGo. No API keys required. Runs as a local Flask server on port 8765 and exposes a `/search` endpoint.

## When to Use
- When the Brave/SerpAPI search is unavailable, rate-limited, or requires a paid API key.
- When agents need to perform web searches as part of their analysis pipeline.
- During development or in environments without external search API access.

## How to Use

### Start the Server
```bash
cd K1NG-Makro/search_server
python server.py
```
The server listens on `http://localhost:8765`.

### Health Check
```bash
curl http://localhost:8765/health
```

### Search Endpoint
```bash
curl -X POST http://localhost:8765/search \
  -H "Content-Type: application/json" \
  -d '{"query": "gold price today", "max_results": 5}'
```

### Integration in Python
```python
from tools.search_server_client import search_web_via_server
results = search_web_via_server("gold price today", max_results=5)
```

## Architecture
- **Backend:** DuckDuckGo (via `duckduckgo-search` Python package)
- **Server:** Flask (`search_server/server.py`)
- **Client:** `tools/search_server_client.py` with automatic fallback to direct DDGS if server is offline.

## Files
- `search_server/server.py` – Flask server
- `tools/search_server_client.py` – Python client / fallback
- Registered in `agent_runner.py` as `search_web_via_server`

## Fallback Behavior
If the local server is unreachable, `search_web_via_server` automatically falls back to direct DuckDuckGo scraping using the same `duckduckgo-search` library.

## Notes
- No API keys required.
- Respects DuckDuckGo rate limits; do not abuse with excessive concurrent queries.
- `max_results` is capped at 20 per request.
