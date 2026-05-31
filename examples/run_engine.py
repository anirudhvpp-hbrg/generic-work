"""Drive the Shadow OS v4 engine offline across several task-classes.

    python examples/run_engine.py

Shows Monarch routing different directives to different shadow loadouts, the
Thresher ratification gate, and RSI dual-output — no model required.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shadow_os import Monarch  # noqa: E402
from monarch.llm import MockLLM  # noqa: E402


def model(system: str, user: str) -> str:
    # Stand-in for a real model: a short, clean, shippable answer. (Avoids
    # echoing the system prompt, whose metadata can contain gate-forbidden words.)
    return "Resolved the directive with grounded, compressed output."


DIRECTIVES = [
    ("tighten this bloated 40-slide proposal deck", False),
    ("research why retention dropped after the v2 onboarding change", False),
    ("design the architecture for a multi-tenant billing system", False),
    ("draft the executive summary for the Hexaware proposal", False),
    ("I'm stuck on how to approach the launch decision", True),  # personal -> Ira
]


def main() -> int:
    monarch = Monarch(llm=MockLLM(handler=model))
    all_shipped = True
    for directive, personal in DIRECTIVES:
        task = monarch.run(directive, context={"personal": personal})
        flag = "SHIPPED" if task.shipped else "VETOED"
        print(f"\n=== {directive!r}")
        print(f"    class={task.task_class}  loadout={'->'.join(task.shadow_loadout)}  "
              f"γ={task.gamma.value}  [{flag}]")
        print(f"    RSI artifacts: {len(task.rsi_artifacts)}  "
              f"governance steps: {len(task.governance_log)}")
        all_shipped = all_shipped and task.shipped

    print("\nTKL learned loadouts:", {k: v.loadout for k, v in monarch.memory.tkl.items()})
    print("Memory ledger units:", len(monarch.memory.ledger))
    return 0 if all_shipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
