# Reconciliation — Monarch OS v1.1 (code) → Shadow OS v4 (spec)

What this repo currently *implements* (Monarch OS v1.1) versus what the canonical
spec ([`shadow-os-v4.md`](shadow-os-v4.md)) now requires. This is the map that
makes the v4 engine build (Option 1) mechanical instead of guesswork.

## TL;DR

The v1.1 code is **a single-agent pipeline**. Shadow OS v4 is **a fleet of 7
capability shadows orchestrated by Monarch**, each running its own 4-stage loop.
v1.1 is not wrong — it is a **subset**. Most of it survives as *primitives*
inside v4; the top-level shape changes from one pipeline to an orchestrator over
many loops.

| | Monarch OS v1.1 (current code) | Shadow OS v4 (target spec) |
|---|---|---|
| Top-level shape | One fixed pipeline | Monarch orchestrates a variable shadow loadout |
| Stages | Intake → Vajra → Caveman → QA → Ship | Perception → Memory → Reasoning → Action (per shadow) |
| "Monarch" means | The whole pipeline object | The kernel/orchestrator over the fleet |
| Agents | 1 (implicit) | 7 shadows (Thresher, Aegis, Axiom, Analyst, Quill, Ira) + Monarch |
| Memory | none | SKB triplets, TKL, decision ledger (Memory stage) |
| Routing | none (fixed flow) | regex-first Shadow Router + Task Classifier |
| Output discipline | Caveman + 11-Q QA | Caveman → a Thresher primitive; QA → release-gate (QA-0…8) |

## Stage mapping (v1.1 → v4)

| v1.1 stage | v1.1 module | v4 home |
|---|---|---|
| **Intake** (strip surface, bind context, reconstruct directive, route shadows) | `monarch/intake.py` | **Monarch · Perception + Sovereign Reconstruction** (4-pass intake, §3). Shadow routing already prototyped here — promote to the Shadow Router dispatch table (§7.1). |
| **Reasoning (Vajra)** | `monarch/reason.py` | The **Reasoning stage** every shadow runs (§2). v1.1's single Vajra prompt becomes the *shared Reasoning primitive*; each shadow specializes it. |
| **Caveman** (compress, preserve substance, tiers) | `monarch/caveman.py` | **Thresher** compression capability (§4.1, "signal compression", Phase-1 structural). Demoted from top-level stage to a Thresher primitive other shadows call. |
| **QA gate** (11-Q voice check) | `monarch/qa.py` | Split per §9.1: outbound **release-gate QA-0…8 → Thresher**; voice/standards → **Aegis**. Monarch still holds final ratify/veto (Invariant 7). |
| **Ship** | `monarch/pipeline.py` | **Action close + Artifact Delivery** (§7.5), now with RSI dual-output (Invariant 6). |
| **Constitution** (laws, invariants, register) | `monarch/constitution.py` | Superset → v4 **Governing Invariants (§1)** + per-shadow sealed laws (e.g. Aegis's 11 laws). |

## What v4 adds that v1.1 has nothing for

These are net-new and define the Option 1 build:

1. **The fleet.** 7 shadow modules, each with capabilities/deployment_triggers/guardrails as **data, not hardcoded personas** (Invariant 1, capability-first).
2. **The 4-stage loop controller** — generic `Perception → Memory → Reasoning → Action`, looping until Reasoning declares goal met, Monarch holds termination veto.
3. **Monarch orchestrator** — classify → route loadout → sequence → arbitrate conflict → ratify/veto → log. v1.1's pipeline is closest to this but governs only itself.
4. **Memory stage** — SKB triplets, TKL entries, decision ledger. v1.1 is stateless.
5. **Shadow Router + Task Classifier** — regex-first, zero-API-cost routing (§7.1–7.2). v1.1's `_SHADOW_KEYWORDS` is the seed.
6. **RSI dual-output** — every run emits deliverable **+** upgrade artifact (Invariant 6). v1.1 emits output only.
7. **γ calibration** (System 1 vs System 2) and **confidence scoring matched to evidence tier**.
8. **Guardrails as first-class** — "import the function, not the pathology" (Invariant 5). Each decoded capability ships its failure-mode governor.

## What stays as-is (reuse, don't rebuild)

- `caveman.py` — the byte-for-byte preservation + filler/forbidden-register logic is exactly Thresher's compression primitive. Keep, re-home.
- `llm.py` — model-agnostic interface (Invariant: model-agnostic) carries straight over to shadow execution.
- `state.py` — `PipelineState` generalizes into the v4 `Task` entity (§7 data model).
- The QA check mechanism — re-point `VOICE_CHECKS` to the release-gate QA-0…8 + Aegis voice/standards split.

## Open decisions that block clean module boundaries

From spec §9 — these need answers before/while building Option 1:

- **§9.1 Standards overlap (Thresher vs Aegis gating).** Drives whether QA lives in one module or two. *Recommendation: consolidate gating under Thresher (release QA-0…8); Aegis keeps inbound conceptual/content standards + commercial + IP.*
- **§9.2 Kernel tier.** Whether to add scheduler/context/memory/tool/access managers (the true AIOS tier, §8). For Option 1, build the cognitive layer first; stub the kernel seams.
- **§9.4 Ira scope.** Keep Ira personal-only → it must be excludable from any client-facing loadout by the router.

## Build order implied by this map (Option 1)

1. Generalize `PipelineState` → `Task`; add the 4-stage loop controller.
2. Shadow base (capabilities/triggers/guardrails as data) + the 6 shadow configs.
3. Monarch orchestrator: classifier → router → sequencer → ratify/veto.
4. Re-home Caveman into Thresher; split QA into Thresher release-gate + Aegis standards.
5. Memory stage (SKB/TKL/ledger) — in-process first, persistence later (§9.2).
6. RSI dual-output on every run.
7. Tests + an updated demo that routes a directive through a real loadout.
