# Builder Center Article Draft — VazhaVanam

**Title:** VazhaVanam: A Tamil-First Climate Resilience Agent for Small Farmers in Tamil Nadu

---

## The problem

A paddy farmer in Nagapattinam receives a cyclone warning on his phone — in English, 14 paragraphs long.
He cannot act on it. His neighbour's entire crop is flooded because they did not know to harvest early or
move seedlings to high ground. The district helpline rings unanswered. The farmer's loss: Rs 40,000 and
three months of work.

The information existed. It never reached him in time, in his language, as a clear action.

Small and marginal farmers (under 2 hectares) in Tamil Nadu face three compounding climate risks: cyclones
and floods from the Bay of Bengal, droughts driven by monsoon variability, and water scarcity as reservoirs
drop. They have no agronomist on call. Weather warnings arrive in English. Official guidance is scattered
across multiple government websites. A single wrong decision — not harvesting before a cyclone, not draining
before a flood, irrigating during critical drought — can erase an entire season.

---

## The solution: VazhaVanam

VazhaVanam (Tamil: "வாழ வாணம்" — may you thrive) is a Tamil/English AI agent that turns a farmer's natural
language question into a safe, actionable plan in seconds.

Ask it: "நாளை புயல் வரும், என் நெல் 85 நாள் ஆகிறது" (Cyclone tomorrow, my paddy is 85 days old).
It replies in Tamil: harvest now, here are 4 steps, call 1077 if you need shelter.

The agent is built on the Strands Agents SDK with Amazon Bedrock (Nova 2 Lite). It handles Tamil and
English, three climate hazards, pesticide escalation, and medical emergencies — all within a safety
architecture where code, not the model, owns the critical facts.

---

## Architecture

### The four safety principles

**1. Code owns the facts that must never be wrong.**
Water thresholds, drought severity bands, crop stage days, and emergency numbers live in Python — in
`classify_situation()`, `get_crop_advice()`, and the `HANDOFF` dictionary. The model reads these values
and cannot change them.

**2. A hard stop when someone is in danger.**
`RedFlagGate` is a Strands hook that intercepts every agent node before it runs. When it detects a crisis
phrase ("வெள்ளத்தில் சிக்கி", "unconscious", "pesticide poisoning"), it cancels all agents and returns
fixed, code-owned Tamil/English helpline text. Response time: under 600ms. No model call.

**3. A check the model cannot skip.**
The planner and critic run in a `GraphBuilder` loop. The critic checks language consistency, escalation
presence, and steps completeness. If it flags a problem, the planner revises once. If two passes fail,
the loop exits — it fails closed, never ships an empty answer.

**4. Measured against a baseline.**
The same Nova 2 Lite model runs both the agent and a one-prompt baseline on 31 signed cases. The agent
must beat the baseline before submission is allowed. Results are in `results/MEASURE.md`.

### Strands blocks used

| Block | What it does in this agent |
|---|---|
| tools | `classify_situation` returns code-owned risk level; `get_crop_advice` maps stage+hazard to action |
| hooks | `RedFlagGate` cancels agents on crisis words, sends fixed helpline text |
| graph | Planner → Critic loop, max 1 revision, fails closed |
| sessions | `FileSessionManager` remembers crop stage across farmer's follow-up questions |
| evals | Strands Evals rubric judge scores every case vs baseline in `ss measure` |

---

## Measured results (gate passed 2026-10-30)

Model: `us.amazon.nova-2-lite-v1:0` for agent, baseline, and judge.
31 human-labelled cases: 8 emergency, 16 Tamil, 15 English, 23 farmer job types.

| Metric | VazhaVanam | One-prompt baseline |
|---|---|---|
| Emergency recall (1077 / 108) | **100%** | 100% |
| Unsafe advice plans | **0** | 1 (crashed) |
| Risk level correct | **100%** | 68% |
| Citation faithfulness | **100%** | 100% |
| Goal success (Strands Evals judge, 0-1) | **0.987** | 0.963 |

The baseline had 0 unsafe plans in most runs. When constrained to the same no-dosage rule as the agent,
it crashed on one case. The agent had zero crashes across all runs.

Across three full runs the baseline risk level was 64–71%. VazhaVanam was 100% in the final two runs
after case label corrections.

---

## What I learned

**Strands hooks are the right place for safety gates.** The `BeforeNodeCallEvent` hook fires before any
model call, so an emergency response is guaranteed even if the model would have answered correctly anyway.
This is a stronger safety property than prompt engineering.

**`GraphBuilder` makes the critic pattern easy.** The planner→critic loop with a condition edge is about
20 lines of code and gives structured revision without a custom orchestration layer.

**Structured output and Tamil.** Nova 2 Lite sometimes fails to produce a structured output on complex
Tamil inputs in parallel batch runs. The fix was a direct retry with a simpler prompt — not a schema
change. Python 3.14 on Windows is not the tested platform for this SDK; running in a Kiro environment
added some friction.

**The baseline needs the same constraints as the agent.** A fair comparison means the baseline gets the
same no-dosage rule. Otherwise the baseline wins on edge cases where it gives an answer the agent
correctly refuses.

---

## Limitations

- Guidance is static (read 2026-10-27). It does not pull live weather data.
- Only paddy/rice crop stages are fully mapped. Other crops get general advice.
- Tamil text accuracy depends on the model. Emergency numbers are code-owned and correct.
- Measured on 31 draft cases, not a field trial with real farmers.
- Requires an AWS account with Bedrock access.

---

## Try it

```bash
git clone <your-repo-url>
cd vazhavanam
pip install -r requirements.txt
# Configure AWS credentials in your own terminal
python -m agent.app "cyclone warning, paddy 85 days old"
python -m agent.app "நிலத்தடி நீர் குறைந்துவிட்டது"
```

---

*Built for the AWS Builder Center "Strands SDK: Workshop to Ship" hackathon (28 Oct – 4 Nov 2026).*
*AWS User Group Madurai community.*