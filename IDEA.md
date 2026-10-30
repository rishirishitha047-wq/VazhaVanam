# IDEA.md — VazhaVanam: Climate Resilience Advisor for Tamil Nadu Rural Communities

## One-line pitch
A Tamil/English agent that turns real-time weather, crop stage and resource conditions into a safe, actionable
plan for small farmers, helping them survive floods, droughts and heat — before the damage happens.

## Who it helps
Small and marginal farmers (< 2 hectares) in flood-prone and drought-prone districts of Tamil Nadu
(Thanjavur, Tiruvarur, Nagapattinam, Cuddalore, Villupuram). Many use shared smartphones; primary language
is Tamil. Connectivity is low-bandwidth. They do not have agronomists on call.

## The real story (Step 1)
A paddy farmer in Nagapattinam receives a cyclone warning on his phone — in English, 14 paragraphs long.
He cannot act on it. His neighbour's entire crop is flooded because they did not know to harvest early or
move seedlings to high ground. The district helpline rings unanswered. The farmer's loss: ₹40,000 and three
months of work. The information existed; it never reached him in time, in his language, as a clear action.

## The decision that must NEVER be wrong
1. **Cyclone / flood emergency** → always hand off to Tamil Nadu SDMA (State Disaster Management Authority)
   and the 1077 Disaster Helpline. Code owns this. The model cannot override it.
2. **Crop chemical / pesticide dosage** → never advise; always escalate to the nearest Krishi Vigyan Kendra (KVK).
3. **Water scarcity alert thresholds** → fixed values in code (reservoir levels from WRD Tamil Nadu); model reads, cannot change.

## What will be measured
| Metric | Target |
|---|---|
| Emergencies correctly handed off | 100 % (agent), ≥ 80 % baseline |
| Plans with unsafe crop advice | 0 |
| Risk level correct (flood / drought / normal) | ≥ 90 % |
| Goal success (Strands Evals judge, 0–1) | ≥ 0.85 vs baseline ≤ 0.70 |

## Languages
Tamil (primary), English (secondary). All safety text and emergency numbers are hard-coded in both.

## Rubric scores (honest, pre-build)
| Quarter | Score | Reason |
|---|---|---|
| Social impact | 9 | Real underserved group; measurable crop loss / safety outcomes; Tamil-first |
| Technical execution | 8 | Graph + hook + tools + sessions; measurable safety gate |
| Communication | 7 | Story is clear; need good video from live Tamil run |
| Originality | 8 | Combines flood + drought + crop advisory; Tamil Strands agent; real WRD data |
| Buildable this week | 8 | Guidance JSON can be seeded from public sources; graph reuses starter spine |

## Argument against (Gate 2 judge)
- "Too similar to HeatSafe Shift" → HeatSafe is about outdoor workers + heat index. VazhaVanam is about
  farmers + multi-hazard climate risk (flood, drought, water scarcity). Different domain, different data,
  different escalation chain. The baseline gap should be larger because the climate advice space is more
  dangerous for a plain prompt.
- "Would a plain prompt do as well?" → No: the baseline has no hook, no fixed thresholds, no escalation
  gate. `ss measure` will prove the gap.
- "Is the impact measurable this week?" → Yes: labelled cases from public cyclone/drought scenarios, scored
  automatically by score.py. Field validation is a stretch goal.

## What is steelmanned
If Tamil-language structured crop + disaster guidance is in guidance.json, and the graph catches unsafe
advice reliably, this is a safety-critical demo that a plain prompt genuinely fails at.

## Distinct from other teams
Does not use the HeatSafe idea. Covers three climate hazards in one agent. Uses WRD Tamil Nadu water data
(no other known team uses this source).

## Not this week (stretch goals)
- Live weather API integration (IMD / Open-Meteo)
- SMS gateway for feature phones
- Real farmer field validation
- Voice (Nova Sonic has no Tamil)
