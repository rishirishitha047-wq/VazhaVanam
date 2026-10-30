# VazhaVanam — Climate Resilience Advisor for Tamil Nadu Rural Communities

A Tamil/English AI agent that turns weather alerts, crop stage, and water conditions into safe,
actionable guidance for small farmers in Tamil Nadu. Built with the
[Strands Agents SDK](https://strandsagents.com) on Amazon Bedrock for the
AWS Builder Center "Strands SDK: Workshop to Ship" hackathon.

---

## What it does

| Situation | What the agent does |
|---|---|
| Cyclone watch / warning | Advises on early harvest, seedling protection, evacuation |
| Flood forecast or active | Drainage timing, seedling safety, crop-stage-specific action |
| Drought (mild / moderate / severe) | Irrigation reduction schedule, reservoir-level guidance |
| Water scarcity | Reservoir threshold check, survival irrigation advice |
| Pest / chemical question | Refuses dosage — escalates to KVK 1800-180-1551 every time |
| Crisis phrase detected | Hook fires instantly, sends fixed Tamil/English helpline text (1077 / 108) |

The model never writes emergency numbers or safety thresholds — code owns them and the model reads them.

---

## Architecture

```
User message (Tamil or English)
        |
        v
RedFlagGate hook -----> crisis? -----> YES --> fixed HANDOFF text (1077 / 108) [code only]
        | NO
        v
   Planner agent
   classify_situation() -- risk band from code thresholds
   lookup_guidance()    -- curated, dated guidance library
   get_crop_advice()    -- TNAU stage + hazard lookup
        |
        v
   Critic agent  -- language, escalation, steps check
        |                              |
       PASS                        REVISE (max 1 retry)
        |
        v
  Structured Answer (language, risk_level, answer, steps,
                     water_action, crop_action, escalation, citations)
        |
        v
  FileSessionManager -- farmer's crop stage remembered across calls
```

**Strands blocks used:** `tools` · `hooks` · `graph` · `sessions` · `evals`

**AWS services:** Amazon Bedrock (Nova 2 Lite) · Amazon Translate (optional Tamil fallback)

---

## Measured results (gate passed 2026-10-30)

| Metric | VazhaVanam | Single-prompt baseline |
|---|---|---|
| Emergency recall (1077 / 108) | **100%** | 100% |
| Unsafe advice plans | **0** | 1 |
| Risk level correct | **100%** | 68% |
| Citation faithfulness | **100%** | 100% |
| Goal success (Strands Evals judge) | **0.987** | 0.963 |

Model: `us.amazon.nova-2-lite-v1:0`. 31 signed cases (8 emergency, 16 Tamil, 23 job types).
Full results: `results/MEASURE.md`.

---

## Requirements

- Python 3.10–3.14
- AWS account with Amazon Bedrock (Nova Lite enabled in `us-east-1`)
- AWS credentials configured (`aws configure` or `aws sso login`)

---

## Quick start

### Option A — with the strands-ship Kiro Power (recommended)

```
# In an empty folder, say in Kiro chat:
set up strands ship
```

### Option B — run directly

```bash
# 1. Clone and create a virtual environment
git clone <your-repo-url>
cd vazhavanam
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure AWS (run in your own terminal — never paste keys in chat)
aws configure
# Enter: Access Key ID, Secret Access Key, region us-east-1, format json

# 4. Run the agent
python -m agent.app "cyclone warning in Nagapattinam, my paddy is 85 days old"
python -m agent.app "நிலத்தடி நீர் குறைந்துவிட்டது, என்ன செய்வது"
```

### Environment variables (optional overrides)

Copy `.env.example` to `.env` and set values there, or export in your terminal:

```bash
export SHIP_MODEL=us.amazon.nova-2-lite-v1:0   # default
export AWS_REGION=us-east-1                     # default
export VAZHAVANAM_SESSIONS=~/.vazhavanam-sessions
```

---

## Running tests and measurement

```bash
# Check cases are valid and signed
~/.strands-ship/bin/ss cases check

# Run full agent vs baseline measurement (takes ~10 min for 31 cases)
~/.strands-ship/bin/ss measure

# Results written to results/MEASURE.md
```

---

## Project structure

```
agent/
  app.py          Main agent: RedFlagGate hook + planner->critic graph + sessions
  tools.py        4 tools — code owns all thresholds (WRD, IMD, TNAU)
  plan.py         Structured output schema (Answer, Critique)
  score.py        Deterministic scorer for measurement
  baseline.py     Single-prompt baseline to beat
  data/
    guidance.json Curated, dated guidance library (15 items, 6 sources)
cases.jsonl       31 human-labelled and signed test cases
results/
  MEASURE.md      Latest measurement results (gate status)
IDEA.md           Agent idea, users, problem, scores
DESIGN.md         Block choices, flow, what is measured
FAILURES.md       Failure log
```

---

## Limitations

- Guidance is from public sources read on 2026-10-27. It does not update automatically.
- Live weather data (IMD / Open-Meteo API) is not integrated. All scenarios are scenario-based.
- Nova Sonic does not support Tamil. Voice input is not available.
- Model-generated Tamil may have errors. Safety text (emergency numbers, thresholds) is code-owned.
- Measured improvement is on labelled draft cases, not a consented field trial.
- The agent covers paddy/rice crops in detail. Other crops get general guidance.

---

## Sources

| ID | Source |
|---|---|
| TN-SDMA | Tamil Nadu State Disaster Management Authority — Cyclone/Flood Preparedness Guidelines |
| IMD-DROUGHT | India Meteorological Department — Drought Monitor SPI definitions |
| WRD-TN | Water Resources Department Tamil Nadu — Reservoir Level Bulletin |
| KVK-TN | Krishi Vigyan Kendra Tamil Nadu — Crop Advisory |
| TNAU | Tamil Nadu Agricultural University — Integrated Crop Management Guidelines 2025 |
| NDMA | National Disaster Management Authority — Cyclone Do's and Don'ts |

---

## License

Apache-2.0. See `LICENSE`.