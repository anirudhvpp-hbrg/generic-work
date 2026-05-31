"""Run a prompt through the Monarch OS pipeline.

    python -m monarch.cli "walk me through why retention dipped"
    echo "draft this email" | python -m monarch.cli --trace

By default it uses the offline MockLLM (Invariant 11: model-agnostic). Wire a
real model by importing Monarch with a custom ``llm`` in your own script.
"""

from __future__ import annotations

import argparse
import json
import sys

from monarch.pipeline import Monarch


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="monarch", description=__doc__)
    parser.add_argument(
        "request",
        nargs="?",
        help="The prompt. If omitted, read from stdin.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Print the full pipeline audit trail as JSON to stderr.",
    )
    parser.add_argument(
        "--max-qa-attempts",
        type=int,
        default=3,
        help="Recompress/reship cycles before shipping best effort.",
    )
    args = parser.parse_args(argv)

    request = args.request if args.request is not None else sys.stdin.read()
    request = request.strip()
    if not request:
        parser.error("no request provided (argument or stdin)")

    state = Monarch(max_qa_attempts=args.max_qa_attempts).run(request)

    print(state.output)
    if args.trace:
        print(json.dumps(state.trace(), indent=2), file=sys.stderr)

    # Invariant 17: nothing ships unless QA passes.
    return 0 if state.shipped else 1


if __name__ == "__main__":
    sys.exit(main())
