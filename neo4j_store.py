"""Neo4j graph store.

Every node carries the shared label Entity next to its own label, and Entity.id is unique.
Labels and relationship types cannot be passed as Cypher parameters, so they are checked
against a fixed whitelist before they are placed in a query.
"""
from __future__ import annotations

import time
from importlib import resources

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

from aegis_rmf.graph.base import FORWARD, LABELS, GraphStore


def _clean(properties: dict | None) -> dict:
    """Neo4j properties must be primitives or lists of primitives."""
    cleaned = {}
    for key, value in (properties or {}).items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            cleaned[key] = value
        elif isinstance(value, (list, tuple)):
            cleaned[key] = [str(item) for item in value]
        else:
            cleaned[key] = str(value)
    return cleaned


class Neo4jGraphStore(GraphStore):
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j", connect_retries: int = 15) -> None:
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        self._connect(connect_retries)
        self.apply_schema()

    def _connect(self, retries: int) -> None:
        """Wait for the server, which can take some seconds to accept connections after a container starts."""
        for attempt in range(retries + 1):
            try:
                self.driver.verify_connectivity()
                return
            except ServiceUnavailable:
                if attempt == retries:
                    raise
                time.sleep(2.0)

    def _run(self, query: str, **parameters) -> list[dict]:
        with self.driver.session(database=self.database) as session:
            return [record.data() for record in session.run(query, **parameters)]

    def apply_schema(self) -> None:
        schema = resources.files("aegis_rmf.graph").joinpath("cypher/schema.cypher").read_text(encoding="utf8")
        for statement in schema.split(";"):
            lines = [line for line in statement.splitlines() if line.strip() and not line.strip().startswith("//")]
            if lines:
                self._run("\n".join(lines))

    def upsert_node(self, label: str, node_id: str, properties: dict) -> None:
        self.check(label=label)
        self._run(f"MERGE (n:Entity {{id: $id}}) SET n:{label}, n += $properties", id=node_id, properties=_clean(properties))

    def upsert_edge(self, source_id: str, relationship: str, target_id: str, properties: dict | None = None) -> None:
        self.check(relationship=relationship)
        result = self._run(
            f"MATCH (a:Entity {{id: $source}}), (b:Entity {{id: $target}}) "
            f"MERGE (a)-[r:{relationship}]->(b) SET r += $properties RETURN count(r) AS linked",
            source=source_id, target=target_id, properties=_clean(properties),
        )
        if not result or result[0]["linked"] == 0:
            raise KeyError(f"Cannot link {source_id} to {target_id}: a node is missing")

    @staticmethod
    def _node(properties: dict, labels: list[str]) -> dict:
        label = next((name for name in labels if name in LABELS), "")
        return {**properties, "label": label}

    def get_node(self, node_id: str) -> dict | None:
        rows = self._run("MATCH (n:Entity {id: $id}) RETURN properties(n) AS properties, labels(n) AS labels", id=node_id)
        return self._node(rows[0]["properties"], rows[0]["labels"]) if rows else None

    def find_nodes(self, label: str) -> list[dict]:
        self.check(label=label)
        rows = self._run(f"MATCH (n:{label}) RETURN properties(n) AS properties, labels(n) AS labels ORDER BY n.id")
        return [self._node(row["properties"], row["labels"]) for row in rows]

    def neighbors(self, node_id: str, relationship: str | None = None, direction: str = FORWARD) -> list[tuple[dict, str, dict]]:
        if relationship is not None:
            self.check(relationship=relationship)
        pattern = f"[r:{relationship}]" if relationship else "[r]"
        arrow = f"(a:Entity {{id: $id}})-{pattern}->(b)" if direction == FORWARD else f"(a:Entity {{id: $id}})<-{pattern}-(b)"
        rows = self._run(
            f"MATCH {arrow} RETURN properties(b) AS properties, labels(b) AS labels, type(r) AS relationship, "
            f"properties(r) AS edge ORDER BY b.id, relationship",
            id=node_id,
        )
        return [(self._node(row["properties"], row["labels"]), row["relationship"], row["edge"]) for row in rows]

    def clear(self) -> None:
        self._run("MATCH (n:Entity) DETACH DELETE n")

    def stats(self) -> dict:
        nodes = self._run(
            "MATCH (n:Entity) UNWIND labels(n) AS label WITH label WHERE label <> 'Entity' "
            "RETURN label, count(*) AS total ORDER BY label"
        )
        edges = self._run("MATCH (:Entity)-[r]->(:Entity) RETURN type(r) AS relationship, count(*) AS total ORDER BY relationship")
        return {
            "nodes": {row["label"]: row["total"] for row in nodes},
            "relationships": {row["relationship"]: row["total"] for row in edges},
        }

    def close(self) -> None:
        self.driver.close()
