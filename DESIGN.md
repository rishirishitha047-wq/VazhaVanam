# DESIGN.md — VazhaVanam: Climate Resilience Advisor

## The decision that must never be wrong
| Decision | Owner | Source |
|---|---|---|
| Cyclone / flood emergency → hand off to 1077 | `RedFlagGate` hook (code) | Tamil Nadu SDMA |
| Water reservoir alert level | `get_water_status` tool (fixed thresholds in Python) | WRD Tamil Nadu public bulletins |
| Drought severity band | `get_risk_level` tool (fixed IMD SPI thresholds) | IMD Drought Monitor definitions |
| Pesticide / chemical dosage → always escalate | `RED_FLAGS` list + `HANDOFF` text (code) | KVK escalation policy |

## Flow
```
User message (Tamil / English)
        │
        ▼
RedFlagGate hook ──── crisis words? ──── YES ──► fixed HANDOFF text (1077 / SDMA) ◄─ code only
        │ NO
        ▼
  Planner agent
  (calls tools: get_risk_level, lookup_guidance, get_water_status, get_crop_advice)
        │
        ▼
  Critic agent  ──── problems? ──── YES (max 2 revisions) ──► Planner again
        │ NO
        ▼
   Structured Answer (language, answer, steps, escalation, citations)
        │
        ▼
  Session saved (FileSessionManager — farmer remembers last crop stage)
        │
        ▼
      Output
```

## Strands blocks used

| Block | File | Job | Rubric quarter |
|---|---|---|---|
| `tools` | `agent/tools.py` | `get_risk_level`, `get_water_status`, `get_crop_advice`, `lookup_guidance` — code owns all thresholds | Technical execution |
| `hooks` | `agent/app.py` `RedFlagGate` | Stops agents on crisis words; sends fixed Tamil/English helpline text | Social impact + Technical |
| `graph` | `agent/app.py` `build_graph()` | Planner → Critic loop; fail-closed after 2 revisions | Technical + Originality |
| `sessions` | `agent/app.py` | `FileSessionManager` — farmer's crop stage remembered across calls | Originality |
| `evals` | `ship_kit/` via `ss measure` | Strands Evals rubric judge scores every case vs baseline | Technical execution |

## AWS services used

| Service | Job |
|---|---|
| Amazon Bedrock (Nova 2 Lite) | Planner and Critic agents |
| Amazon Translate | Tamil ↔ English for guidance lookup when language is Tamil |

## What is measured

Cases in `cases.jsonl` cover:
- 8 emergency cases (cyclone warning, flood onset, chemical poisoning scare) → must hand off
- 10 normal Tamil advisory cases (crop stage, water check, drought advice)
- 8 normal English advisory cases
- 5 edge cases (mixed Tamil/English, ambiguous risk)

Metrics computed by `agent/score.py`:
- `escalated`: emergency case correctly handed off
- `risk_correct`: risk level matches label
- `complete`: all answer fields present and in correct language
- `citations_valid`: only cites ids from guidance.json
- `unsafe`: any model-written advice on pesticide dose or emergency action

Baseline: `agent/baseline.py` — same model, single prompt, no hook, no graph, no fixed thresholds.

## Rubric sanity check (post-design)
| Quarter | Score | Change from IDEA.md |
|---|---|---|
| Social impact | 9 | Unchanged |
| Technical execution | 9 | +1: graph + hook + sessions + evals all pulling weight |
| Communication | 7 | Unchanged — depends on video |
| Originality | 9 | +1: Tamil sessions + multi-hazard in one graph is novel |
| Buildable this week | 8 | Unchanged |

## Beyond the workshop
A plain swarm hands off to specialists. VazhaVanam adds a safety gate that code owns, a critic that
catches unsafe crop advice before it reaches the farmer, and a session layer that remembers their crop
stage — so the second message is smarter than the first. None of that is in the workshop lessons.

## Out of scope this week
- Live IMD / Open-Meteo API calls (guidance.json uses static scenarios)
- SMS delivery for feature phones
- Voice (Nova Sonic has no Tamil; Amazon Transcribe ta-IN is a stretch goal)
