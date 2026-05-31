# Shadow OS — Capability-First Cognitive Engine

> **Canonical spec:** [`docs/shadow-os-v4.md`](docs/shadow-os-v4.md) ·
> **Visual map:** [`docs/architecture.html`](docs/architecture.html) ·
> **Code↔spec map:** [`docs/reconciliation-v1.1-to-v4.md`](docs/reconciliation-v1.1-to-v4.md)

**Shadow OS v4** is a capability-first agent cognitive layer: 7 shadows
(Thresher, Aegis, Axiom, Analyst, Quill, Ira) orchestrated by **Monarch**, each
running one loop — **Perception → Memory → Reasoning → Action**. It runs *on top
of* an AIOS-style kernel; it is not itself AIOS (see spec section 8).

**Status:** the spec (v4) is canonical and the engine is implemented in
`shadow_os/`. The older `monarch/` package implements **Monarch OS v1.1** — a
single-agent pipeline whose stages (Caveman, QA, the model interface) are reused
by v4 as primitives. See the reconciliation note for the full map.

---

## Shadow OS v4 — the engine (`shadow_os/`)

7 shadows orchestrated by Monarch, each running **Perception → Memory →
Reasoning → Action**. Capability-first: shadows are configured by data
(capabilities, deployment triggers, guardrails), not hardcoded personas.

```python
from shadow_os import Monarch

monarch = Monarch()                       # offline MockLLM by default
task = monarch.run("tighten this bloated proposal deck")

print(task.final_output)   # ratified by Thresher's gate, then shipped
print(task.trace())        # task_class, loadout, γ, RSI artifacts, governance
```

```bash
python -m shadow_os.cli "research why retention dropped" --trace
python -m shadow_os.cli --personal "I'm stuck on how to approach the launch"
python examples/run_engine.py      # routes 5 directives across the fleet
```

**What it does, mapped to the spec:**

| Piece | Module | Spec |
|-------|--------|------|
| Monarch orchestrator (reconstruct → classify → route → sequence → ratify → log) | `shadow_os/monarch.py` | section 3 |
| 4-stage loop (capability-first base) | `shadow_os/shadows/base.py` | section 2 |
| 7 shadows (Thresher, Aegis, Axiom, Analyst, Quill, Ira) | `shadow_os/shadows/` | section 4 |
| Regex-first router + task classifier | `shadow_os/router.py` | section 7.1–7.2 |
| Memory: SKB / TKL / decision ledger | `shadow_os/memory.py` | section 2, section 7 |
| Task entity + RSI + governance | `shadow_os/task.py` | section 7 |
| 8 Governing Invariants + Socratic gate | `shadow_os/invariants.py` | section 1, section 3 |

**Decisions baked in:** gating is consolidated in **Thresher** (section 9.1); **Ira** is
personal-only and never enters a non-personal loadout (section 9.4); Caveman is reused
as Thresher's compression primitive (not duplicated). Invariant 7 (Monarch
absolute) is enforced — nothing ships unless Thresher's gate ratifies it; every
run emits RSI dual-output (Invariant 6).

---

## The kernel — resource layer (`kernel/`)

The cognitive engine decides *which shadow reasons about what*. The kernel is the
AIOS-style resource layer beneath it: it decides *which request gets LLM, memory,
tools* and enforces per-agent access. Shadow OS runs **on** this kernel.

| Manager | Module | Role |
|---------|--------|------|
| LLM Core | `kernel/llm_core.py` | One shared model across agents, with usage accounting |
| Scheduler | `kernel/scheduler.py` | Priority ordering of dispatched agent jobs |
| Context Manager | `kernel/context.py` | Snapshot / restore an agent's loop state on context-switch |
| Storage + Memory | `kernel/storage.py` | **Durable** atomic-write store + LRU memory with semantic search |
| Tool Manager | `kernel/tools.py` | Unified tool registry the Action stage calls into |
| Access Manager | `kernel/access.py` | Per-agent permissions |

```python
from kernel import Kernel
from shadow_os import Monarch

kernel = Kernel()
monarch = Monarch(kernel=kernel)        # boots the fleet onto the kernel
task = monarch.run("draft the proposal summary")

kernel.llm_core.usage()                 # {'calls': 3, ...} — shared, accounted
len(kernel.memory)                      # shipped output persisted
```

