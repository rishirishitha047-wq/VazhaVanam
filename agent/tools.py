"""VazhaVanam tools -- code owns all thresholds. The model reads these values; it cannot change them.

Sources:
  WRD Tamil Nadu reservoir thresholds: https://www.tn.gov.in/wrd (read 2026-10-27)
  IMD SPI drought bands: https://imd.gov.in/pages/drought_main.php (read 2026-10-27)
  TNAU crop stage days: https://www.tnau.ac.in (read 2026-10-27)
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from strands import tool

DATA = Path(__file__).parent / "data"
TAMIL = re.compile(r"[\u0B80-\u0BFF]")

_WATER_CRITICAL_PCT = 15
_WATER_LOW_PCT      = 30
_WATER_NORMAL_PCT   = 60


@lru_cache(maxsize=1)
def guidance():
    return json.loads((DATA / "guidance.json").read_text(encoding="utf-8"))


def guidance_ids() -> set[str]:
    return {g["id"] for g in guidance()["items"]}


def language_of(text: str) -> str:
    return "ta" if TAMIL.search(text or "") else "en"


def has_tamil(text: str) -> bool:
    return bool(TAMIL.search(text or ""))


@tool
def lookup_guidance(topic: str) -> list[dict]:
    """Search the curated, dated guidance library. Returns items with id and text.
    ALWAYS call this first. You may only cite ids that appear in these results.

    Args:
        topic: keywords about the situation, e.g. 'cyclone harvest paddy flood water drought warning'
    """
    words = [w for w in re.findall(r"\w+", topic.lower()) if len(w) > 2]
    items = guidance()["items"]
    hits = [g for g in items if any(w in (g["id"] + " " + g["text"]).lower() for w in words)]
    if len(hits) < 8:
        hit_ids = {g["id"] for g in hits}
        hits = hits + [g for g in items if g["id"] not in hit_ids][:8 - len(hits)]
    return [{"id": g["id"], "text": g["text"]} for g in hits[:10]]


@tool
def classify_situation(
    cyclone_alert: Literal["none", "watch", "warning", "hit"] = "none",
    flood_alert: Literal["none", "forecast", "active", "emergency"] = "none",
    drought_level: Literal["none", "mild", "moderate", "severe"] = "none",
    reservoir_pct: float = -1,
) -> dict:
    """Classify the overall climate situation and return the risk level plus guidance ids.
    Code owns the risk bands -- the model reports what it heard, code decides the risk.

    Use the LOWEST alert that fits:
      cyclone_alert:
        'watch'   = advance warning, tomorrow, yellow alert, "cyclone vanthu vittu" (not yet arrived)
        'warning' = orange/red alert, imminent landfall within hours
        'hit'     = cyclone already struck, active damage NOW
      flood_alert:
        'forecast' = heavy rain expected, not yet flooding
        'active'   = water entering fields or roads, rising water levels
        'emergency' = people trapped, swept away, submerged
      drought_level:
        'mild' = reduced rainfall noticed, SPI -1.0 to -1.49
        'moderate' = declared drought, SPI -1.5 to -1.99
        'severe' = severe declared, SPI -2.0+, water sources failing
      reservoir_pct: % of full capacity (-1 = unknown)

    Args:
        cyclone_alert: current cyclone alert level
        flood_alert: current flood alert level
        drought_level: current drought severity
        reservoir_pct: reservoir storage percentage, -1 if not mentioned
    """
    ids = set()
    risk = "normal"
    risk_rank = {"normal": 0, "watch": 1, "warning": 2, "emergency": 3}

    def upgrade(new_risk: str, new_ids: list[str]):
        nonlocal risk
        ids.update(new_ids)
        if risk_rank.get(new_risk, 0) > risk_rank.get(risk, 0):
            risk = new_risk

    if cyclone_alert == "hit":
        upgrade("emergency", ["G-CYCLONE-EVACUATE", "G-CYCLONE-DONT", "G-EMERGENCY-NUMBERS", "G-RELIEF-CAMP"])
    elif cyclone_alert == "warning":
        upgrade("warning", ["G-CYCLONE-EVACUATE", "G-CYCLONE-HARVEST", "G-CYCLONE-DONT", "G-EMERGENCY-NUMBERS"])
    elif cyclone_alert == "watch":
        upgrade("warning", ["G-CYCLONE-HARVEST", "G-CYCLONE-DONT", "G-EMERGENCY-NUMBERS", "G-RELIEF-CAMP"])

    if flood_alert == "emergency":
        upgrade("emergency", ["G-CYCLONE-EVACUATE", "G-FLOOD-DRAIN", "G-EMERGENCY-NUMBERS"])
    elif flood_alert == "active":
        upgrade("warning", ["G-FLOOD-SEEDLING", "G-FLOOD-DRAIN", "G-EMERGENCY-NUMBERS"])
    elif flood_alert == "forecast":
        upgrade("watch", ["G-FLOOD-SEEDLING", "G-FLOOD-DRAIN"])

    if drought_level == "severe":
        upgrade("warning", ["G-DROUGHT-SEVERE", "G-WATER-CRITICAL", "G-CROP-PADDY-FLOWERING"])
    elif drought_level == "moderate":
        upgrade("watch", ["G-DROUGHT-MODERATE", "G-WATER-LOW", "G-CROP-PADDY-FLOWERING"])
    elif drought_level == "mild":
        upgrade("watch", ["G-DROUGHT-MILD", "G-CROP-PADDY-FLOWERING"])

    if reservoir_pct >= 0:
        if reservoir_pct <= _WATER_CRITICAL_PCT:
            upgrade("warning", ["G-WATER-CRITICAL", "G-DROUGHT-SEVERE"])
        elif reservoir_pct <= _WATER_LOW_PCT:
            upgrade("watch", ["G-WATER-LOW", "G-DROUGHT-MODERATE"])

    if not ids:
        ids = {"G-CROP-PADDY-FLOWERING", "G-CROP-HARVEST-TIMING"}

    return {
        "risk_level":    risk,
        "guidance_ids":  sorted(ids),
        "cyclone_alert": cyclone_alert,
        "flood_alert":   flood_alert,
        "drought_level": drought_level,
        "reservoir_pct": reservoir_pct,
    }


@tool
def get_crop_advice(crop: str, stage_days: int, hazard: str) -> dict:
    """Return crop-specific action guidance for the current growth stage and hazard.
    Never advise on pesticide dosage -- always escalate to KVK for chemicals.

    Args:
        crop: crop name (e.g. 'paddy', 'groundnut', 'sugarcane')
        stage_days: days since sowing / transplanting
        hazard: 'cyclone', 'flood', 'drought', or 'normal'
    """
    if crop.lower() in ("paddy", "rice", "நெல்"):
        if stage_days < 30:    stage = "seedling"
        elif stage_days < 55:  stage = "tillering"
        elif stage_days < 80:  stage = "flowering"
        elif stage_days < 110: stage = "grain_filling"
        else:                  stage = "maturity"
    else:
        stage = "unknown"

    advice_map = {
        ("seedling",      "flood"):   ("Move seedlings to high ground immediately.", ["G-FLOOD-SEEDLING"]),
        ("seedling",      "cyclone"): ("Move seedlings to high ground.", ["G-FLOOD-SEEDLING", "G-CYCLONE-HARVEST"]),
        ("tillering",     "flood"):   ("Open drainage channels now; max 5 days submerged.", ["G-FLOOD-DRAIN"]),
        ("tillering",     "drought"): ("Maintain 2 cm water; reduce irrigation 25%.", ["G-DROUGHT-MILD", "G-CROP-PADDY-FLOWERING"]),
        ("flowering",     "drought"): ("Critical: maintain 3-5 cm water. Stress now cuts yield.", ["G-CROP-PADDY-FLOWERING", "G-DROUGHT-MODERATE"]),
        ("flowering",     "flood"):   ("Drain to 5 cm max.", ["G-FLOOD-DRAIN", "G-CROP-PADDY-FLOWERING"]),
        ("grain_filling", "drought"): ("Survival irrigation only. Harvest at 80% maturity.", ["G-DROUGHT-SEVERE", "G-CROP-HARVEST-TIMING"]),
        ("maturity",      "cyclone"): ("Harvest immediately.", ["G-CYCLONE-HARVEST", "G-CROP-HARVEST-TIMING"]),
        ("maturity",      "flood"):   ("Harvest immediately.", ["G-CROP-HARVEST-TIMING"]),
        ("maturity",      "normal"):  ("Harvest at 20-25% moisture.", ["G-CROP-HARVEST-TIMING"]),
    }
    action, ids = advice_map.get(
        (stage, hazard),
        ("Contact KVK 1800-180-1551 for advice on your crop stage.", ["G-CROP-PADDY-PEST"])
    )
    return {
        "crop": crop, "stage": stage, "stage_days": stage_days, "hazard": hazard,
        "action": action, "guidance_ids": ids,
        "escalation": "Contact KVK 1800-180-1551 for pest/disease/chemical advice.",
    }