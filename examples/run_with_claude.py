"""Drive the engine against a real Claude model.

    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python examples/run_with_claude.py "tighten this bloated proposal deck"

Each shadow's reasoning now runs on Claude Opus 4.8 (adaptive thinking, prompt
caching on the per-shadow system prompt). Without a key/SDK this prints a hint
and exits — it does not fall back silently.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shadow_os import Monarch  # noqa: E402
from monarch.claude_llm import ClaudeLLM  # noqa: E402


def main() -> int:
    directive = " ".join(sys.argv[1:]) or "draft the executive summary for the Hexaware proposal"

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY (and `pip install anthropic`) to run this. "
              "For offline runs use examples/run_engine.py.")
        return 2

    llm = ClaudeLLM()                      # Opus 4.8, adaptive thinking, cached system
    monarch = Monarch(llm=llm)
    task = monarch.run(directive)

    print(f"[class={task.task_class} · loadout={'->'.join(task.shadow_loadout)} · "
          f"{'SHIPPED' if task.shipped else 'VETOED'}]\n")
    print(task.final_output or "(vetoed — see governance trail)")
    print("\nClaude usage:", llm.usage)
    return 0 if task.shipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
