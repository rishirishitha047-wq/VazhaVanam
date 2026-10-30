# Demo Script — VazhaVanam (under 3 minutes)

## Before you record

1. Have a terminal open in the project folder
2. Confirm Bedrock works: `~/.strands-ship/bin/ss bedrock`
3. Set PYTHONIOENCODING=utf-8 so Tamil prints correctly
4. Keep results/MEASURE.md visible in a second pane

---

## Scene 1 — The problem (0:00–0:20)

Narrate (no commands):
> "A farmer in Nagapattinam gets a cyclone warning in English. He cannot act on it.
> VazhaVanam answers in Tamil — in under 10 seconds — with exactly what to do today."

---

## Scene 2 — Emergency hook (0:20–0:45)

Show the red-flag hook firing instantly (no model call):

```bash
python -m agent.app "வெள்ளத்தில் சிக்கி விட்டோம், வயல் முழுவதும் மூழ்கிவிட்டது"
```

Expected output (under 600ms):
```
[safety] RED FLAG (வெள்ளத்தில் சிக்கி) -> HANDOFF, agents cancelled
[plan] handoff | lang=ta | ~550 ms
Risk level: EMERGENCY
இது அவசர நிலை. உடனே 1077 ...
```

Point out:
- "RED FLAG" line = hook fired, no model was called
- Response in Tamil under 1 second
- 1077 is hard-coded in Python, the model cannot change it

---

## Scene 3 — Cyclone advisory in Tamil (0:45–1:30)

```bash
python -m agent.app "நாளை புயல் வரும் என்கிறார்கள், என் நெல் 85 நாள் ஆகிறது, என்ன செய்வது"
```

Expected output:
```
[critic] pass 1: PASS
[plan] agent | lang=ta | ~12000 ms
Risk level: WARNING
...Tamil advisory...
Steps:
  1. உடனடியாக நெல் அறுவடை செய்யவும்
  2. ...
```

Point out:
- Risk level WARNING (not emergency — cyclone watch, not yet hit)
- Planner–critic graph ran: critic passed on first try
- Steps are in Tamil — no English words

---

## Scene 4 — English drought advisory (1:30–2:00)

```bash
python -m agent.app "severe drought, reservoir at 10 percent, should I still plant paddy"
```

Expected output:
```
Risk level: WARNING
Do not plant new paddy this season...
Steps: ...
For help: Call KVK 1800-180-1551 ...1077...
```

Point out:
- Reservoir 10% → code threshold → WARNING (not watch)
- Correctly refuses to advise planting, gives alternative

---

## Scene 5 — Pesticide escalation (2:00–2:20)

```bash
python -m agent.app "my paddy has brown plant hopper, what pesticide should I spray"
```

Expected output:
- No chemical name or dosage in answer
- Escalates to KVK 1800-180-1551

Point out:
- The agent refuses to give pesticide advice — that is the correct behaviour
- Code-owned escalation, not a model decision

---

## Scene 6 — Measurement badge (2:20–2:50)

Show `results/MEASURE.md`:

```
| Metric | VazhaVanam | Baseline |
| Emergency recall | 100% | 100% |
| Unsafe advice | 0 | 1 |
| Risk level correct | 100% | 68% |
| Goal success | 0.987 | 0.963 |
```

Say:
> "These are real numbers from 31 human-labelled cases, measured by Strands Evals.
> The baseline is the same model — one prompt, no tools, no graph, no hook.
> The agent wins on every safety metric."

---

## Scene 7 — Close (2:50–3:00)

> "VazhaVanam — Tamil-first, safety-first climate guidance for the farmers who need it most."

---

## Recording command (when ready)

```bash
~/.strands-ship/bin/ss video
```

This records a live run of the agent and saves `results/demo.mp4`.