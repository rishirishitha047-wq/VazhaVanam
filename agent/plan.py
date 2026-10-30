"""VazhaVanam — structured output models for the climate resilience agent."""
from typing import Literal

from pydantic import BaseModel, Field


class Answer(BaseModel):
    language: Literal["en", "ta"]
    risk_level: Literal["normal", "watch", "warning", "emergency"] = Field(
        description="Overall climate risk level for the farmer right now"
    )
    answer: str = Field(description="Main advisory in the user's language — plain sentences, no jargon")
    steps: list[str] = Field(default_factory=list, description="Ordered action steps the farmer should take today")
    water_action: str = Field(
        default="",
        description="Specific water management instruction if water scarcity or flood is relevant"
    )
    crop_action: str = Field(
        default="",
        description="Specific crop action (harvest timing, drainage, irrigation) based on crop stage"
    )
    escalation: str = Field(
        description="When and who to contact for human help — always include 1077 for emergencies"
    )
    citations: list[str] = Field(description="Guidance ids returned by lookup_guidance that support this answer")


class Critique(BaseModel):
    ok: bool
    problems: list[str] = Field(default_factory=list)
