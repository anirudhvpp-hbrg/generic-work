"""Monarch — the unified pipeline (spec §0).

    INTAKE -> REASONING (Vajra) -> OUTPUT (Caveman) -> QA -> SHIP

Reasoning stays full; output compresses; QA is a hard stop that recompresses and
reships on failure; ship means attach-and-send-ready.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from monarch.caveman import compress, select_tier
from monarch.intake import run_intake
from monarch.llm import LLM, MockLLM
from monarch.qa import run_qa
from monarch.reason import run_reasoning
from monarch.state import PipelineState, Tier


class Monarch:
    """The Monarch OS cognitive pipeline.

    Args:
        llm: Any object with ``complete(system, user) -> str``. Defaults to
            ``MockLLM`` so the pipeline runs offline (Invariant 11: model-agnostic).
        max_qa_attempts: How many recompress/reship cycles before giving up and
            shipping the best attempt with the QA report attached.
    """

    def __init__(self, llm: Optional[LLM] = None, max_qa_attempts: int = 3):
        self.llm = llm or MockLLM()
        self.max_qa_attempts = max(1, max_qa_attempts)

    def run(self, request: str, context: Optional[Dict[str, Any]] = None) -> PipelineState:
        state = PipelineState(raw_request=request, context=dict(context or {}))

        # 1. Intake — native, automatic.
        run_intake(state)

        # 2. Reason — full Vajra substrate.
        run_reasoning(state, self.llm)

        # 3 + 4. Compress (Caveman) then QA, looping on failure (§0.4).
        ultra = bool(state.context.get("_ultra"))
        state.tier = select_tier(state.register, state.override_active, ultra=ultra)

        attempt = 0
        tier = state.tier
        while True:
            attempt += 1
            state.output = compress(state.draft, tier)
            state.qa = run_qa(state, attempts=attempt)
            if state.qa.passed or attempt >= self.max_qa_attempts:
                break
            # Recompress harder on failure: escalate tier toward Ultra.
            tier = _escalate(tier)
            state.tier = tier

        # 5. Ship — only when QA passes (Invariant 17). Otherwise the output and
        # its failing QA report are returned for inspection, not shipped.
        state.shipped = state.qa.passed
        return state


def _escalate(tier: Tier) -> Tier:
    if tier is Tier.LITE:
        return Tier.FULL
    if tier is Tier.FULL:
        return Tier.ULTRA
    return Tier.ULTRA
