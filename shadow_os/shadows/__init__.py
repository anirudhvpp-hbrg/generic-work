"""The shadow fleet. Capability-first runners; configured by data, not persona."""

from shadow_os.shadows.base import Shadow, Reasoning
from shadow_os.shadows.thresher import Thresher
from shadow_os.shadows.aegis import Aegis
from shadow_os.shadows.axiom import Axiom
from shadow_os.shadows.analyst import Analyst
from shadow_os.shadows.quill import Quill
from shadow_os.shadows.ira import Ira

__all__ = [
    "Shadow", "Reasoning",
    "Thresher", "Aegis", "Axiom", "Analyst", "Quill", "Ira",
]


def build_fleet(llm):
    """Instantiate every shadow against one LLM, keyed by id."""
    return {s.id: s for s in (
        Thresher(llm), Aegis(llm), Axiom(llm), Analyst(llm), Quill(llm), Ira(llm),
    )}
