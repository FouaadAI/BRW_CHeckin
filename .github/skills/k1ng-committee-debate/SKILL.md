---
name: k1ng-committee-debate
description: War-Room debate protocol for K1NG. Triggers when agent score spread exceeds 30 points or when war_room_active flag is set.
---

# K1NG Committee Debate Skill

Structured adversarial and iterative debate protocol to resolve high-disagreement scenarios among the six K1NG agents.

## When to Activate

- **Score Spread > 30**: For any asset, the highest agent score minus the lowest agent score exceeds 30 points
- **War Room Flag**: `war_room_state.is_war_room_active()` returns `True`
- **Low Confidence Divergence**: Consensus confidence < 60 with polarized scores

## Debate Modes

### Mode A – Adversarial Debate (Default)

Used when `war_room_active == False` but scores diverge.

**Flow:**
1. **Round 1**: Each agent produces initial scores + reasoning (already done in `run_analysis_cycle`)
2. **Critique Phase**: Each agent critiques the 2 most divergent peers
   - Input: `prompts/agent_critique.md`
   - Each agent receives:
     - Its own original scores & reasoning
     - The top-2 most divergent peer results (by absolute score difference)
   - Output: Updated scores JSON
3. **Meta-Debater Phase**: A meta-debater synthesizes all critiques
   - Input: `prompts/meta_debater.md`
   - Receives `initial_results`, `critique_results`, and historical `accuracies`
   - Output: Final consensus JSON with `consensus`, `signals`, `current_prices`, `debate_summary`

### Mode B – War Room Iterative Debate

Used when `war_room_active == True`.

**Flow:**
1. **Round 1**: Same as Mode A – initial agent results
2. **Round 2 – Re-evaluation**: Each agent reconsiders its scores after seeing all other agents' results
   - Input: `prompts/war_room_agent.md`
   - Each agent receives:
     - Its own original scores & reasoning
     - Summary of all other agents (scores + reasoning truncated to 700 chars)
   - Output: Updated JSON
3. **No Meta-Debater**: The Orchestrator directly computes consensus from Round-2 results

## Consensus Calculation

### Weighted Consensus (Recommended)

```python
weight = confidence × (0.5 + 0.5 × accuracy)
```

Where `accuracy` comes from `db_manager.get_agent_accuracy(agent_name, asset)`.

### Simple Fallback

Median of all agent scores per asset (unweighted).

## Output Format

The debate must return a JSON object with these keys:

```json
{
  "consensus": {
    "oil": 62,
    "gold": 78,
    "btc": 45,
    "eurusd": 55
  },
  "signals": {
    "gold": {
      "direction": "BUY",
      "avg_confidence": 82
    }
  },
  "current_prices": {
    "oil": 74.35,
    "gold": 4234.50,
    "btc": 76500.00,
    "eurusd": 1.1850
  },
  "debate_summary": "Gold consensus emerged from physical supply tightness and smart-money accumulation. BTC disagreement remains high due to on-chain outflows vs. ETF inflows."
}
```

### Hard Validation Gates (Orchestrator)

After debate, the Orchestrator filters signals:
- `avg_confidence >= 75`
- `score >= 75` for BUY OR `score <= 25` for SELL
- Otherwise → direction forced to `"NEUTRAL"`

## Score Spread Detection

```python
def _has_high_disagreement(agent_results, asset, threshold=30):
    scores = [r['scores'].get(asset, 50) for r in agent_results if 'scores' in r]
    return max(scores) - min(scores) > threshold if len(scores) >= 2 else False
```

## Prompt Files

| Prompt | Purpose |
|--------|---------|
| `prompts/agent_critique.md` | Template for adversarial critique |
| `prompts/meta_debater.md` | Meta-debater synthesis prompt |
| `prompts/war_room_agent.md` | Re-evaluation prompt for War Room Round 2 |
| `prompts/orchestrator.md` | Fallback debate moderator prompt |

## Copilot CLI Action Plan

When asked to run or debug a debate:

1. Check `war_room_state.py` to see if the flag is active.
2. Read the latest agent results from `output/` or debug logs.
3. Calculate score spreads per asset (`max - min`).
4. If any spread > 30, activate this skill and:
   - Read `prompts/agent_critique.md` and `prompts/meta_debater.md`
   - Verify the critique loop in `orchestrator.py::_run_adversarial_debate()`
5. If War Room is active, read `prompts/war_room_agent.md` and verify `_run_war_room_debate()`.
6. Ensure the final debate JSON contains all required keys (`consensus`, `signals`, `current_prices`, `debate_summary`).
7. Run `python main.py --once` and inspect the debate summary in the generated report.
