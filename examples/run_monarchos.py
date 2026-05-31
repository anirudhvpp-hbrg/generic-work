"""Boot Monarch OS locally and run a directive through Shadow OS.

    python examples/run_monarchos.py "tighten this bloated proposal deck"

Uses ephemeral (in-process) memory and the offline MockLLM unless you set
ANTHROPIC_API_KEY. For the full local experience (durable memory + a shell), run
``python -m monarchos`` instead.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monarchos import boot  # noqa: E402


def main() -> int:
    directive = " ".join(sys.argv[1:]) or "research why retention dropped after onboarding"
    rt = boot(persist=False)                 # in-process; set ANTHROPIC_API_KEY for Claude
    print("Monarch OS status:", rt.status())
    task = rt.run(directive)
    print(f"\n[{'SHIPPED' if task.shipped else 'VETOED'}] "
          f"class={task.task_class} loadout={'->'.join(task.shadow_loadout)}")
    print(task.final_output)
    return 0 if task.shipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
