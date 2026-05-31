"""Tests for the Caveman compressor (spec section II) — run with `pytest`."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monarch import compress, detect_register, find_forbidden, select_tier  # noqa: E402
from monarch.state import Register, Tier  # noqa: E402


def test_strips_filler_opener():
    out = compress("Sure! Here is the fix.\nDo X.", Tier.FULL)
    assert not out.lower().startswith("sure")
    assert "Do X." in out


def test_strips_filler_closer():
    out = compress("Do X.\nHope this helps!", Tier.FULL)
    assert "hope this helps" not in out.lower()
    assert "Do X." in out


def test_bans_exclamation_outside_code():
    out = compress("Ship it!", Tier.FULL)
    assert "!" not in out


def test_preserves_code_block_byte_for_byte():
    text = "Fix:\n```python\nprint('hi!')  # keep this!\n```\nDone."
    out = compress(text, Tier.FULL)
    assert "print('hi!')  # keep this!" in out  # exclamation inside code kept


def test_preserves_paths_and_urls():
    text = "See /etc/hosts and https://example.com/x for details."
    out = compress(text, Tier.FULL)
    assert "/etc/hosts" in out
    assert "https://example.com/x" in out


def test_collapses_blank_runs_in_full():
    text = "A.\n\n\n\nB."
    out = compress(text, Tier.FULL)
    assert "\n\n\n" not in out


def test_ultra_drops_connectives():
    out = compress("Well, the cause is latency.", Tier.ULTRA)
    assert not out.lower().startswith("well,")
    assert "latency" in out


def test_find_forbidden_flags_register_and_exclamation():
    hits = find_forbidden("This is a weapon! It transcends limits.")
    assert "weapon" in hits
    assert "transcends" in hits
    assert "exclamation mark" in hits


def test_find_forbidden_ignores_protected_spans():
    # exclamation/forbidden term inside code must not be flagged
    assert find_forbidden("ok `weapon!` done") == []


def test_detect_register():
    assert detect_register("I feel anxious about this") == Register.EMOTIONAL
    assert detect_register("optimize the query") == Register.TECHNICAL
    assert detect_register("I want to die") == Register.CRISIS


def test_tier_selection_rules():
    assert select_tier(Register.TECHNICAL, override=False) == Tier.FULL
    assert select_tier(Register.EMOTIONAL, override=False) == Tier.LITE
    assert select_tier(Register.CRISIS, override=True) == Tier.LITE
    assert select_tier(Register.TECHNICAL, override=True) == Tier.LITE
    assert select_tier(Register.TECHNICAL, override=False, ultra=True) == Tier.ULTRA
