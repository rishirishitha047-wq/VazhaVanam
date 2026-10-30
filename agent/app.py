"""VazhaVanam -- Climate Resilience Advisor for Tamil Nadu small farmers."""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time

from strands import Agent
from strands.hooks import BeforeNodeCallEvent, HookProvider, HookRegistry
from strands.models import BedrockModel
from strands.multiagent import GraphBuilder
from strands.session import FileSessionManager

from . import tools
from .plan import Answer, Critique

MODEL_ID    = os.environ.get("SHIP_MODEL", "us.amazon.nova-2-lite-v1:0")
REGION      = os.environ.get("AWS_REGION",  "us-east-1")
SESSION_DIR = os.environ.get("VAZHAVANAM_SESSIONS", os.path.expanduser("~/.vazhavanam-sessions"))

logging.getLogger("strands").setLevel(logging.CRITICAL)

RED_FLAGS = [
    "flood", "cyclone hit", "cyclone struck", "stranded", "swept away",
    "வெள்ளத்தில் சிக்கி", "புயல் தாக்கியது", "மூழ்கிவிட்டோம்",
    "pesticide poisoning", "chemical burn", "sprayed too much",
    "பூச்சிக்கொல்லி விஷம்", "மண்ணெண்ணெய் குடித்தேன்",
    "unconscious", "not breathing", "chest pain", "suicide", "kill myself",
    "மயக்கமாகி", "மூச்சு வரவில்லை",
]

HANDOFF = {
    "en": (
        "This is an emergency. Please call 1077 (Tamil Nadu Disaster Helpline, free, 24x7) "
        "or 108 (Ambulance) immediately. Move to higher ground or a government relief camp. "
        "For chemical/pesticide emergencies call 1800-180-1551 (KVK). "
        "This assistant will not answer emergency situations -- call the helpline now."
    ),
    "ta": (
        "இது அவசர நிலை. உடனே 1077 (தமிழ்நாடு பேரிடர் உதவி எண், இலவசம், 24x7) "
        "அல்லது 108 (ஆம்புலன்ஸ்) அழைக்கவும். அரசு நிவாரண முகாமிற்கு சென்று விடுங்கள். "
        "பூச்சிக்கொல்லி அவசரத்திற்கு 1800-180-1551 (KVK). "
        "இந்த உதவியாளர் அவசர நிலைக்கு பதில் சொல்லாது -- இப்போதே உதவி எண்ணை அழைக்கவும்."
    ),
}

PLANNER_PROMPT = """You are VazhaVanam, a Tamil Nadu climate advisor for small farmers.
Answer ONLY in {lang}. Tamil answers: Tamil script only, no English words except KVK and numbers.

Always call these tools in order:
1. lookup_guidance("cyclone flood drought water crop harvest paddy warning")
2. classify_situation with:
   - cyclone_alert = "none"|"watch"|"warning"|"hit"
     ("watch" = advance warning, yellow alert, "tomorrow", not yet arrived)
     ("warning" = orange/red alert, imminent or just arrived)
     ("hit" = already struck, active damage)
   - flood_alert = "none"|"forecast"|"active"|"emergency"
     ("forecast" = heavy rain expected; "active" = water entering/rising)
   - drought_level = "none"|"mild"|"moderate"|"severe"
   - reservoir_pct = extract from message, or -1
3. get_crop_advice(crop, stage_days, hazard) only if crop + days mentioned

Use classify_situation's risk_level as the answer's risk_level.
Only cite ids from the guidance_ids returned by any tool in this call.
Always include 1077 in the escalation field.
Never give pesticide dosage amounts or medical treatment.
Provide 3-5 action steps for ALL risk levels including normal.
"""

CRITIC_PROMPT = """Review this Tamil Nadu farmer advisory in {lang}.
Reply ok=false ONLY if:
1. Tamil answer contains English sentences (KVK, 1077, 108 are OK)
2. English answer contains Tamil script
3. escalation field is missing "1077"
4. steps list is empty (steps are required for all risk levels)
5. answer field is empty

Reply ok=true, problems=[] otherwise. Do NOT flag KVK as wrong language.
"""

# Simplified retry prompt when graph fails to produce structured output
RETRY_PROMPT = """You are VazhaVanam. Answer only in {lang}.
Call classify_situation first, then write a short advisory.
Include 1077 in escalation. Give 3 action steps.
Never give chemical dosage.
"""


class RedFlagGate(HookProvider):
    def __init__(self):
        self.tripped: list[str] = []

    def register_hooks(self, registry: HookRegistry, **_):
        registry.add_callback(BeforeNodeCallEvent, self._check)

    def _check(self, event: BeforeNodeCallEvent):
        text = str(event.invocation_state.get("user_text", "")).lower()
        hits = [p for p in RED_FLAGS if p in text]
        if hits:
            self.tripped = hits
            event.cancel_node = "red flag: " + ", ".join(hits)


def _model() -> BedrockModel:
    return BedrockModel(model_id=MODEL_ID, region_name=REGION, temperature=0.2)


