"""Cognitive Routing (spec §7.1–7.2): regex-first, zero-API-cost dispatch.

``TaskClassifier`` maps a raw directive to a task-class with regex rules.
``ShadowRouter`` maps a task-class to a shadow loadout (primary + support) via a
deterministic dispatch table — no LLM call to route. Unmatched input falls back
to ``general`` (Monarch governs). Ira is personal-only (Invariant / spec §9.4):
it is never placed in a loadout unless ``context["personal"]`` is set.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple


# Ordered (task_class, compiled regex). First match wins.
_CLASS_RULES: List[Tuple[str, "re.Pattern"]] = [
    ("research",     re.compile(r"\b(research|analy[sz]e|data|evidence|investigate|sources?|verify)\b", re.I)),
    ("architecture", re.compile(r"\b(architect|design|system|first principles|structure|blueprint|refactor)\b", re.I)),
    ("commercial",   re.compile(r"\b(proposal|rfp|pricing|revenue|deal|client|margin|commercial|stakeholder)\b", re.I)),
    ("compression",  re.compile(r"\b(compress|tighten|cut|trim|deck|slide|brief|too long|bloated|legibility)\b", re.I)),
    ("artifact",     re.compile(r"\b(write|draft|document|workbook|guide|deck|content|narrative|email)\b", re.I)),
    ("redirection",  re.compile(r"\b(stuck|should i|approach|mindset|overwhelmed|decision|reframe|how do i think)\b", re.I)),
]

# task_class -> (primary, [support...]). Capability-first: Thresher fronts most
# external work (everything enters the gate first, spec §4.1).
_DISPATCH: Dict[str, Tuple[str, List[str]]] = {
    "research":      ("analyst",  ["thresher"]),
    "architecture":  ("axiom",    ["thresher", "quill"]),
    "commercial":    ("aegis",    ["thresher", "quill"]),
    "compression":   ("thresher", ["quill"]),
    "artifact":      ("quill",    ["thresher"]),
    "redirection":   ("ira",      []),
    "general":       ("thresher", []),
}


class TaskClassifier:
    def classify(self, raw_input: str) -> str:
        for task_class, pattern in _CLASS_RULES:
            if pattern.search(raw_input):
                return task_class
        return "general"


class ShadowRouter:
    def loadout(self, task_class: str, personal: bool = False) -> List[str]:
        primary, support = _DISPATCH.get(task_class, _DISPATCH["general"])
        order = [primary, *support]
        # Ira is personal-only — strip from any non-personal loadout (§9.4).
        if not personal:
            order = [s for s in order if s != "ira"]
        # If stripping Ira emptied the loadout, Monarch governs via Thresher.
        return order or ["thresher"]
