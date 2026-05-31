"""Stage 2 — Vajra reasoning substrate (spec §0.2).

Reasoning stays full; only the *output* compresses. This stage builds a Vajra
system prompt from the Constitution and asks the LLM to think in the mandated
structure (taxonomy, Claim->Evidence->Implication->Kill condition, three
layers, TRANSFORM/AMPLIFY/AVOID/AUTOMATE triage), then produces the uncompressed
draft answer.
"""

from __future__ import annotations

from monarch.constitution import FIVE_LAWS, UNBREAKABLE_CORE
from monarch.llm import LLM
from monarch.state import PipelineState

_VAJRA_SYSTEM = """You are the Vajra reasoning substrate of Monarch OS.
Reason in full depth. Do not compress here — compression happens downstream.

Five Laws:
{laws}

Unbreakable Core:
{core}

Method, in order:
1. Taxonomy first — classify what kind of problem this is before answering.
2. Chain every assertion: Claim -> Evidence -> Implication -> Kill condition.
3. Work three layers: what was asked, what was thought-asked, what was unasked.
   Layer 3 (the unasked) is the real work.
4. Triage moves as TRANSFORM / AMPLIFY / AVOID / AUTOMATE before content.
5. Deliver the delta, not generic prescription. System over one-off output.
Conclusions are provisional; certainty is earned, not performed.
Produce a complete, correct answer to the directive."""


def build_system_prompt() -> str:
    laws = "\n".join(f"  {i + 1}. {law}" for i, law in enumerate(FIVE_LAWS))
    core = "\n".join(f"  - {c}" for c in UNBREAKABLE_CORE)
    return _VAJRA_SYSTEM.format(laws=laws, core=core)


def run_reasoning(state: PipelineState, llm: LLM) -> PipelineState:
    system = build_system_prompt()
    shadows = (
        f"\nRouted shadows (advisory): {', '.join(state.routed_shadows)}."
        if state.routed_shadows
        else ""
    )
    user = f"Directive:\n{state.directive}{shadows}"

    answer = llm.complete(system, user)
    state.reasoning = answer
    # The draft to be compressed is the model's answer. Reasoning trace and
    # draft are the same artifact here; a richer setup could separate them.
    state.draft = answer
    return state
