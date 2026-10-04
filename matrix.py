"""Build the ISO 14971 traceability matrix by walking the knowledge graph.

The matrix is derived from the graph and not from the in process records, so what is exported
is exactly what an auditor would obtain by querying the graph database directly.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from aegis_rmf.graph.base import BACKWARD, FORWARD, GraphStore

SHORT = {"occurrence": "P", "detectability": "D", "severity": "S"}


class TraceRow(BaseModel):
    risk_id: str
    title: str
    component_id: str
    component_name: str
    subsystem: str
    failure_mode_id: str
    failure_mode: str
    cause: str
    hazard: str
    hazardous_situation_id: str
    hazardous_situation: str
    harm_id: str
    harm: str
    detection_method: str
    severity_pre: int
    probability_pre: int
    detectability_pre: int
    rpn_pre: int
    region_pre: str
    priority_pre: str
    probability_basis: str
    field_matched_count: int
    controls: list[str] = Field(default_factory=list)
    control_ids: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)
    verification_refs: list[str] = Field(default_factory=list)
    severity_post: int
    probability_post: int
    detectability_post: int
    rpn_post: int
    region_post: str
    priority_post: str
    rpn_reduction_pct: float
    disposition: str
    design_refs: list[str] = Field(default_factory=list)
    standard_refs: list[str] = Field(default_factory=list)
    incident_refs: list[str] = Field(default_factory=list)


class ClauseCoverage(BaseModel):
    key: str
    designation: str
    clause: str
    topic: str
    risk_items: int
    requirements: int
    document_sections: list[str]
    status: str


def _first(nodes: list[dict], what: str, risk_id: str) -> dict:
    if not nodes:
        raise ValueError(f"Broken trace: {risk_id} has no {what}")
    return nodes[0]


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def build_row(store: GraphStore, risk: dict) -> TraceRow:
    risk_id = risk["id"]
    situation = _first(store.into(risk_id, "ASSESSED_AS"), "hazardous situation", risk_id)
    failure_mode = _first(store.into(situation["id"], "LEADS_TO"), "failure mode", risk_id)
    component = _first(store.into(failure_mode["id"], "HAS_FAILURE_MODE"), "component", risk_id)
    harm = _first(store.out(risk_id, "FOR_HARM"), "harm", risk_id)
    if harm["id"] not in {node["id"] for node in store.out(situation["id"], "RESULTS_IN")}:
        raise ValueError(f"Broken trace: {risk_id} harm does not match its hazardous situation")
    hazard = _first(store.out(situation["id"], "INVOLVES_HAZARD"), "hazard", risk_id)

    controls, control_ids, requirement_ids, verification_refs = [], [], [], []
    design_refs = [risk["source_ref"]]
    standard_refs = [node["key"] for node in store.out(risk_id, "GOVERNED_BY")]
    for control, _, edge in store.neighbors(risk_id, "CONTROLLED_BY", FORWARD):
        credit = " ".join(
            f"{SHORT[name]}{edge.get(f'credited_{name}', 0)}" for name in SHORT if edge.get(f"claimed_{name}", 0)
        )
        controls.append(
            f"{control['id']} {control['name']} [{control['control_type'].replace('_', ' ')}, "
            f"verification {edge['verification_status']}, credited {credit}]"
        )
        control_ids.append(control["id"])
        for requirement in store.out(control["id"], "IMPLEMENTED_BY"):
            requirement_ids.append(requirement["id"])
            design_refs.append(f"{requirement['id']} at {requirement['source_ref'].split(' (')[0]}")
            standard_refs += [node["key"] for node in store.out(requirement["id"], "COMPLIES_WITH")]
            records = store.out(requirement["id"], "VERIFIED_BY")
            if records:
                verification_refs += [f"{v['id']} {v['result']} {v['report']}" for v in records]
            else:
                verification_refs.append(f"{requirement['id']} has no verification record")

    return TraceRow(
        risk_id=risk_id, title=risk["title"], component_id=component["id"], component_name=component["name"],
        subsystem=component["subsystem"], failure_mode_id=failure_mode["id"], failure_mode=failure_mode["name"],
        cause=failure_mode["cause"], hazard=hazard["name"], hazardous_situation_id=situation["id"],
        hazardous_situation=situation["name"], harm_id=harm["id"], harm=harm["name"],
        detection_method=risk["detection_method"],
        severity_pre=risk["severity_pre"], probability_pre=risk["probability_pre"],
        detectability_pre=risk["detectability_pre"], rpn_pre=risk["rpn_pre"], region_pre=risk["region_pre"],
        priority_pre=risk["priority_pre"], probability_basis=risk["probability_basis"],
        field_matched_count=risk["field_matched_count"],
        controls=controls, control_ids=control_ids, requirement_ids=_unique(requirement_ids),
        verification_refs=_unique(verification_refs),
        severity_post=risk["severity_post"], probability_post=risk["probability_post"],
        detectability_post=risk["detectability_post"], rpn_post=risk["rpn_post"], region_post=risk["region_post"],
        priority_post=risk["priority_post"], rpn_reduction_pct=risk["rpn_reduction_pct"],
        disposition=risk["disposition"], design_refs=_unique(design_refs),
        standard_refs=sorted(set(standard_refs)),
        incident_refs=[node["id"] for node in store.out(risk_id, "SUPPORTED_BY")],
    )


def build_matrix(store: GraphStore) -> list[TraceRow]:
    """One row per RiskItem, ordered by risk identifier."""
    return [build_row(store, risk) for risk in store.find_nodes("RiskItem")]


def standards_coverage(store: GraphStore) -> list[ClauseCoverage]:
    """For each catalogue clause, the evidence in the file that addresses it."""
    coverage = []
    for clause in store.find_nodes("StandardClause"):
        risks = store.into(clause["id"], "GOVERNED_BY")
        requirements = store.into(clause["id"], "COMPLIES_WITH")
        sections = [node["name"] for node in store.into(clause["id"], "CITES")]
        evidenced = bool(risks or requirements or sections)
        coverage.append(ClauseCoverage(
            key=clause["key"], designation=clause["designation"], clause=clause["clause"], topic=clause["topic"],
            risk_items=len(risks), requirements=len(requirements), document_sections=sections,
            status="Evidenced" if evidenced else "No evidence in file",
        ))
    return sorted(coverage, key=lambda c: (c.designation, [int(part) for part in c.clause.split(".")]))


def verify_bidirectional(store: GraphStore) -> dict:
    """Check that every forward link from component to verification can be walked back again."""
    checked, broken = 0, []
    forward_cache: dict[str, dict[str, list[str]]] = {}
    backward_cache: dict[str, dict[str, list[str]]] = {}
    for risk in store.find_nodes("RiskItem"):
        row = build_row(store, risk)
        if row.component_id not in forward_cache:
            forward_cache[row.component_id] = store.trace(row.component_id, FORWARD)
        forward = forward_cache[row.component_id]
        for control_id in row.control_ids:
            for requirement in store.out(control_id, "IMPLEMENTED_BY"):
                targets = [requirement["id"]] + [v["id"] for v in store.out(requirement["id"], "VERIFIED_BY")]
                for target in targets:
                    checked += 1
                    label = "Requirement" if target.startswith("REQ_") else "Verification"
                    if target not in backward_cache:
                        backward_cache[target] = store.trace(target, BACKWARD)
                    back = backward_cache[target]
                    if target not in forward.get(label, []) or row.component_id not in back.get("Component", []) \
                            or row.risk_id not in back.get("RiskItem", []):
                        broken.append(f"{row.component_id} to {target} through {row.risk_id}")
    return {"links_checked": checked, "broken_links": broken, "bidirectional": not broken}
