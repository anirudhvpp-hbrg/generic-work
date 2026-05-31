"""Stage 4 — QA gate (spec §0.4): 11-question voice check + invariants.

The spec mandates an "11-question voice check + invariants" and that QA is a
hard stop, never advisory: on failure -> recompress -> reship. The spec states
the *Voice test* but does not enumerate the 11 questions verbatim, so the 11
checks below are derived from the Voice section (§III), the Caveman rules (§II),
and the relevant Invariants (§V 17, 18). They are deliberately mechanical so QA
can actually gate. Treat ``VOICE_CHECKS`` as the configurable spec point.
"""

from __future__ import annotations

import re
from typing import Callable, List, Tuple

from monarch.caveman import find_forbidden
from monarch.state import PipelineState, QAReport, Register

# Each check: (name, predicate) where predicate(text, state) -> bool (True=pass).
Check = Tuple[str, Callable[[str, PipelineState], bool]]


def _no_forbidden_register(text: str, state: PipelineState) -> bool:
    return not find_forbidden(text)


def _no_exclamation(text: str, state: PipelineState) -> bool:
    # find_forbidden already covers it, but keep as a discrete voice question.
    return "!" not in re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def _no_filler_opener(text: str, state: PipelineState) -> bool:
    lowered = text.strip().lower()
    return not any(
        lowered.startswith(p)
        for p in ("sure", "great question", "i'd be happy", "certainly",
                  "of course", "let me unpack")
    )


def _first_line_load_bearing(text: str, state: PipelineState) -> bool:
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    return len(first) >= 3 and not first.lower().startswith(("here", "below"))


def _has_substance(text: str, state: PipelineState) -> bool:
    return bool(text.strip())

# Invariant 16 / completion discipline — output should read as a deliverable,
# not narration about what the OS is doing.
def _not_self_narrating(text: str, state: PipelineState) -> bool:
    lowered = text.lower()
    return not any(
        phrase in lowered
        for phrase in ("as the os", "the pipeline", "i will now", "i am going to",
                       "monarch will", "let me walk you through what i")
    )


def _respects_register_warmth(text: str, state: PipelineState) -> bool:
    # Lite/crisis register must not be terse to the point of coldness:
    # require at least a minimal length when register is emotional/crisis.
    if state.register in (Register.EMOTIONAL, Register.CRISIS):
        return len(text.strip()) >= 20
    return True


def _no_recap_closer(text: str, state: PipelineState) -> bool:
    tail = " ".join(text.strip().lower().splitlines()[-1:])
    return not any(
        c in tail
        for c in ("hope this helps", "let me know if", "feel free to")
    )


def _single_idea_density(text: str, state: PipelineState) -> bool:
    # Voice §III: short sentences, one idea each. Flag run-on sentences.
    sentences = re.split(r"(?<=[.?])\s+", re.sub(r"```.*?```", "", text,
                                                 flags=re.DOTALL))
    return all(len(s.split()) <= 60 for s in sentences if s.strip())


def _forward_close(text: str, state: PipelineState) -> bool:
    # "Final line moves forward" — non-empty, not a dead-end apology.
    last = next((ln.strip() for ln in reversed(text.splitlines()) if ln.strip()),
                "")
    return bool(last) and not last.lower().startswith(("sorry", "unfortunately"))


def _word_load_bearing(text: str, state: PipelineState) -> bool:
    # Reject obvious padding phrases.
    lowered = text.lower()
    return not any(
        p in lowered
        for p in ("at the end of the day", "needless to say", "it goes without",
                  "in order to be able to", "the fact of the matter is")
    )


# The 11 derived voice/invariant questions (spec §0.4).
VOICE_CHECKS: List[Check] = [
    ("substance_present", _has_substance),
    ("no_forbidden_register", _no_forbidden_register),
    ("no_exclamation", _no_exclamation),
    ("no_filler_opener", _no_filler_opener),
    ("no_recap_closer", _no_recap_closer),
    ("first_line_load_bearing", _first_line_load_bearing),
    ("forward_close", _forward_close),
    ("not_self_narrating", _not_self_narrating),
    ("single_idea_density", _single_idea_density),
    ("word_load_bearing", _word_load_bearing),
    ("register_warmth", _respects_register_warmth),
]

assert len(VOICE_CHECKS) == 11, "QA must run exactly 11 voice questions (spec)"


def run_qa(state: PipelineState, attempts: int) -> QAReport:
    """Run the 11-question voice check against the compressed output."""
    text = state.output
    checks = {}
    failures = []
    for name, predicate in VOICE_CHECKS:
        ok = predicate(text, state)
        checks[name] = ok
        if not ok:
            failures.append(name)
    return QAReport(
        passed=not failures,
        failures=failures,
        checks=checks,
        attempts=attempts,
    )
