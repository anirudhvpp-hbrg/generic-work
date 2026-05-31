"""Monarch OS launcher — one-shot or interactive, run locally.

    monarch-os                         # interactive shell
    monarch-os "tighten this deck"     # one directive, then exit
    monarch-os --personal "I'm stuck"  # allow the personal shadow (Ira)
    monarch-os --offline --trace ...   # force offline, show the audit trail

Equivalent: ``python -m monarchos [...]``.
"""

from __future__ import annotations

import argparse
import json
import sys

from monarchos.runtime import MonarchOS, boot


def _render(os_rt: MonarchOS, directive: str, personal: bool, trace: bool) -> bool:
    task = os_rt.run(directive, personal=personal)
    flag = "SHIPPED" if task.shipped else "VETOED"
    loadout = "->".join(task.shadow_loadout) or "-"
    print(f"\n[{flag}] class={task.task_class}  loadout={loadout}  gamma={task.gamma.value}")
    print("-" * 60)
    print(task.final_output or "(vetoed — see the governance trail with --trace)")
    if trace:
        print("\n--- trace ---", file=sys.stderr)
        print(json.dumps(task.trace(), indent=2), file=sys.stderr)
    return task.shipped


def _banner(os_rt: MonarchOS) -> None:
    s = os_rt.status()
    print("=" * 60)
    print("  Monarch OS — Shadow OS operating within it")
    print("=" * 60)
    print(f"  model : {s['model']}")
    print(f"  state : {s['state_path']}  ({s['memory_units']} memories)")
    print(f"  fleet : {', '.join(s['shadows'])}")
    print("  type a directive, or /help. /quit to exit.")
    print("-" * 60)


def _repl(os_rt: MonarchOS, personal: bool, trace: bool) -> int:
    _banner(os_rt)
    while True:
        try:
            line = input("monarch-os> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            return 0
        if not line:
            continue
        if line in ("/quit", "/exit", "/q"):
            print("bye.")
            return 0
        if line == "/help":
            print("  <text>         run a directive\n"
                  "  /personal      toggle the personal shadow (Ira)\n"
                  "  /trace         toggle the audit trail\n"
                  "  /status        show runtime status\n"
                  "  /quit          exit")
            continue
        if line == "/personal":
            personal = not personal
            print(f"  personal = {personal}")
            continue
        if line == "/trace":
            trace = not trace
            print(f"  trace = {trace}")
            continue
        if line == "/status":
            print(json.dumps(os_rt.status(), indent=2, default=str))
            continue
        _render(os_rt, line, personal, trace)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="monarch-os", description=__doc__)
    p.add_argument("directive", nargs="*", help="A directive. Omit for an interactive shell.")
    p.add_argument("--personal", action="store_true", help="Allow the personal shadow (Ira).")
    p.add_argument("--offline", action="store_true", help="Force the offline MockLLM.")
    p.add_argument("--trace", action="store_true", help="Print the audit trail.")
    p.add_argument("--state", metavar="PATH", help="Durable memory file (default ~/.monarchos/state.json).")
    p.add_argument("--ephemeral", action="store_true", help="Do not persist memory to disk.")
    p.add_argument("--model", help="Override the Claude model (e.g. claude-opus-4-8).")
    args = p.parse_args(argv)

    os_rt = boot(
        state_path=args.state,
        offline=args.offline,
        persist=not args.ephemeral,
        model=args.model,
    )

    directive = " ".join(args.directive).strip()
    if directive:
        shipped = _render(os_rt, directive, args.personal, args.trace)
        return 0 if shipped else 1
    return _repl(os_rt, args.personal, args.trace)


if __name__ == "__main__":
    sys.exit(main())
