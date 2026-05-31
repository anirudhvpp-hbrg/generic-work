"""Run the cognitive engine on the resource kernel — full stack, offline.

    python examples/run_on_kernel.py

Shows the kernel doing real work beneath Monarch: shared LLM Core accounting,
per-agent access enforcement (Aegis may touch pipeline data; Ira may not),
context snapshots, kernel-persisted memory, and the standalone scheduler
sequencing independent jobs by priority.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monarch.llm import MockLLM  # noqa: E402
from kernel import Kernel, AccessDenied  # noqa: E402
from shadow_os import Monarch  # noqa: E402


def main() -> int:
    kernel = Kernel(llm=MockLLM(handler=lambda s, u: "Grounded, compressed answer."))
    monarch = Monarch(kernel=kernel)  # boots the fleet onto the kernel

    task = monarch.run("draft the executive summary for the Hexaware proposal")
    print("Directive shipped:", task.shipped, "| loadout:", "->".join(task.shadow_loadout))
    print("Kernel LLM usage:", kernel.llm_core.usage())
    print("Context snapshots:", [s for s in task.shadow_loadout if kernel.context.has(s)])
    print("Kernel memory units:", len(kernel.memory))

    # Access enforcement — the concrete example.
    print("\nAccess control:")
    print("  aegis -> pipeline_data:",
          kernel.syscall("aegis", "tool.call", tool="pipeline_data"))
    try:
        kernel.syscall("ira", "tool.call", tool="pipeline_data")
    except AccessDenied as e:
        print("  ira  -> pipeline_data: DENIED —", e)

    # Standalone scheduler: independent jobs run in priority order.
    print("\nScheduler (priority order):")
    kernel.scheduler.submit("analyst", lambda: "evidence", priority=5)
    kernel.scheduler.submit("thresher", lambda: "gate", priority=1)  # highest
    kernel.scheduler.submit("quill", lambda: "prose", priority=8)
    kernel.scheduler.run()
    print("  executed:", kernel.scheduler.history)

    return 0 if task.shipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
