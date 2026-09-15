---
name: k1ng-signal-builder
description: Generate deterministic Turbo-Grid signal JSONs (v2.0) for cTrader ingestion, including SL/TP levels, grid parameters, and persisting to output/signals/.
---

# K1NG Signal Builder Skill

Generate standardized, deterministic trading signals for the cTrader Turbo-Grid bot.

## When to Use

- After the Orchestrator has reached a consensus with confidence ≥ 75 and score ≥ 75 (BUY) or ≤ 25 (SELL)
- When `_save_signals_for_ctrader()` needs to emit a JSON file
- When manually constructing a signal for back-testing or dry-run

## Signal JSON Schema (v2.0)

Each signal is a single object inside an array (cTrader expects a JSON array):

```json
[
  {
    "signal_id": "btc_long_001",
    "action": "open",
    "instrument": "BTCUSD",
    "direction": "BUY",
    "entry_type": "limit",
    "entry_price": 76500,
    "grid_spacing_pct": 0.36,
    "max_levels": 12,
    "progression_factor": 1.20,
    "global_sl": 71000,
    "global_tp": 88000
  }
]
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `signal_id` | string | ✅ | Unique ID, e.g. `sig_20260511_143022` or `btc_long_001` |
| `action` | string | ✅ | Always `"open"` for new grid positions |
| `instrument` | string | ✅ | Asset code: `oil`, `gold`, `btc`, `eurusd` (mapped to broker symbol) |
| `direction` | string | ✅ | `"BUY"` or `"SELL"` |
| `entry_type` | string | ✅ | `"limit"` (grid uses limit orders) or `"market"` |
| `entry_price` | float | ✅ | Consensus median price from agents |
| `grid_spacing_pct` | float | ✅ | Distance between grid levels in % (default 0.36) |
| `max_levels` | int | ✅ | Maximum grid layers (default 12) |
| `progression_factor` | float | ✅ | Volume multiplier per level (default 1.20) |
| `global_sl` | float | ✅ | Hard stop-loss price (deterministic) |
| `global_tp` | float | ✅ | Hard take-profit price (deterministic) |

## Deterministic SL / TP Calculation

Use the volatility-adjusted method from `orchestrator.py::_build_turbo_signal_deterministic()`:

```python
avg_daily_range = entry_price * 0.02  # fallback if vola analysis fails

if direction == "BUY":
    sl = entry_price - avg_daily_range * 0.5
    tp1 = entry_price + avg_daily_range * 0.5
    tp2 = entry_price + avg_daily_range * 1.0
    tp3 = entry_price + avg_daily_range * 1.5
else:  # SELL
    sl = entry_price + avg_daily_range * 0.5
    tp1 = entry_price - avg_daily_range * 0.5
    tp2 = entry_price - avg_daily_range * 1.0
    tp3 = entry_price - avg_daily_range * 1.5
```

Round to 2 decimals (4 for `eurusd`).

## Grid Parameters (from `config.yaml`)

```yaml
turbo_grid:
  start_volume_lot: 0.01
  default_spacing_pct: 0.36
  progression_factor: 1.2
  max_levels: 15
  volatility_stop_pct: 5.0
  max_risk_pct: 1.5
  scale_out_pct: 50
  trailing_distance_pct: 1.0
```

These values are injected into the `grid_params` field when the signal is built programmatically.

## Validation Rules

1. **Confidence gate**: `avg_confidence >= 75` AND (`score >= 75` for BUY or `score <= 25` for SELL)
2. **Price plausibility**: entry_price must be inside reference ranges:
   - oil: 50 – 150
   - gold: 4000 – 5500
   - btc: 60000 – 100000
   - eurusd: 1.10 – 1.25
3. **Direction coherence**: `global_sl` must be *below* entry for BUY, *above* entry for SELL
4. **File naming**: `output/signals/k1ng_signal_{asset}.json`

## Copilot CLI Action Plan

When asked to build a signal:

1. Read `orchestrator.py` around `_build_turbo_signal_deterministic()` to verify the latest formula.
2. Read `config.yaml` under `turbo_grid:` to fetch current default parameters.
3. Compute SL/TP using the deterministic volatility method above.
4. Emit the JSON array with all required fields.
5. Save it to `output/signals/k1ng_signal_{asset}.json` (create directory if missing).
6. Confirm the file path and print a one-line summary: `Signal: {direction} {instrument} @ {entry_price} | SL {sl} | TP {tp}`.
