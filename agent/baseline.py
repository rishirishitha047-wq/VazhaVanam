"""VazhaVanam baseline — one agent, one prompt, same model and guidance: the bar to beat.
No hook, no graph, no fixed thresholds, no sessions.
"""
import time

from strands import Agent

from . import tools
from .app import _model
from .plan import Answer


def run(case: dict) -> dict:
    t0   = time.time()
    lang = case.get("lang") or tools.language_of(case["text"])
    guidance_lines = "\n".join(f"{g['id']}: {g['text']}" for g in tools.guidance()["items"])
    lang_label = "Tamil (Tamil script)" if lang == "ta" else "English"

    a = Agent(
        model=_model(),
        callback_handler=None,
        structured_output_model=Answer,
        system_prompt=(
            f"You are a helpful farming and climate advisor for Tamil Nadu.\nFor pesticide or chemical questions, do not give dosage. Tell the farmer to contact KVK 1800-180-1551.\n"
            f"Answer in {lang_label}.\n"
            f"Only cite guidance ids from this list:\n{guidance_lines}\n"
            f"Always include 1077 in the escalation field for dangerous situations."
        ),
    )
    msg = f"Farmer ({lang}): {case['text']}"
    result = a(msg)
    ans = result.structured_output
    if ans is None:
        # retry once
        ans = a(msg).structured_output
    if ans is None:
        raise RuntimeError("baseline returned no structured answer")
    return {
        "plan": ans.model_dump(),
        "meta": {"path": "baseline", "latency_ms": int((time.time() - t0) * 1000)},
    }
