"""End-to-end tests for the Monarch pipeline — run with `pytest`."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monarch import Monarch, MockLLM  # noqa: E402
from monarch.intake import run_intake  # noqa: E402
from monarch.qa import VOICE_CHECKS, run_qa  # noqa: E402
from monarch.state import PipelineState, Register, Tier  # noqa: E402


def test_intake_strips_surface_and_routes_shadows():
    state = PipelineState(raw_request="hey could you analyze the retention data")
    run_intake(state)
    assert not state.directive.lower().startswith("hey")
    assert "Analyst" in state.routed_shadows


def test_intake_detects_override():
    state = PipelineState(raw_request="walk me through the architecture")
    run_intake(state)
    assert state.override_active is True


def test_intake_binds_context_into_directive():
    state = PipelineState(raw_request="summarize", context={"topic": "AIOS"})
    run_intake(state)
    assert "topic=AIOS" in state.directive


def test_pipeline_ships_clean_output():
    monarch = Monarch(llm=MockLLM(handler=lambda s, u: "Cause: latency. Fix: cache."))
    state = monarch.run("why is it slow")
    assert state.shipped is True
    assert state.qa.passed is True
    assert "Cause: latency" in state.output


def test_pipeline_compresses_filler_and_exclamation():
    draft = "Sure! I'd be happy to help.\nThe fix is to add an index.\nHope this helps!"
    monarch = Monarch(llm=MockLLM(handler=lambda s, u: draft))
    state = monarch.run("how to speed up the query")
    assert "!" not in state.output
    assert "hope this helps" not in state.output.lower()
    assert "add an index" in state.output
    assert state.shipped is True


def test_qa_runs_exactly_eleven_questions():
    assert len(VOICE_CHECKS) == 11
    state = PipelineState(raw_request="x", output="A clean, load-bearing answer.")
    report = run_qa(state, attempts=1)
    assert len(report.checks) == 11


def test_qa_fails_on_forbidden_register_then_pipeline_flags():
    # A draft that stays forbidden even after compression should not ship.
    draft = "This weapon transcends all limits and recursive degradation."
    monarch = Monarch(llm=MockLLM(handler=lambda s, u: draft), max_qa_attempts=2)
    state = monarch.run("describe it")
    assert state.qa.passed is False
    assert state.shipped is False
    assert "no_forbidden_register" in state.qa.failures


def test_emotional_register_uses_lite_tier():
    monarch = Monarch(llm=MockLLM(handler=lambda s, u: "That sounds really hard. "
                                                       "Here is one small next step."))
    state = monarch.run("I feel overwhelmed and anxious about the launch")
    assert state.register == Register.EMOTIONAL
    assert state.tier == Tier.LITE
    assert state.shipped is True


def test_ultra_tier_on_explicit_request():
    monarch = Monarch(llm=MockLLM(handler=lambda s, u: "Well, the answer is yes."))
    state = monarch.run("tl;dr is it worth it")
    assert state.tier == Tier.ULTRA
    assert not state.output.lower().startswith("well,")


def test_trace_is_serializable_dict():
    state = Monarch().run("plan the roadmap")
    trace = state.trace()
    assert set(trace) >= {"directive", "tier", "qa_passed", "shipped", "shadows"}
    assert "Strategist" in trace["shadows"]
