"""The Shadow base — capability-first, runs the 4-stage loop (spec section 2).

A Shadow is configured by *data* (capabilities, deployment_triggers, guardrails),
not by a hardcoded persona (Invariant 1). The base implements the shared loop:

    PERCEPTION -> MEMORY -> REASONING -> ACTION   (loop until goal met)

Subclasses override only where the spec defines specialized, deterministic
behaviour (e.g. Thresher's compression, Aegis's triage matrix). Everything else
runs the shared, model-backed Reasoning stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from monarch.llm import LLM
from shadow_os.memory import Memory
from shadow_os.task import RSIArtifact, ShadowResult, Task


@dataclass
class Reasoning:
    """Result of the Reasoning stage."""

    plan: str
    draft: str
    confidence: float
    goal_met: bool
    self_critique: str


class Shadow:
    """Base capability-runner. Configure via class attributes or __init__."""

    id: str = "shadow"
    tier: str = "Master"
    status: str = "CORE"
    capabilities: List[str] = []
    deployment_triggers: List[str] = []
    guardrails: List[str] = []
    # How this shadow specializes the Reasoning system prompt.
    reasoning_directive: str = (
        "Reason in full depth and produce a correct, complete answer."
    )

    def __init__(self, llm: LLM):
        self.llm = llm

    # --- Stage 1: Perception ----------------------------------------------

    def perceive(self, task: Task, incoming: str) -> str:
        """Normalize input; filter noise. ``incoming`` is the directive or an
        upstream shadow's artifact passed down the loadout sequence."""
        return incoming.strip()

    # --- Stage 2: Memory ---------------------------------------------------

    def remember(self, task: Task, memory: Memory) -> str:
        units = memory.recall_context(task.task_class)
        if not units:
            return ""
        return "Relevant prior context:\n" + "\n".join(f"- {u.text}" for u in units)

    # --- Stage 3: Reasoning ------------------------------------------------

    def _system_prompt(self) -> str:
        caps = "\n".join(f"- {c}" for c in self.capabilities)
        guards = "\n".join(f"- {g}" for g in self.guardrails) or "- (none)"
        return (
            f"You are the {self.id.title()} capability of Shadow OS ({self.tier}).\n"
            f"{self.reasoning_directive}\n\n"
            f"Your capabilities:\n{caps}\n\n"
            f"Guardrails (import the function, not the pathology):\n{guards}\n\n"
            "Method: taxonomy first; chain Claim -> Evidence -> Implication -> "
            "Kill condition; work the unasked third layer; deliver the delta. "
            "Self-critique before finalizing. Conclusions are provisional; "
            "confidence is earned, not performed."
        )

    def reason(self, task: Task, perception: str, recalled: str) -> Reasoning:
        user = f"Directive:\n{task.reconstructed_intent or perception}"
        if recalled:
            user += f"\n\n{recalled}"
        if perception and perception != task.reconstructed_intent:
            user += f"\n\nInput to work on:\n{perception}"
        draft = self.llm.complete(self._system_prompt(), user)
        critique = self._self_critique(draft)
        confidence = self._confidence(task, draft)
        return Reasoning(
            plan=f"{self.id}: apply {self.capabilities[0] if self.capabilities else 'capability'}",
            draft=draft,
            confidence=confidence,
            goal_met=True,  # base shadows resolve in one pass; loopers override
            self_critique=critique,
        )

    def _self_critique(self, draft: str) -> str:
        # Lightweight, deterministic self-check (mandatory before Action, section 2).
        flags = []
        if len(draft.strip()) < 20:
            flags.append("thin output")
        if "TODO" in draft or "??" in draft:
            flags.append("unresolved markers")
        return "; ".join(flags) if flags else "passes self-critique"

    def _confidence(self, task: Task, draft: str) -> float:
        # Confidence matched to evidence tier (spec section 2). Heuristic baseline:
        # longer, critique-clean drafts on System2 tasks score higher.
        base = 0.6 if draft.strip() else 0.0
        if "passes self-critique" in self._self_critique(draft):
            base += 0.2
        if task.gamma.value == "system2":
            base += 0.1
        return round(min(base, 0.95), 2)

    # --- Stage 4: Action ---------------------------------------------------

    def act(self, task: Task, reasoning: Reasoning) -> ShadowResult:
        rsi = RSIArtifact(
            shadow=self.id,
            delta=f"produced {task.task_class} artifact",
            failure_avoided="generic, ungrounded output",
            reuse_destination=f"tkl::{task.task_class}",
            verify_status="verified" if reasoning.goal_met else "unverified",
        )
        return ShadowResult(
            shadow=self.id,
            artifact=reasoning.draft,
            confidence=reasoning.confidence,
            goal_met=reasoning.goal_met,
            self_critique=reasoning.self_critique,
            rsi=rsi,
        )

    # --- The loop ----------------------------------------------------------

    def run(
        self,
        task: Task,
        memory: Memory,
        incoming: Optional[str] = None,
        max_iters: int = 3,
    ) -> ShadowResult:
        """Perception -> Memory -> Reasoning -> Action, looping until goal met."""
        perception = self.perceive(task, incoming or task.reconstructed_intent or task.raw_input)
        recalled = self.remember(task, memory)
        iterations = 0
        reasoning = self.reason(task, perception, recalled)
        iterations += 1
        while not reasoning.goal_met and iterations < max_iters:
            reasoning = self.reason(task, perception, recalled)
            iterations += 1
        result = self.act(task, reasoning)
        result.iterations = iterations
        return result
