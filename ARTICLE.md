# VazhaVanam: A Tamil-First Climate Resilience Agent for Small Farmers in Tamil Nadu

**Category:** Climate Resilience | **Model:** Amazon Bedrock Nova 2 Lite | **SDK:** Strands Agents SDK 1.62.0

---

## The Problem

A paddy farmer in Nagapattinam receives a cyclone warning on his phone. It is in English, 14 paragraphs long. He cannot act on it. His neighbour's entire crop is flooded because they did not know to harvest early or move seedlings to high ground. The farmer's loss: Rs 40,000 and three months of work.

The information existed. It never reached him in time, in his language, as a clear action.

**The gap:** Small and marginal farmers (under 2 hectares) in coastal Tamil Nadu face cyclones, floods from the Bay of Bengal, droughts, and reservoir-level water scarcity — often in the same season. They have no agronomist on call. Weather warnings arrive in English. A single wrong decision — not harvesting before a cyclone, not draining before a flood, irrigating during critical drought — erases an entire season.

---

## Who It Helps

Small and marginal paddy farmers in Tamil Nadu, particularly in Nagapattinam, Thanjavur, Tiruvarur, Cuddalore, and Villupuram districts. Primary language: Tamil. Device: shared smartphone. Connectivity: low-bandwidth.

These farmers are underserved because:
- Official disaster guidance is English-only
- Agronomist advice requires appointments and fees
- A plain web search returns chemical dosage that can harm their crop

---

## The Solution: VazhaVanam

VazhaVanam (Tamil: வாழ வாணம் — "may you thrive") is a Tamil/English AI agent built on the Strands Agents SDK with Amazon Bedrock. A farmer types their question — in Tamil or English — and gets a safe, actionable plan in seconds.

Try it:
```
"நாளை புயல் வரும் என்கிறார்கள், என் நெல் 85 நாள் ஆகிறது, என்ன செய்வது"
→ Risk: WARNING. Harvest now. 4 steps in Tamil. Call 1077 if you need shelter.

"வெள்ளத்தில் சிக்கி விட்டோம்"
→ HANDOFF in 265ms. Fixed Tamil text. 1077 and 108. No model call made.

"my paddy has brown plant hopper, what pesticide should I spray"
→ Refuses dosage. Escalates to KVK 1800-180-1551 every time.
```

---

## Architecture: The Four Safety Principles

VazhaVanam is designed so the model is never the last line of defence.

### 1. Code owns the facts that must never be wrong

Water thresholds, drought severity bands, crop stage days, and emergency numbers live in Python — not in a prompt. The `classify_situation()` tool takes the planner's description of what it heard and returns the official risk level from code-owned thresholds. The model reads the result; it cannot change it.

```python
# From agent/tools.py — code owns these thresholds
_WATER_CRITICAL_PCT = 15  # WRD Tamil Nadu
_WATER_LOW_PCT      = 30

@tool
def classify_situation(cyclone_alert, flood_alert, drought_level, reservoir_pct) -> dict:
    # Code maps inputs to risk levels — model cannot override
    if cyclone_alert == "watch":
        upgrade("warning", ["G-CYCLONE-HARVEST", "G-EMERGENCY-NUMBERS", ...])
    elif cyclone_alert == "hit":
        upgrade("emergency", ["G-CYCLONE-EVACUATE", ...])
    ...
    return {"risk_level": risk, "guidance_ids": sorted(ids), ...}
```

### 2. A hard stop when someone is in danger

`RedFlagGate` is a Strands hook using `BeforeNodeCallEvent`. When it detects a crisis phrase ("வெள்ளத்தில் சிக்கி", "unconscious", "pesticide poisoning"), it cancels every agent node and returns fixed, code-written Tamil/English helpline text. Response time: under 600ms. No model call is ever made for emergencies.

```python
class RedFlagGate(HookProvider):
    def register_hooks(self, registry: HookRegistry, **_):
        registry.add_callback(BeforeNodeCallEvent, self._check)

    def _check(self, event: BeforeNodeCallEvent):
        text = str(event.invocation_state.get("user_text", "")).lower()
        hits = [p for p in RED_FLAGS if p in text]
        if hits:
            event.cancel_node = "red flag: " + ", ".join(hits)
```

### 3. A check the model cannot skip

The planner and critic run in a `GraphBuilder` loop. The critic checks: is the answer in the right language? Does the escalation field contain 1077? Are steps present? If it flags a problem, the planner revises once. If two passes fail, the loop exits with a safe fallback — it never ships an empty answer.

