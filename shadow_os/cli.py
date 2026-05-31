"""Run a directive through the Shadow OS v4 engine.

    python -m shadow_os.cli "tighten this bloated proposal deck"
    python -m shadow_os.cli --personal "I'm stuck on how to approach the launch"
    echo "research the retention drop" | python -m shadow_os.cli --trace

Offline MockLLM by default (model-agnostic). Wire a real model in your own
script via Monarch(llm=...).
"""

from __future__ import annotations

import argparse
import json
import sys

from shadow_os.monarch import Monarch


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="shadow_os", description=__doc__)
    p.add_argument("directive", nargs="?", help="The directive. If omitted, read stdin.")
    p.add_argument("--personal", action="store_true", help="Allow Ira (personal-only) in the loadout.")
    p.add_argument("--trace", action="store_true", help="Print the run trace as JSON to stderr.")
    args = p.parse_args(argv)

    directive = args.directive if args.directive is not None else sys.stdin.read()
    directive = directive.strip()
    if not directive:
        p.error("no directive provided (argument or stdin)")

    task = Monarch().run(directive, context={"personal": args.personal})

    print(f"[class={task.task_class} · loadout={'->'.join(task.shadow_loadout)} · "
          f"γ={task.gamma.value} · {'SHIPPED' if task.shipped else 'VETOED'}]\n")
    print(task.final_output or "(vetoed — see governance trail)")
    if args.trace:
        print(json.dumps(task.trace(), indent=2), file=sys.stderr)
    return 0 if task.shipped else 1


if __name__ == "__main__":
    sys.exit(main())