def build_graph(lang: str, gate: RedFlagGate, session_id: str | None = None):
    sm_kwargs = {}
    if session_id:
        try:
            sm_kwargs["session_manager"] = FileSessionManager(SESSION_DIR)
        except Exception:
            pass

    planner = Agent(
        model=_model(), name="planner",
        system_prompt=PLANNER_PROMPT.format(lang=lang),
        tools=[tools.lookup_guidance, tools.classify_situation, tools.get_crop_advice],
        structured_output_model=Answer, callback_handler=None,
        **sm_kwargs,
    )
    critic = Agent(
        model=_model(), name="critic",
        system_prompt=CRITIC_PROMPT.format(lang=lang),
        structured_output_model=Critique, callback_handler=None,
    )

    def needs_revision(state) -> bool:
        r = state.results.get("critic")
        v = getattr(r.result, "structured_output", None) if r else None
        n = sum(1 for x in state.execution_order if x.node_id == "planner")
        if v is not None:
            label = "PASS" if v.ok else "REVISE -- " + "; ".join(v.problems)[:200]
            print(f"[critic] pass {n}: {label}", flush=True)
        return bool(v is not None and not v.ok and n < 2)

    b = GraphBuilder()
    b.add_node(planner, "planner")
    b.add_node(critic,  "critic")
    b.add_edge("planner", "critic")
    b.add_edge("critic", "planner", condition=needs_revision)
    b.set_entry_point("planner")
    b.set_max_node_executions(4)
    b.reset_on_revisit(True)
    b.set_hook_providers([gate])
    return b.build()


def _retry_direct(text: str, lang: str) -> Answer | None:
    """Direct single-agent retry when graph structured output fails."""
    try:
        a = Agent(
            model=_model(), name="planner_retry",
            system_prompt=RETRY_PROMPT.format(lang=lang),
            tools=[tools.lookup_guidance, tools.classify_situation, tools.get_crop_advice],
            structured_output_model=Answer, callback_handler=None,
        )
        result = a(f"Farmer ({lang}): {text}")
        return result.structured_output
    except Exception as e:
        print(f"[plan] retry failed: {e}", flush=True)
        return None


def run(case: dict) -> dict:
    t0   = time.time()
    lang = case.get("lang") or tools.language_of(case["text"])
    gate = RedFlagGate()
    meta = {"path": "agent", "passes": 0}
    sid  = case.get("session_id")

    try:
        res = build_graph(lang, gate, session_id=sid)(
            f"Farmer ({lang}): {case['text']}",
            invocation_state={"user_text": case["text"]},
        )
    except Exception as exc:
        if not gate.tripped:
            print(f"[plan] graph error: {exc}", flush=True)
        res = None

    if gate.tripped:
        print(f"[safety] RED FLAG ({', '.join(gate.tripped)}) -> HANDOFF, agents cancelled", flush=True)
        ans = Answer(
            language=lang, risk_level="emergency",
            answer=HANDOFF[lang], steps=[], water_action="", crop_action="",
            escalation=HANDOFF[lang], citations=[],
        )
        meta["path"] = "handoff"
    else:
        # Try to get structured output from graph result
        ans = None
        if res is not None:
            pr = res.results.get("planner")
            if pr is not None:
                ans = getattr(pr.result, "structured_output", None)

        if ans is None:
            # Graph failed to produce structured output -- retry directly
            print(f"[plan] retrying direct for lang={lang}", flush=True)
            ans = _retry_direct(case["text"], lang)

        if ans is None:
            # Final fallback -- never crashes, safe escalation
            print(f"[plan] WARNING: all retries failed, using safe fallback", flush=True)
            ans = Answer(
                language=lang, risk_level="watch",
                answer=(
                    "Please call KVK at 1800-180-1551 for agricultural advice, or 1077 for disaster emergencies."
                    if lang == "en" else
                    "விவசாய ஆலோசனைக்கு KVK 1800-180-1551 அல்லது அவசர நிலைக்கு 1077 அழைக்கவும்."
                ),
                steps=[], water_action="", crop_action="",
                escalation="Call 1077 for emergencies, KVK 1800-180-1551 for crop advice.",
                citations=[],
            )
            meta["path"] = "fallback"

        if meta["path"] == "agent" and res is not None:
            meta["passes"] = sum(1 for n in res.execution_order if n.node_id == "planner")

    meta["latency_ms"] = int((time.time() - t0) * 1000)
    meta["lang"]       = lang
    print(f"[plan] {meta['path']} | lang={lang} | {meta['latency_ms']} ms", flush=True)
    return {"plan": ans.model_dump(), "meta": meta}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m agent.app")
    ap.add_argument("text")
    ap.add_argument("--json",       action="store_true")
    ap.add_argument("--session-id", default=None)
    a = ap.parse_args(argv)
    out = run({"text": a.text, "session_id": a.session_id})
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        plan = out["plan"]
        print(f"\nRisk level: {plan['risk_level'].upper()}")
        print(f"\n{plan['answer']}")
        if plan["steps"]:
            print("\nSteps:")
            for i, s in enumerate(plan["steps"], 1):
                print(f"  {i}. {s}")
        if plan.get("water_action"): print(f"\nWater: {plan['water_action']}")
        if plan.get("crop_action"):  print(f"\nCrop:  {plan['crop_action']}")
        print(f"\nFor help: {plan['escalation']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())