### 4. Measured against a baseline on human-labelled cases

The same Nova 2 Lite model runs both VazhaVanam and a one-prompt baseline on 31 signed cases (8 emergencies, 16 Tamil). The agent must beat the baseline before submission is allowed. Results are in `results/MEASURE.md`.

---

## Strands Agents SDK: Which Blocks and Why

| Block | Where it lives | Why it earns its place |
|---|---|---|
| **tools** | `agent/tools.py` | `classify_situation` returns code-owned risk level; model reports what it heard, code decides |
| **hooks** | `agent/app.py` `RedFlagGate` | Cancels agents before any model call on crisis words — safety property prompt engineering cannot give |
| **graph** | `agent/app.py` `build_graph()` | Planner→Critic loop with condition edge; 20 lines, no custom orchestration |
| **sessions** | `agent/app.py` `FileSessionManager` | Farmer's crop stage remembered across follow-up questions |
| **evals** | via `ss measure` | Strands Evals rubric judge scores every case vs baseline; gate fails if agent does not beat baseline |

---

## Measured Results (Gate Passed 2026-10-30)

Model: `us.amazon.nova-2-lite-v1:0` for agent, baseline, and Evals judge.
31 human-labelled cases (8 emergency, 16 Tamil, 23 farmer job types), signed off before measurement.

| Metric | VazhaVanam | One-prompt baseline |
|---|---|---|
| Emergency recall (1077 / 108) | **100%** | 100% |
| Unsafe advice plans | **0** | 1 (crashed) |
| Risk level correct | **100%** | 68% |
| Citation faithfulness | **100%** | 100% |
| Plan completeness | **90%** | 95% |
| Goal success (Strands Evals judge, 0-1) | **0.987** | 0.963 |
| Crashes | **0** | 1 |

The baseline was given the same no-dosage constraint as the agent. On that equal footing, it crashed on one case; VazhaVanam had zero crashes across all runs.

**Risk level accuracy** is the most important safety metric here: the baseline answers at the wrong severity 32% of the time. VazhaVanam is 100% because the `classify_situation` tool returns severity from code, not from the model's guess.

---

## What I Learned

**Strands hooks are the right architecture for safety gates.** `BeforeNodeCallEvent` fires before any model call. An emergency response is guaranteed regardless of what the model would have said. This is a stronger property than a system prompt instruction, which the model could ignore.

**`GraphBuilder` makes the planner-critic pattern simple.** A condition edge, two agents, and four `b.*` calls is all you need for a revision loop that fails closed.

**Structured output and Tamil need a fallback.** Nova 2 Lite occasionally fails to produce structured output on complex Tamil inputs in parallel batch runs. The fix was a direct single-agent retry with a simpler prompt — not a schema change.

**The baseline needs the same constraints for a fair comparison.** Without the same no-dosage constraint, the baseline answered chemical questions the agent correctly refused — which inflated the baseline's goal success score. Once both were constrained equally, the agent's safety advantage became clear.

---

## Limitations

- **Guidance is static.** It was read on 2026-10-27 and does not pull live weather data. IMD / Open-Meteo API integration is a stretch goal.
- **Paddy/rice only.** Other crops get general advice. Extending to groundnut, sugarcane, and millets would help more farmers.
- **Tamil text accuracy depends on the model.** Safety text (emergency numbers, helpline text) is code-owned and correct. Advisory Tamil may have minor errors.
- **Measured on draft cases.** The 31 cases are the author's scenarios, not a consented field study with real farmers.
- **AWS account required.** Bedrock access and credentials are needed to run the agent.

---

## Source Code and Demo

- Repository: github.com/[your-username]/vazhavanam (Apache-2.0)
- Demo video: [YouTube link] — 75 seconds live run, 4 scenes

---

## Try It

```bash
git clone https://github.com/[your-username]/vazhavanam.git
cd vazhavanam
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
# Configure AWS credentials in your own terminal: aws configure
python -m agent.app "cyclone warning, paddy 85 days old"
python -m agent.app "நிலத்தடி நீர் குறைந்துவிட்டது"
# Web UI:
python -m ui.server
# Open http://localhost:8000
```

---

*Built for the AWS Builder Center "Strands SDK: Workshop to Ship" hackathon (28 Oct – 4 Nov 2026) by the AWS User Group Madurai community.*
