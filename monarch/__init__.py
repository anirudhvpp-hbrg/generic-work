"""Monarch OS v1.1 — a working implementation of the cognitive pipeline.

    INTAKE -> REASONING (Vajra) -> OUTPUT (Caveman) -> QA -> SHIP

The spec lives in ``docs/monarch-os-v1.1.md``. This package turns it into code:
deterministic intake/compression/QA, a model-agnostic reasoning stage, and a
sealed Constitution the run is checked against.

Example::

    from monarch import Monarch

    monarch = Monarch()              # offline MockLLM by default
    state = monarch.run("walk me through why our retention dipped")
    print(state.output)              # Caveman-compressed, QA-passed
    print(state.trace())             # full audit trail
"""

from monarch.pipeline import Monarch
from monarch.state import PipelineState, QAReport, Register, Tier
from monarch.llm import LLM, MockLLM, CallableLLM
from monarch.caveman import compress, select_tier, detect_register, find_forbidden

__all__ = [
    "Monarch",
    "PipelineState",
    "QAReport",
    "Register",
    "Tier",
    "LLM",
    "MockLLM",
    "CallableLLM",
    "compress",
    "select_tier",
    "detect_register",
    "find_forbidden",
]

__version__ = "1.1.0"
