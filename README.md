# Shadow OS — Capability-First Cognitive Engine

> **Canonical spec:** [`docs/shadow-os-v4.md`](docs/shadow-os-v4.md) ·
> **Visual map:** [`docs/architecture.html`](docs/architecture.html) ·
> **Code↔spec map:** [`docs/reconciliation-v1.1-to-v4.md`](docs/reconciliation-v1.1-to-v4.md)

**Shadow OS v4** is a capability-first agent cognitive layer: 7 shadows
(Thresher, Aegis, Axiom, Analyst, Quill, Ira) orchestrated by **Monarch**, each
running one loop — **Perception → Memory → Reasoning → Action**. It runs *on top
of* an AIOS-style kernel; it is not itself AIOS (see spec §8).

**Status:** the spec (v4) is canonical. The code in `monarch/` currently
implements **Monarch OS v1.1** — a single-agent pipeline that is a *subset* of
v4, being evolved into the full 7-shadow engine. See the reconciliation note for
exactly what maps where and what's missing.

---

## Monarch OS v1.1 — the current code (a v4 subset)

A runnable single-agent pipeline. Its stages become primitives inside v4
(Caveman → Thresher compression; QA → release-gate; Vajra → the Reasoning stage).

```
INTAKE → REASONING (Vajra) → OUTPUT (Caveman) → QA → SHIP
```

**Reasoning stays full. Output compresses. Nothing ships until QA passes.**

## The pipeline

| Stage | Module | What it does | Deterministic? |
|-------|--------|--------------|----------------|
| **Intake** | `intake.py` | Strip surface request → bind context → reconstruct directive → route shadows | yes |
| **Reasoning** | `reason.py` | Vajra substrate: taxonomy, Claim→Evidence→Implication→Kill condition, three layers | needs an LLM |
| **Caveman** | `caveman.py` | Strip filler, ban exclamation/forbidden register, preserve code/paths/URLs byte-for-byte, tier select | yes |
| **QA** | `qa.py` | 11-question voice check + invariants; hard stop, recompress on fail | yes |
| **Ship** | `pipeline.py` | Ship only when QA passes (Invariant 17) | yes |

The sealed Constitution (Five Laws, Eight Constants, Invariants, forbidden
register, Shadow Fleet) is data in `constitution.py`.

## Install

No required dependencies. Python 3.10–3.11.

```bash
pip install -e .
```

## Quickstart (offline)

```python
from monarch import Monarch

monarch = Monarch()                       # offline MockLLM by default
state = monarch.run("walk me through why retention dipped")

print(state.output)     # Caveman-compressed, QA-passed
print(state.trace())    # full audit trail (directive, shadows, tier, QA)
```

CLI:

```bash
python -m monarch.cli "draft the launch note" --trace
echo "tl;dr is it worth it" | python -m monarch.cli
```

See the whole pipeline stage-by-stage:

```bash
python examples/run_demo.py
```

## Wiring a real model

The reasoning stage is model-agnostic (Invariant 11). Pass anything with
`complete(system, user) -> str`:

```python
from monarch import Monarch, CallableLLM

def my_model(system, user):
    ...  # call your provider, return the text
    return text

monarch = Monarch(llm=CallableLLM(my_model))
```

## Caveman, precisely

- **Preserves substance byte-for-byte:** code blocks, inline code, file paths,
  URLs, and numbers are masked before any text transform and restored after.
- **Strips filler:** opener phrases ("Sure!", "I'd be happy to"), recap closers
  ("Hope this helps"), and pure-filler phrases anywhere.
- **Hard bans:** exclamation marks and the forbidden register (`sovereign`,
  `weapon`, `transcends`, …). Content-bearing forbidden terms that survive
  compression cause QA to **block the ship** rather than be silently deleted.
- **Tier selection:** Full (default) · Lite (emotional/crisis or override) ·
  Ultra (explicit `tl;dr`/`ultra`).

## What is faithful vs. derived

The implementation follows the spec exactly where it is concrete. Two parts the
spec names but does not fully enumerate are explicit extension points:

- **The 11 QA questions** — the spec mandates "11-question voice check" and
  states the Voice test but doesn't list the 11 verbatim. `qa.VOICE_CHECKS`
  derives 11 mechanical checks from §II/§III/§V; edit that list to match your
  canonical questions.
- **Shadow routing** — the Shadow Fleet roster is named in `constitution.py`;
  routing internals aren't specified, so `intake._SHADOW_KEYWORDS` is a simple
  keyword map you can extend.

## Tests

```bash
pytest          # 21 tests, no model required
```

Covers Caveman compression (filler, exclamation, byte-for-byte preservation,
tiers), intake routing, the 11-question QA gate, register detection, and
end-to-end ship/block behaviour.

## License

MIT
