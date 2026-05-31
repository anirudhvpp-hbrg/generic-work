"""The object carried through the Monarch pipeline, stage to stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Tier(str, Enum):
    """Caveman compression tier (spec §II)."""

    FULL = "full"
    LITE = "lite"
    ULTRA = "ultra"


class Register(str, Enum):
    """Detected emotional/technical register, drives tier selection."""

    TECHNICAL = "technical"
    EMOTIONAL = "emotional"
    CRISIS = "crisis"


@dataclass
class QAReport:
    """Result of the QA gate (spec §0.4)."""

    passed: bool = False
    failures: List[str] = field(default_factory=list)
    checks: Dict[str, bool] = field(default_factory=dict)
    attempts: int = 0


@dataclass
class PipelineState:
    """Mutable state threaded through every stage.

    Each stage reads what it needs and writes its own fields; nothing is
    overwritten destructively, so the final state is a full audit trail of the
    run — Intake's directive, Vajra's reasoning, the draft, the compressed
    output, and the QA verdict.
    """

    # Intake inputs
    raw_request: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    # Intake outputs (§0.1)
    directive: str = ""
    routed_shadows: List[str] = field(default_factory=list)
    register: Register = Register.TECHNICAL
    override_active: bool = False

    # Reasoning outputs (§0.2)
    reasoning: str = ""

    # Output stages (§0.2 draft -> §0.3 compressed)
    draft: str = ""
    tier: Tier = Tier.FULL
    output: str = ""

    # QA (§0.4)
    qa: QAReport = field(default_factory=QAReport)

    # Ship (§0.5)
    shipped: bool = False

    def trace(self) -> Dict[str, Any]:
        """A compact dict view of the run for logging/inspection."""
        return {
            "directive": self.directive,
            "shadows": self.routed_shadows,
            "register": self.register.value,
            "tier": self.tier.value,
            "override_active": self.override_active,
            "qa_passed": self.qa.passed,
            "qa_attempts": self.qa.attempts,
            "qa_failures": self.qa.failures,
            "shipped": self.shipped,
        }
