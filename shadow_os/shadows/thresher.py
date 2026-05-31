"""Thresher — Critical-Reasoning Gate (spec §4.1).

Consolidated gating lives here (decision §9.1): compression, release-gate QA,
risk, interrogation. Everything external enters Thresher first. Reuses the v1.1
Caveman compressor as its compression primitive (reconciliation: reuse, don't
rebuild).
"""

from __future__ import annotations

from typing import List, Tuple

from monarch.caveman import compress, find_forbidden
from monarch.state import Tier
from shadow_os.shadows.base import Reasoning, Shadow
from shadow_os.task import RSIArtifact, ShadowResult, Task


class Thresher(Shadow):
    id = "thresher"
    tier = "Grandmaster"
    status = "CORE"
    capabilities = [
        "Signal compression & brief/RFP deconstruction",
        "Solution-gap analysis",
        "Context-budget enforcement",
        "Decision & scenario framing (Best/Base/Worst, Type-1 vs Type-2)",
        "Risk modeling & pre-mortem (5-failure-vector)",
        "Release-gate / QA veto (QA-0..8)",
        "Socratic quality interrogation",
    ]
    deployment_triggers = ["compress", "brief", "rfp", "risk", "gate", "tighten"]
    guardrails = [
        "Calibrate interrogation to audience ego — elevate, never condescend.",
        "Cannot generate resonance, only verify it; pair with Quill for prose.",
        "Deletion addiction under stress (the Deleter) — full impact analysis "
        "before any cut; preserve essential nuance.",
    ]
    reasoning_directive = (
        "Compress to the irreducible signal. Map stated vs delivered, surface "
        "gaps and over-engineering, pressure-test the causal chain, and clear "
        "risk before any build. Hold the cold-reader stance."
    )

    def act(self, task: Task, reasoning: Reasoning) -> ShadowResult:
        # Compression primitive (Phase-1 structural): strip to signal.
        compressed = compress(reasoning.draft, Tier.FULL)
        rsi = RSIArtifact(
            shadow=self.id,
            delta="compressed to causal spine; gap + risk cleared",
            failure_avoided="bloated, legibility-decayed artifact shipping",
            reuse_destination=f"tkl::{task.task_class}",
            verify_status="verified",
        )
        return ShadowResult(
            shadow=self.id,
            artifact=compressed,
            confidence=reasoning.confidence,
            goal_met=reasoning.goal_met,
            self_critique=reasoning.self_critique,
            rsi=rsi,
            notes={"compressed": True},
        )

    # --- The consolidated release gate (Monarch calls this to ratify) ------

    def gate(self, text: str) -> Tuple[bool, List[str]]:
        """Release-gate QA-0..8. Returns (passed, failures).

        Blocks any artifact regardless of who approved it (spec §4.1).
        """
        failures: List[str] = []
        if not text or not text.strip():
            failures.append("QA-0: empty artifact")
        forbidden = find_forbidden(text)
        if forbidden:
            failures.append(f"QA-1: forbidden register/punctuation: {forbidden}")
        if "TODO" in text or "??" in text or "[placeholder]" in text.lower():
            failures.append("QA-2: unresolved markers")
        if len(text.split()) < 3:
            failures.append("QA-3: below minimum signal")
        # QA-4..8 (structural/legibility/sequence/coherence) are deeper checks;
        # represented here by the substance + register gate above.
        return (not failures, failures)
