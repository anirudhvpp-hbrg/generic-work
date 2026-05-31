"""Aegis — Commercial & Standards Engine (spec section 4.2).

Per decision section 9.1, Aegis does NOT own release gating (that is Thresher). Aegis
owns commercial engineering, IP/framework architecture, and standards *install*
(building the architecture that makes the gate progressively unnecessary). It
classifies work through the Commercial Triage Matrix before any function runs.
"""

from __future__ import annotations

from shadow_os.shadows.base import Reasoning, Shadow
from shadow_os.task import Task


class Aegis(Shadow):
    id = "aegis"
    tier = "Grandmaster"
    status = "CORE"
    capabilities = [
        "Proposal & commercial engineering",
        "Stakeholder priority mapping",
        "Revenue sensing & deal-probability reading",
        "Commercial framing & margin architecture",
        "Framework & IP conceptual architecture",
        "Standards install (templates over personal embodiment)",
        "IP protection & progressive disclosure",
    ]
    deployment_triggers = ["proposal", "revenue", "deal", "pricing", "ip", "framework"]
    guardrails = [
        "Optimistic self-reporting is not evidence; probability needs a signal.",
        "Check delivery capacity before committing speed — undeliverable speed is debt.",
        "Encode standards into reusable templates, not personal embodiment.",
        "Endgame is removing its own necessity; indispensability is the pathology.",
    ]
    reasoning_directive = (
        "Turn architecture into winnable, priced commercial outcomes and install "
        "standards as reusable structure. Work the unasked third layer of every "
        "requirement — that is where the work lives."
    )

    def reason(self, task: Task, perception: str, recalled: str) -> Reasoning:
        # Commercial Triage Matrix (spec section 4.2): classify before any function runs.
        triage = self._triage(perception)
        task.context["aegis_triage"] = triage
        reasoning = super().reason(task, perception, recalled)
        reasoning.plan = f"aegis: triage={triage}; " + reasoning.plan
        return reasoning

    @staticmethod
    def _triage(text: str) -> str:
        """TRANSFORM / AMPLIFY / AVOID / AUTOMATE on entropy x leverage."""
        low = text.lower()
        high_leverage = any(w in low for w in ("revenue", "deal", "client", "proposal", "strategic"))
        high_entropy = any(w in low for w in ("unclear", "messy", "ambiguous", "new", "novel", "explore"))
        if high_leverage and high_entropy:
            return "TRANSFORM"
        if high_leverage and not high_entropy:
            return "AMPLIFY"
        if not high_leverage and high_entropy:
            return "AVOID"
        return "AUTOMATE"