```bash
python examples/run_on_kernel.py        # full stack: accounting, access, scheduler
```

When Monarch is given a kernel, shadow completions go through the shared LLM
Core, each shadow is access-checked before it runs, its loop state is
snapshotted, and shipped output is persisted to kernel memory. The concrete
access example is enforced: the commercial agent (Aegis) may touch pipeline
data, the personal agent (Ira) may not.

### Durable storage

Give the kernel a `storage_path` and the resource layer is durable: every write
is flushed to disk atomically (temp file + `os.replace`, crash-safe), and a fresh
kernel on the same path rehydrates its memory. Memory also supports
dependency-free semantic `search` (token-overlap) — a stand-in a real embedding
backend can replace without changing callers.

```python
from kernel import Kernel
from shadow_os import Monarch

k1 = Kernel(storage_path="state.json")
Monarch(kernel=k1).run("research why retention dropped")

k2 = Kernel(storage_path="state.json")     # new process, same path
len(k2.memory)                             # rehydrated from disk
k2.memory.search("retention drop")         # [(key, record, score), ...]
```

### Notion-backed memory + embedding search

Memory can live in a **Notion database** instead of a local file — browsable and
editable in the same workspace as the specs. `NotionStorage` is a drop-in for the
disk store, and an `embedder` upgrades `search` from token overlap to **cosine
similarity over embeddings** (true semantic recall).

```python
from kernel import Kernel, NotionStorage, HttpNotionTransport, VoyageEmbedder
from shadow_os import Monarch

kernel = Kernel(
    storage=NotionStorage("YOUR_DATABASE_ID", HttpNotionTransport()),  # NOTION_TOKEN env
    embedder=VoyageEmbedder(),                                          # VOYAGE_API_KEY env
)
Monarch(kernel=kernel).run("research why retention dropped")
kernel.memory.search("why did churn rise")     # semantic — matches without shared words
```

- **Embedders are pluggable** (`embed(text) -> list[float]`): `HashEmbedder`
  (offline, deterministic, no key — the default/fallback) or `VoyageEmbedder`
  (real semantics; Anthropic has no embeddings API, so Voyage is the partner).
  OpenAI or a local model drop in the same way.
- **Notion transport is injectable**: `HttpNotionTransport` (live, standard-library
  HTTP) or `InMemoryNotionTransport` (offline tests). Tests use the in-memory one,
  so CI never touches the network.

**To go live** you provide: a Notion integration **token** (`NOTION_TOKEN`), a
**database ID** with a `Key` (title) and `Payload` (rich_text) property, and —
for real embeddings — `VOYAGE_API_KEY`. Without them the engine runs offline on
disk + `HashEmbedder` exactly as before.

Remaining kernel work: preemptive concurrency in the scheduler.

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
`complete(system, user) -> str`.

**Claude (built-in adapter):**

```bash
pip install -e ".[claude]"        # installs the anthropic SDK
export ANTHROPIC_API_KEY=sk-ant-...
python examples/run_with_claude.py "tighten this proposal deck"
```

```python
from shadow_os import Monarch
from monarch.claude_llm import ClaudeLLM

monarch = Monarch(llm=ClaudeLLM())   # Sonnet 4.6 default, Haiku for clear tasks
task = monarch.run("draft the Hexaware proposal summary")
```

`ClaudeLLM` **tiers by task**: **Sonnet 4.6** (adaptive thinking, `effort:
"high"`) for normal work, and **Haiku 4.5** for clear, simple prompts (short and
free of complexity markers — Haiku omits `effort`/`thinking`, which it doesn't
accept). It **caches each shadow's (stable) system prompt** (`cache_control:
ephemeral`) so repeated calls reuse the cached prefix. Tune via
`ClaudeLLM(model=..., simple_model=..., auto_tier=False, effort=..., max_tokens=...)`;
per-model usage is tracked on `llm.usage`.

**Any other provider:**

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
  derives 11 mechanical checks from section II/section III/section V; edit that list to match your
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
