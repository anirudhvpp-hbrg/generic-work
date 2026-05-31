"""Stage 1 — Sovereign Intake (spec §0.1).

Strip surface request -> bind context -> reconstruct directive -> route shadows.

Intake is native and automatic: it runs on every prompt with no invocation.
The shadow router uses a keyword map because the spec names the Shadow Fleet but
does not enumerate routing internals; the map is the documented extension point.
"""

from __future__ import annotations

import re
from typing import Dict, List

from monarch.caveman import detect_register
from monarch.constitution import OVERRIDE_TRIGGERS, SHADOW_FLEET
from monarch.state import PipelineState

# Keyword -> shadow routing. Extend freely; this is the configurable seam the
# spec leaves open ("Routed by Monarch intake").
_SHADOW_KEYWORDS: Dict[str, tuple] = {
    "Strategist": ("strategy", "roadmap", "go-to-market", "positioning", "plan"),
    "Analyst": ("analyze", "analysis", "data", "metric", "numbers", "evaluate"),
    "Visionary": ("vision", "future", "imagine", "long-term", "north star"),
    "Genius": ("invent", "novel", "breakthrough", "design", "architect"),
    "Axiom Prime": ("first principles", "axiom", "fundamental", "ground truth"),
    "Sentinel Prime": ("risk", "security", "threat", "safeguard", "compliance"),
    "Thresher": ("cut", "prioritize", "triage", "kill", "trim", "scope"),
}

# Filler/politeness prefixes stripped to reach the true ask.
_SURFACE_PREFIXES = (
    "hey", "hi", "hello", "please", "could you", "can you", "would you",
    "i was wondering if you could", "i need you to", "i want you to",
    "would you mind", "if you don't mind",
)


def _strip_surface(request: str) -> str:
    text = request.strip()
    lowered = text.lower()
    changed = True
    while changed:
        changed = False
        for prefix in _SURFACE_PREFIXES:
            if lowered.startswith(prefix):
                text = text[len(prefix):].lstrip(" ,:-")
                lowered = text.lower()
                changed = True
    return text or request.strip()


def _route_shadows(text: str) -> List[str]:
    lowered = text.lower()
    routed: List[str] = []
    for shadow, keywords in _SHADOW_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            routed.append(shadow)
    return routed


def _detect_override(text: str) -> bool:
    lowered = text.lower()
    return any(trigger in lowered for trigger in OVERRIDE_TRIGGERS)


def _detect_ultra(text: str) -> bool:
    lowered = text.lower()
    return any(p in lowered for p in ("ultra", "telegraphic", "one-liner",
                                      "just the answer", "tl;dr"))


def run_intake(state: PipelineState) -> PipelineState:
    request = state.raw_request
    core = _strip_surface(request)

    # Reconstruct directive: the stripped core ask, bound to any context keys.
    directive = core
    if state.context:
        bound = "; ".join(f"{k}={v}" for k, v in state.context.items())
        directive = f"{core}\n[context: {bound}]"

    state.directive = directive
    state.routed_shadows = _route_shadows(core)
    state.register = detect_register(request)
    state.override_active = _detect_override(request)
    # stash ultra detection on context for the output stage
    state.context.setdefault("_ultra", _detect_ultra(request))
    return state
