"""The 8 Governing Invariants of Shadow OS v4 (spec §1).

Data, not behaviour. The orchestrator references these; tests assert the engine
upholds the enforceable ones (notably 6 RSI dual-output and 7 Monarch absolute).
"""

from __future__ import annotations

INVARIANTS = (
    "Capability-first: no proper name survives as a standalone entity.",
    "No mixed justification: each capability makes its case alone.",
    "Evidence-grounded: survival decided by real usage, not self-report.",
    "Fold or retire, don't bloat.",
    "Import the function, not the pathology: dysfunction becomes a guardrail.",
    "RSI dual-output: every run yields a deliverable + an upgrade artifact.",
    "Monarch absolute: no shadow output ships unratified.",
    "Compression-before-deposit: nothing bloated enters the knowledge store.",
)

# 5-question Socratic self-interrogation gate (spec §3, run before classification).
SOCRATIC_GATE = (
    "What is actually being asked, beneath the surface request?",
    "What must be true for this to succeed (the unasked third layer)?",
    "What is the cost of being wrong here — Type-1 or Type-2 decision?",
    "What evidence grounds the planned answer, and at what confidence tier?",
    "What would the cold reader, with no prior context, conclude?",
)
