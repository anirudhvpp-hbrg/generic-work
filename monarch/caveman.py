"""Caveman — the binding output layer (spec section II).

Deterministic compression applied to every shipped response. Rules implemented
here come straight from the spec:

- strip filler openers/closers,
- ban exclamation marks and the forbidden register,
- preserve protected spans (code blocks, paths, URLs, numbers) byte-for-byte,
- select a tier (Full / Lite / Ultra) and honour override conditions.

Substance is never altered: protected spans are masked out before any text
transformation and restored afterwards, so code, tables, and tool output pass
through untouched.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from monarch.constitution import (
    FILLER_CLOSERS,
    FILLER_OPENERS,
    FORBIDDEN_REGISTER,
)
from monarch.state import Register, Tier

# Spans that must survive byte-for-byte. Order matters: fenced code first.
_PROTECTED_PATTERNS = (
    re.compile(r"```.*?```", re.DOTALL),   # fenced code blocks
    re.compile(r"`[^`\n]+`"),               # inline code
    re.compile(r"https?://\S+"),            # URLs
    re.compile(r"(?:[~./]\S+/\S+|/\S+)"),  # file paths
)

_PLACEHOLDER = "\x00MONARCH_PROTECTED_{}\x00"


def _mask(text: str) -> Tuple[str, List[str]]:
    """Replace protected spans with placeholders; return (masked, spans)."""
    spans: List[str] = []

    def repl(match: "re.Match") -> str:
        spans.append(match.group(0))
        return _PLACEHOLDER.format(len(spans) - 1)

    for pattern in _PROTECTED_PATTERNS:
        text = pattern.sub(repl, text)
    return text, spans


def _unmask(text: str, spans: List[str]) -> str:
    for i, span in enumerate(spans):
        text = text.replace(_PLACEHOLDER.format(i), span)
    return text


# Pure-filler phrases removed anywhere they appear (not just as openers).
_FILLER_PHRASES = (
    "i'd be happy to help",
    "i would be happy to help",
    "great question",
    "let me unpack",
)


def _strip_filler_openers(text: str) -> str:
    """Strip stacked filler phrases from the start of the first non-empty line."""
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        current = line.strip()
        changed = True
        while changed:
            changed = False
            lowered = current.lower()
            for opener in FILLER_OPENERS:
                if lowered.startswith(opener):
                    current = current[len(opener):].lstrip(" ,.:!-")
                    changed = True
                    break
        if current:
            lines[idx] = current
        else:
            lines.pop(idx)
        break  # only the first non-empty line is an "opener"
    return "\n".join(lines)


def _remove_filler_phrases(text: str) -> str:
    """Delete pure-filler phrases anywhere, then tidy resulting whitespace."""
    for phrase in _FILLER_PHRASES:
        text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)
    # tidy: collapse double spaces and orphaned space-before-punctuation
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    # drop lines that are now empty or just punctuation
    kept = [
        ln for ln in text.splitlines()
        if ln.strip() and re.search(r"[A-Za-z0-9]", ln)
    ] if text else []
    # preserve intentional blank lines between content by re-joining simply
    return "\n".join(kept) if kept else text


def _strip_filler_closers(text: str) -> str:
    lines = text.splitlines()
    while lines:
        tail = lines[-1].strip().lower().rstrip("?.! ")
        if not lines[-1].strip():
            lines.pop()
            continue
        if any(tail.startswith(c) or tail == c for c in FILLER_CLOSERS):
            lines.pop()
            continue
        break
    return "\n".join(lines)


def detect_register(text: str) -> Register:
    """Coarse register detection to drive tier selection (spec section II)."""
    lowered = text.lower()
    crisis = ("suicid", "self-harm", "kill myself", "want to die", "panic attack")
    emotional = ("i feel", "i'm scared", "i am scared", "anxious", "grieving",
                 "heartbroken", "i'm struggling", "i am struggling", "overwhelmed")
    if any(w in lowered for w in crisis):
        return Register.CRISIS
    if any(w in lowered for w in emotional):
        return Register.EMOTIONAL
    return Register.TECHNICAL


def select_tier(register: Register, override: bool, ultra: bool = False) -> Tier:
    """Auto tier selection (spec section II 'Tier selection').

    - Emotional / crisis register -> Lite (filler-only removal, keep warmth).
    - Explicit ultra request -> Ultra.
    - Override active (expand/long-form) -> Lite (suspend aggressive cuts).
    - Otherwise -> Full (default).
    """
    if register in (Register.EMOTIONAL, Register.CRISIS):
        return Tier.LITE
    if ultra:
        return Tier.ULTRA
    if override:
        return Tier.LITE
    return Tier.FULL


def find_forbidden(text: str) -> List[str]:
    """Forbidden-register terms present in the (unmasked) visible prose."""
    masked, _ = _mask(text)
    lowered = masked.lower()
    hits = [term for term in FORBIDDEN_REGISTER if term in lowered]
    if "!" in masked:
        hits.append("exclamation mark")
    return hits


def _scrub_forbidden(text: str) -> str:
    """Neutralise banned punctuation outside protected spans (exclamations)."""
    masked, spans = _mask(text)
    masked = masked.replace("!", ".")
    return _unmask(masked, spans)


def compress(text: str, tier: Tier = Tier.FULL) -> str:
    """Apply Caveman compression at the given tier. Substance preserved.

    Lite  -> filler removal + exclamation scrub only.
    Full  -> Lite + collapse blank-line runs (fragment-friendly).
    Ultra -> Full + drop leading discourse connectives per line.
    """
    if not text:
        return text

    masked, spans = _mask(text)

    masked = _strip_filler_openers(masked)
    masked = _strip_filler_closers(masked)
    masked = _remove_filler_phrases(masked)
    masked = masked.replace("!", ".")  # exclamation ban (masked spans safe)

    if tier in (Tier.FULL, Tier.ULTRA):
        # collapse 3+ blank lines to a single blank line
        masked = re.sub(r"\n{3,}", "\n\n", masked)

    if tier is Tier.ULTRA:
        connectives = (
            "well, ", "so, ", "now, ", "basically, ", "essentially, ",
            "in other words, ", "that said, ", "to be clear, ",
        )
        out_lines = []
        for line in masked.splitlines():
            stripped = line.lstrip()
            low = stripped.lower()
            for c in connectives:
                if low.startswith(c):
                    indent = line[: len(line) - len(stripped)]
                    stripped = stripped[len(c):]
                    stripped = stripped[:1].upper() + stripped[1:]
                    line = indent + stripped
                    break
            out_lines.append(line)
        masked = "\n".join(out_lines)

    result = _unmask(masked, spans).strip("\n")
    return result
