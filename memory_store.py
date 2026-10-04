"""In memory graph store built on networkx. Used for tests, offline runs and quick demonstrations."""
from __future__ import annotations

from collections import Counter

import networkx as nx

from aegis_rmf.graph.base import FORWARD, GraphStore


class MemoryGraphStore(GraphStore):
    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()

    def upsert_node(self, label: str, node_id: str, properties: dict) -> None:
        self.check(label=label)
        existing = self.graph.nodes[node_id] if node_id in self.graph else {}
        self.graph.add_node(node_id, **{**existing, **properties, "label": label})

    def upsert_edge(self, source_id: str, relationship: str, target_id: str, properties: dict | None = None) -> None:
        self.check(relationship=relationship)
        for node_id in (source_id, target_id):
            if node_id not in self.graph:
                raise KeyError(f"Cannot link missing node {node_id}")
        self.graph.add_edge(source_id, target_id, key=relationship, **(properties or {}))

    def get_node(self, node_id: str) -> dict | None:
        if node_id not in self.graph:
            return None
        return {"id": node_id, **self.graph.nodes[node_id]}

    def find_nodes(self, label: str) -> list[dict]:
        self.check(label=label)
        return [{"id": n, **data} for n, data in sorted(self.graph.nodes(data=True)) if data.get("label") == label]

    def neighbors(self, node_id: str, relationship: str | None = None, direction: str = FORWARD) -> list[tuple[dict, str, dict]]:
        if node_id not in self.graph:
            return []
        if direction == FORWARD:
            edges = [(target, key, data) for _, target, key, data in self.graph.out_edges(node_id, keys=True, data=True)]
        else:
            edges = [(source, key, data) for source, _, key, data in self.graph.in_edges(node_id, keys=True, data=True)]
        found = [(self.get_node(other), key, dict(data)) for other, key, data in edges if relationship in (None, key)]
        return sorted(found, key=lambda item: (item[0]["id"], item[1]))

    def clear(self) -> None:
        self.graph.clear()

    def stats(self) -> dict:
        nodes = Counter(data.get("label", "") for _, data in self.graph.nodes(data=True))
        edges = Counter(key for _, _, key in self.graph.edges(keys=True))
        return {"nodes": dict(sorted(nodes.items())), "relationships": dict(sorted(edges.items()))}
