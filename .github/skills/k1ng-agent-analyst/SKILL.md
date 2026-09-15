---
name: k1ng-agent-analyst
description: Common framework for the six K1NG domain agents — tool invocation rules, JSON output schema, price extraction, and validation.
---

# K1NG Agent Analyst Skill

Standardized workflow for the six K1NG layer agents (`physical`, `smart_money`, `polymarket`, `social`, `china`, `onchain`).

## Agent Inventory

| ID | Name | Layer | Prompt File | Minimum Tools |
|----|------|-------|-------------|---------------|
| `physical` | Physischer Analyst | 1 | `prompts/agent_1_physical.md` | `get_current_price`, `get_commodity_data`, `get_news` |
| `smart_money` | Smart Money Analyst | 2 | `prompts/agent_2_smart_money.md` | `get_current_price`, `get_cftc_cot_data`, `get_news` |
| `polymarket` | Prognosemarkt-Analyst | 3 | `prompts/agent_3_polymarket.md` | `get_current_price`, `get_polymarket_probability` |
| `social` | Social Velocity Analyst | 4 | `prompts/agent_4_social.md` | `get_current_price`, `get_news`, `search_web` |
| `china` | China-Spezialist | 5 | `prompts/agent_5_china.md` | `get_current_price`, `get_news`, `get_economic_indicator_av` |
| `onchain` | On-Chain & Flow Analyst | 6 | `prompts/agent_6_onchain.md` | `get_crypto_price`, `get_orderbook_depth` |

## Mandatory JSON Output Schema

Every agent MUST return **only** a JSON object with these exact top-level keys:

```json
{
  "agent": "Physischer Analyst",
  "layer": 1,
  "confidence": 82,
  "scores": {
    "oil": 65,
    "gold": 78,
    "btc": 55,
    "eurusd": 60
  },
  "prices": {
    "oil": 74.35,
    "gold": 4234.50,
    "btc": 76500.00,
    "eurusd": 1.1850
  },
  "reasoning": "Concise summary of the analysis...",
  "key_drivers": ["driver 1", "driver 2"]
}
```

### Field Rules

- `confidence`: integer 0–100 (clamped by `agent_runner.py`)
- `scores`: integers 0–100 per asset; 50 = neutral
- `prices`: **float values only** (or `null`). Never omit this field.
- `reasoning`: max ~700 chars (truncated for downstream prompts)

## Tool Invocation Protocol

### Step 1 – Identify Data Needs

The agent MUST NOT reuse prices or news from the Orchestrator context. It must call tools itself.

### Step 2 – Call Tools

Use the `task` tool or direct `llm.chat(..., tools=..., tool_choice='required')`.

For **Ollama** (no `tool_choice="required"`):
- Retry up to 2× with a strict user message:
  ```
  "⚠️ FEHLER: Du hast kein einziges Tool aufgerufen!
   Du MUSST mindestens die folgenden Tools verwenden: ..."
  ```
- If still no tool calls → return `{"error": "Agent hat keine Tools aufgerufen"}`

For **Ollama / BigModel**:
- First call with `tool_choice='auto'`
- If no tool calls → retry with `tool_choice='required'`

### Step 3 – Process Tool Results

After receiving tool results, append a user message:
```
"Bitte fahre mit deiner Analyse fort und gib das Ergebnis als gültiges JSON-Objekt aus. 
 Vergiss nicht das Feld `prices` mit den tatsächlich abgerufenen Preisen."
```

### Step 4 – Validate JSON

`agent_runner.py` performs these validations automatically:
1. Extracts JSON via regex `\{.*\}` (greedy dotall)
2. Clamps `confidence` to `[0, 100]`
3. Converts all `scores` values to integers
4. Validates `prices` dict: only `oil`, `gold`, `btc`, `eurusd` keys; float or null

## Price Extraction

### New Method (Preferred)

Use `_extract_prices_from_agents_new()` in `orchestrator.py`:
- Takes the `prices` field directly from each agent JSON
- Computes the **median** per asset across all agents
- Fallback: `None` if no agent reported a price

### Old Method (Fallback)

Regex extraction from `reasoning` text is deprecated but kept as fallback in `_extract_prices_from_agents()`.

## Copilot CLI Action Plan

When asked to work with an agent:

1. Open the agent's prompt file (`prompts/agent_{N}_{id}.md`) and read it.
2. Verify the `REQUIRED_TOOLS` mapping in `agent_runner.py`.
3. Ensure the agent prompt ends with an **ACTION PLAN** block that forces tool calls.
4. Run `python main.py --once` and inspect the agent JSON in the debug output.
5. If an agent returns `"error": "JSON‑Parsing fehlgeschlagen"`, check the raw output for markdown fences or explanatory text before/after the JSON.
