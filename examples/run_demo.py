"""Drive the Monarch pipeline offline and show every stage (no model needed).

    python examples/run_demo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monarch import Monarch, MockLLM  # noqa: E402


def scripted_llm(system: str, user: str) -> str:
    # Pretend the model produced a filler-laden, exclamation-heavy draft so the
    # Caveman compressor and QA gate visibly do their job.
    return (
        "Sure! I'd be happy to help with this great question.\n\n"
        "Retention dipped after the v2 onboarding change.\n"
        "Root cause: the new email step added friction at signup.\n"
        "Fix: restore the one-click path; instrument the funnel at `/signup`.\n\n"
        "Hope this helps!"
    )


def main() -> int:
    monarch = Monarch(llm=MockLLM(handler=scripted_llm))
    state = monarch.run("hey, could you walk me through why retention dipped?")

    print("=== DIRECTIVE (intake) ===")
    print(state.directive)
    print("\n=== DRAFT (Vajra, pre-compression) ===")
    print(state.draft)
    print(f"\n=== TIER: {state.tier.value}  REGISTER: {state.register.value} ===")
    print("\n=== OUTPUT (Caveman-compressed) ===")
    print(state.output)
    print("\n=== QA ===")
    print(f"passed={state.qa.passed} attempts={state.qa.attempts}")
    if state.qa.failures:
        print("failures:", state.qa.failures)
    print(f"\nshipped={state.shipped}")
    return 0 if state.shipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
