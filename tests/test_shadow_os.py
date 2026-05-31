"""Tests for the Shadow OS v4 engine — run with `pytest` (no model required)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monarch.llm import MockLLM  # noqa: E402
from shadow_os import Monarch, Memory, TaskClassifier, ShadowRouter  # noqa: E402
from shadow_os.shadows.thresher import Thresher  # noqa: E402
from shadow_os.task import Gamma  # noqa: E402


# --- Routing ---------------------------------------------------------------

def test_classifier_maps_task_classes():
    c = TaskClassifier()
    assert c.classify("tighten this bloated deck") == "compression"
    assert c.classify("research the data") == "research"
    assert c.classify("design the system architecture") == "architecture"
    assert c.classify("write the proposal pricing") == "commercial"
    assert c.classify("xyzzy") == "general"


def test_router_fronts_thresher_and_excludes_ira_by_default():
    r = ShadowRouter()
    # compression -> thresher primary
    assert r.loadout("compression")[0] == "thresher"
    # redirection routes to ira, but ira is stripped unless personal
    assert "ira" not in r.loadout("redirection", personal=False)
    assert r.loadout("redirection", personal=True)[0] == "ira"


# --- Sovereign Reconstruction / γ -----------------------------------------

def test_gamma_calibration_high_vs_low_stakes():
    m = Monarch(llm=MockLLM(handler=lambda s, u: "clean answer"))
    low = m.run("tighten this paragraph")
    high = m.run("decide whether to launch the irreversible contract architecture")
    assert low.gamma == Gamma.SYSTEM1
    assert high.gamma == Gamma.SYSTEM2


def test_intake_strips_surface_politeness():
    m = Monarch(llm=MockLLM(handler=lambda s, u: "clean answer"))
    task = m.run("hey could you tighten this deck")
    assert not task.reconstructed_intent.lower().startswith("hey")


# --- End-to-end orchestration ---------------------------------------------

def test_run_ships_clean_output_and_emits_rsi():
    m = Monarch(llm=MockLLM(handler=lambda s, u: "Cause: friction at signup. Fix: one-click path."))
    task = m.run("tighten the retention writeup")
    assert task.shipped is True
    assert task.ratified is True
    assert task.final_output
    assert len(task.rsi_artifacts) >= 1            # Invariant 6
    assert task.governance_log                      # governance trail exists


def test_monarch_vetoes_forbidden_register():
    # Output containing forbidden register must be vetoed at the gate (Inv. 7).
    m = Monarch(llm=MockLLM(handler=lambda s, u: "This weapon transcends all limits."))
    task = m.run("describe the product")
    assert task.shipped is False
    assert task.ratified is False
    assert any("VETO" in g.action for g in task.governance_log)


def test_personal_directive_routes_to_ira():
    m = Monarch(llm=MockLLM(handler=lambda s, u: "What is the decision really about?"))
    task = m.run("I'm stuck on how to approach this", context={"personal": True})
    assert "ira" in task.shadow_loadout


def test_ira_never_in_nonpersonal_loadout():
    m = Monarch(llm=MockLLM(handler=lambda s, u: "reframed question"))
    task = m.run("I'm stuck on how to approach this")  # personal not set
    assert "ira" not in task.shadow_loadout


# --- Thresher gate + compression primitive --------------------------------

def test_thresher_gate_blocks_empty_and_forbidden():
    t = Thresher(MockLLM())
    assert t.gate("")[0] is False
    assert t.gate("a clean shippable sentence here")[0] is True
    ok, failures = t.gate("this is a weapon!")
    assert ok is False and any("QA-1" in f for f in failures)


def test_thresher_compresses_filler_in_act():
    m = Monarch(llm=MockLLM(handler=lambda s, u: "Sure! Here is the fix. Hope this helps!"))
    task = m.run("compress this note")
    # filler + exclamation stripped by Thresher's compression primitive
    assert "!" not in task.final_output
    assert "hope this helps" not in task.final_output.lower()


# --- Memory ----------------------------------------------------------------

def test_memory_learns_loadout_via_tkl():
    mem = Memory()
    m = Monarch(llm=MockLLM(handler=lambda s, u: "clean answer"), memory=mem)
    m.run("research the data")
    assert "research" in mem.tkl
    assert mem.tkl["research"].loadout[0] == "analyst"


def test_memory_compresses_before_deposit():
    mem = Memory()
    unit = mem.deposit("Sure! the deposited fact.\nHope this helps!")
    assert "!" not in unit.text
    assert "hope this helps" not in unit.text.lower()
