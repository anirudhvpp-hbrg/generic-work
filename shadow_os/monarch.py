"""Monarch — the orchestrator / kernel (spec section 3).

Runs the loop on the fleet, not on a problem:

    Sovereign Reconstruction -> classify -> route loadout -> sequence ->
    ratify (Thresher gate, Invariant 7) -> log governance + telemetry + RSI ->
    deposit to memory (Invariant 8).

Monarch holds absolute veto. Nothing ships unratified.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from monarch.llm import LLM, MockLLM
from shadow_os.memory import Memory
from shadow_os.router import ShadowRouter, TaskClassifier
from shadow_os.shadows import build_fleet
from shadow_os.shadows.thresher import Thresher
from shadow_os.task import DecisionType, Gamma, Task

# Heuristics for γ calibration (System 1 fast-path vs System 2 deliberate).
_HIGH_STAKES = re.compile(
    r"\b(irreversible|launch|fire|hire|contract|legal|architecture|strategy|bet|acquire)\b",
    re.I,
)


class Monarch:
    """The orchestrator. Decides which shadow reasons about what, then ratifies.

    Optionally runs on a resource ``kernel`` (the AIOS-style tier in the
    ``kernel`` package). When a kernel is supplied, shadow completions go through
    its shared LLM Core (usage accounting), each shadow is access-checked before
    it runs, its loop state is snapshotted on the kernel, and shipped output is
    persisted to kernel memory. Without a kernel, Monarch runs standalone.
    """

    def __init__(
        self,
        llm: Optional[LLM] = None,
        memory: Optional[Memory] = None,
        kernel: Any = None,
    ):
        self.kernel = kernel
        # When booted on a kernel, route model calls through its shared LLM Core.
        if kernel is not None and llm is None:
            self.llm = kernel.llm_core
        else:
            self.llm = llm or MockLLM()
        self.memory = memory or Memory()
        self.fleet = build_fleet(self.llm)
        self.classifier = TaskClassifier()
        self.router = ShadowRouter()
        if kernel is not None:
            from kernel.boot import boot_shadow_os
            boot_shadow_os(kernel, self)

    # --- Sovereign Reconstruction (4-pass intake, section 3) ----------------------

    def _reconstruct(self, task: Task) -> None:
        raw = task.raw_input.strip()
        # 1. intent extraction — strip surface politeness to the core ask
        intent = re.sub(
            r"^(hey|hi|hello|please|could you|can you|would you|i want you to|i need you to)\b[ ,:-]*",
            "", raw, flags=re.I,
        ).strip() or raw
        task.reconstructed_intent = intent
        # 2. belief construction — what must be true (the unasked third layer)
        task.beliefs = [
            "the surface ask is not the whole ask",
            "success depends on the unasked third layer",
        ]
        # 3. γ calibration — System 1 vs System 2
        high_stakes = bool(_HIGH_STAKES.search(raw)) or len(raw.split()) > 40
        task.gamma = Gamma.SYSTEM2 if high_stakes else Gamma.SYSTEM1
        task.decision_type = DecisionType.TYPE1 if high_stakes else DecisionType.TYPE2
        # 4. SNR enforcement
        task.snr_notes = "signal isolated; commodity framing stripped"

    # --- Run ---------------------------------------------------------------

    def run(self, directive: str, context: Optional[Dict[str, Any]] = None) -> Task:
        task = Task(raw_input=directive, context=dict(context or {}))

        # Perception + Sovereign Reconstruction
        self._reconstruct(task)
        task.log("intake", "sovereign reconstruction (intent/belief/γ/SNR)", True)

        # Classify + route loadout (Memory may recall a prior winning loadout)
        task.task_class = self.classifier.classify(task.reconstructed_intent)
        personal = bool(task.context.get("personal"))
        recalled = self.memory.recall_loadout(task.task_class)
        task.shadow_loadout = recalled or self.router.loadout(task.task_class, personal=personal)
        # Ira is personal-only — enforce even if recalled (section 9.4)
        if not personal:
            task.shadow_loadout = [s for s in task.shadow_loadout if s != "ira"] or ["thresher"]
        task.log("routing", f"loadout={task.shadow_loadout} (class={task.task_class})", True)

        # Sequence the loadout: each shadow's artifact feeds the next
        incoming = task.reconstructed_intent
        for shadow_id in task.shadow_loadout:
            shadow = self.fleet.get(shadow_id)
            if shadow is None:
                continue
            if self.kernel is not None:
                self.kernel.access.require(shadow_id, "execute")  # resource-layer gate
            result = shadow.run(task, self.memory, incoming=incoming)
            task.results[shadow_id] = result
            if result.rsi:
                task.rsi_artifacts.append(result.rsi)  # dual-output: deliverable + upgrade
            if self.kernel is not None:
                self.kernel.context.snapshot(
                    shadow_id, {"artifact": result.artifact, "confidence": result.confidence}
                )
            incoming = result.artifact  # thread forward
            task.log(shadow_id, f"loop done (conf={result.confidence})", True)

        # Candidate final output = last shadow's artifact
        last_id = task.shadow_loadout[-1] if task.shadow_loadout else None
        candidate = task.results[last_id].artifact if last_id in task.results else ""

        # Ratify via Thresher's consolidated release gate (Invariant 7)
        gate: Thresher = self.fleet["thresher"]
        passed, failures = gate.gate(candidate)
        task.ratified = passed
        task.shipped = passed
        task.final_output = candidate if passed else ""
        task.log(
            "ratification",
            "Monarch veto via Thresher gate: " + ("PASS" if passed else f"VETO {failures}"),
            passed,
        )

        # Telemetry + Memory deposit (Invariant 8: compression-before-deposit)
        task.telemetry = {
            "shadows_deployed": list(task.results.keys()),
            "gates_passed": passed,
            "gamma": task.gamma.value,
            "rsi_artifacts": len(task.rsi_artifacts),
        }
        self.memory.log_run(task.task_class, task.shadow_loadout, success=passed)
        if passed and candidate:
            self.memory.deposit(candidate, confidence=0.7, provenance=last_id or "run")
            # Persist to the kernel's storage-backed memory when running on one.
            if self.kernel is not None:
                key = f"{task.task_class}:{len(self.kernel.memory)}"
                self.kernel.syscall(
                    "monarch", "mem.write", key=key, text=candidate,
                    meta={"task_class": task.task_class, "gamma": task.gamma.value},
                )
                task.telemetry["kernel_llm_usage"] = self.kernel.llm_core.usage()

        return task
