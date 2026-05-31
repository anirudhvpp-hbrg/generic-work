"""The Memory stage backing store (spec section 2 Memory, section 7 data model).

In-process implementation: SKB triplets (state->action->next_state), TKL entries
(task_class -> the loadout that worked), and a decision ledger. This is the thin,
app-specific slice the spec (section 8) notes would be backed by an AIOS Memory/Storage
Manager in a true kernel build. Persistence is a later concern (section 9.2).

Invariant 8 (compression-before-deposit) is enforced at the deposit boundary:
units are compressed via the Caveman primitive before they enter the store.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from monarch.caveman import compress  # reuse the v1.1 compression primitive
from monarch.state import Tier


@dataclass
class SKBTriplet:
    state: str
    action: str
    next_state: str
    outcome: str
    belief_provenance: str = "run"


@dataclass
class TKLEntry:
    task_class: str
    loadout: List[str]
    hits: int = 1
    hit_rate: float = 1.0


@dataclass
class MemoryUnit:
    text: str
    confidence: float = 0.5
    belief_provenance: str = "run"


class Memory:
    """Semantic recall for the Memory stage. Not infrastructure persistence."""

    def __init__(self) -> None:
        self.skb: List[SKBTriplet] = []
        self.tkl: Dict[str, TKLEntry] = {}
        self.ledger: List[MemoryUnit] = []

    # --- recall (Memory stage reads) ---------------------------------------

    def recall_loadout(self, task_class: str) -> Optional[List[str]]:
        """Return the loadout that previously solved this task-class, if any."""
        entry = self.tkl.get(task_class)
        return list(entry.loadout) if entry else None

    def recall_context(self, task_class: str, limit: int = 5) -> List[MemoryUnit]:
        relevant = [u for u in self.ledger if task_class in u.text]
        return relevant[-limit:]

    # --- deposit (Memory stage writes; Invariant 8) ------------------------

    def log_run(self, task_class: str, loadout: List[str], success: bool) -> None:
        entry = self.tkl.get(task_class)
        if entry is None:
            self.tkl[task_class] = TKLEntry(task_class, list(loadout))
            return
        entry.hits += 1
        # rolling hit-rate
        entry.hit_rate = ((entry.hit_rate * (entry.hits - 1)) + (1.0 if success else 0.0)) / entry.hits
        if success:
            entry.loadout = list(loadout)

    def deposit(self, text: str, confidence: float = 0.5, provenance: str = "run") -> MemoryUnit:
        """Compress before deposit (Invariant 8), then store."""
        compressed = compress(text, Tier.FULL)
        unit = MemoryUnit(text=compressed, confidence=confidence, belief_provenance=provenance)
        self.ledger.append(unit)
        return unit

    def record_skb(self, state: str, action: str, next_state: str, outcome: str) -> None:
        self.skb.append(SKBTriplet(state, action, next_state, outcome))
