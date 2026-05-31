"""The Task entity and run artifacts (spec §7 data model).

``Task`` generalizes the v1.1 ``PipelineState``: it carries a directive through
Sovereign Reconstruction, routing, the shadow loadout's loops, and ratification —
and accumulates the governance trail, telemetry, and RSI artifacts a run must
produce (Invariant 6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Gamma(str, Enum):
    """Sovereign Confidence Ratio — System 1 fast-path vs System 2 deliberate."""

    SYSTEM1 = "system1"   # fast, low-stakes, pattern-matched
    SYSTEM2 = "system2"   # deliberate, high-stakes, full loop


class DecisionType(str, Enum):
    TYPE1 = "type1"  # irreversible — pre-mortem mandatory
    TYPE2 = "type2"  # reversible — move fast


@dataclass
class RSIArtifact:
    """Shadow RSI Contract (Invariant 6)."""

    shadow: str
    delta: str
    failure_avoided: str
    reuse_destination: str
    verify_status: str = "unverified"


@dataclass
class GovernanceEntry:
    """One line of the governance trail (spec §7 Governance Log)."""

    trigger: str
    action: str
    monarch_ratification: bool
    metrics_delta: str = ""


@dataclass
class ShadowResult:
    """Output of one shadow's 4-stage loop."""

    shadow: str
    artifact: str = ""
    confidence: float = 0.0          # 0..1, matched to evidence tier
    iterations: int = 0
    goal_met: bool = False
    self_critique: str = ""
    rsi: Optional[RSIArtifact] = None
    notes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """A directive flowing through the engine."""

    # Perception / intake
    raw_input: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    # Sovereign Reconstruction (Monarch, §3)
    reconstructed_intent: str = ""
    beliefs: List[str] = field(default_factory=list)
    gamma: Gamma = Gamma.SYSTEM2
    decision_type: DecisionType = DecisionType.TYPE2
    snr_notes: str = ""

    # Routing
    task_class: str = "general"
    shadow_loadout: List[str] = field(default_factory=list)

    # Execution
    results: Dict[str, ShadowResult] = field(default_factory=dict)
    final_output: str = ""

    # Governance / ratification
    ratified: bool = False
    shipped: bool = False
    governance_log: List[GovernanceEntry] = field(default_factory=list)
    rsi_artifacts: List[RSIArtifact] = field(default_factory=list)
    telemetry: Dict[str, Any] = field(default_factory=dict)

    def log(self, trigger: str, action: str, ratified: bool, delta: str = "") -> None:
        self.governance_log.append(
            GovernanceEntry(trigger, action, ratified, delta)
        )

    def trace(self) -> Dict[str, Any]:
        return {
            "task_class": self.task_class,
            "gamma": self.gamma.value,
            "decision_type": self.decision_type.value,
            "loadout": self.shadow_loadout,
            "ratified": self.ratified,
            "shipped": self.shipped,
            "rsi_count": len(self.rsi_artifacts),
            "governance_steps": len(self.governance_log),
            "telemetry": self.telemetry,
        }
