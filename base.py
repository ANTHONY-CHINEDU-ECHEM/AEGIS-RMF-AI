"""Graph store contract and the traversals shared by every backend.

Backends implement seven primitives. Traceability logic is written once against those primitives,
so the in memory store used in tests and the Neo4j store used in production behave identically.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque

LABELS = {
    "Component", "FailureMode", "HazardousSituation", "Hazard", "Harm", "RiskItem", "ControlMeasure",
    "Requirement", "Verification", "StandardClause", "DocumentSection", "Incident",
}
RELATIONSHIPS = {
    "HAS_FAILURE_MODE", "LEADS_TO", "RESULTS_IN", "INVOLVES_HAZARD", "ASSESSED_AS", "FOR_HARM",
    "CONTROLLED_BY", "IMPLEMENTED_BY", "VERIFIED_BY", "COMPLIES_WITH", "GOVERNED_BY", "SUPPORTED_BY",
    "DOCUMENTED_IN", "HAS_REQUIREMENT", "CITES",
}
FORWARD, BACKWARD = "forward", "backward"


class GraphStore(ABC):
    """Property graph of uniquely identified nodes and typed, directed relationships."""

    @abstractmethod
    def upsert_node(self, label: str, node_id: str, properties: dict) -> None: ...

    @abstractmethod
    def upsert_edge(self, source_id: str, relationship: str, target_id: str, properties: dict | None = None) -> None: ...

    @abstractmethod
    def get_node(self, node_id: str) -> dict | None:
        """Return the node properties plus the keys id and label, or None."""

    @abstractmethod
    def find_nodes(self, label: str) -> list[dict]:
        """Return all nodes with the label, ordered by id."""

    @abstractmethod
    def neighbors(self, node_id: str, relationship: str | None = None, direction: str = FORWARD) -> list[tuple[dict, str, dict]]:
        """Return (node, relationship, edge properties) for adjacent nodes, ordered by node id."""

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def stats(self) -> dict:
        """Return node counts by label and relationship counts by type."""

    def close(self) -> None:  # noqa: B027
        """Release backend resources. Backends without resources keep this default."""

    @staticmethod
    def check(label: str | None = None, relationship: str | None = None) -> None:
        if label is not None and label not in LABELS:
            raise ValueError(f"Unknown node label: {label!r}")
        if relationship is not None and relationship not in RELATIONSHIPS:
            raise ValueError(f"Unknown relationship type: {relationship!r}")

    def out(self, node_id: str, relationship: str) -> list[dict]:
        return [node for node, _, _ in self.neighbors(node_id, relationship, FORWARD)]

    def into(self, node_id: str, relationship: str) -> list[dict]:
        return [node for node, _, _ in self.neighbors(node_id, relationship, BACKWARD)]

    def trace(self, node_id: str, direction: str = FORWARD) -> dict[str, list[str]]:
        """Breadth first trace from a node. Returns reachable node ids grouped by label."""
        if self.get_node(node_id) is None:
            raise KeyError(node_id)
        seen, queue = {node_id}, deque([node_id])
        reached: dict[str, list[str]] = {}
        while queue:
            current = queue.popleft()
            for node, _, _ in self.neighbors(current, None, direction):
                if node["id"] not in seen:
                    seen.add(node["id"])
                    reached.setdefault(node["label"], []).append(node["id"])
                    queue.append(node["id"])
        return {label: sorted(ids) for label, ids in sorted(reached.items())}
