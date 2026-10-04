"""Load the clause catalogue used for regulatory cross references."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class StandardClause(BaseModel):
    key: str
    designation: str
    standard_title: str
    edition: str
    clause: str
    topic: str
    summary: str

    @property
    def node_id(self) -> str:
        return "CLAUSE_" + self.key.replace(" cl ", "_").replace(" ", "").replace(".", "_")

    def text(self) -> str:
        return f"{self.designation} clause {self.clause}. {self.topic}. {self.summary}"


def load_standards(path: Path) -> dict[str, StandardClause]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf8"))["standards"]
    clauses: dict[str, StandardClause] = {}
    for designation, spec in raw.items():
        for clause, body in spec["clauses"].items():
            key = f"{designation} cl {clause}"
            clauses[key] = StandardClause(
                key=key, designation=designation, standard_title=spec["title"], edition=str(spec["edition"]),
                clause=str(clause), topic=body["topic"], summary=body["summary"],
            )
    return clauses
