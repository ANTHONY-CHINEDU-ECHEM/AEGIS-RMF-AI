"""Gap analysis: findings an auditor would raise against the risk management file."""
from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel

from aegis_rmf.graph.base import FORWARD, GraphStore

BLOCKER, MAJOR, ACTION = "BLOCKER", "MAJOR", "ACTION"
ORDER = {BLOCKER: 0, MAJOR: 1, ACTION: 2}


class Gap(BaseModel):
    rule: str
    level: str
    subject_id: str
    clause: str
    message: str


def find_gaps(store: GraphStore, field_lookup: Callable[[str], int] | None = None) -> list[Gap]:
    """Evaluate the gap rules. field_lookup returns the count of similar incidents for a text."""
    gaps: list[Gap] = []

    for component in store.find_nodes("Component"):
        if not store.out(component["id"], "HAS_FAILURE_MODE"):
            message = f"Component {component['id']} {component['name']} has no failure mode analysis"
            if field_lookup:
                count = field_lookup(component["name"])
                if count:
                    message += f", yet {count} similar incident reports exist in field data"
            gaps.append(Gap(rule="G1 component without hazard analysis", level=MAJOR, subject_id=component["id"],
                            clause="ISO 14971 cl 5.4", message=message))

    for risk in store.find_nodes("RiskItem"):
        risk_id = risk["id"]
        controls = store.neighbors(risk_id, "CONTROLLED_BY", FORWARD)
        if risk["region_pre"] != "ACCEPTABLE" and not controls:
            gaps.append(Gap(rule="G2 risk without control", level=MAJOR, subject_id=risk_id, clause="ISO 14971 cl 7.1",
                            message=f"{risk_id} is in the {risk['region_pre']} region before control and has no risk control measure"))
        for control, _, edge in controls:
            status = edge["verification_status"]
            if status == "MISSING":
                gaps.append(Gap(rule="G3 control without verification record", level=MAJOR, subject_id=control["id"],
                                clause="ISO 14971 cl 7.2",
                                message=f"{control['id']} for {risk_id} has an implementing requirement with no verification record, so no credit was given"))
            elif status in ("FAIL", "PENDING"):
                gaps.append(Gap(rule="G4 control verification not passed", level=BLOCKER if status == "FAIL" else MAJOR,
                                subject_id=control["id"], clause="ISO 14971 cl 7.2",
                                message=f"{control['id']} for {risk_id} has verification status {status}, so no credit was given"))
        if controls and risk["severity_pre"] >= 4 and all(c["control_type"] == "information_for_safety" for c, _, _ in controls):
            gaps.append(Gap(rule="G5 information for safety as sole control", level=MAJOR, subject_id=risk_id,
                            clause="ISO 14971 cl 7.1",
                            message=f"{risk_id} can cause critical or catastrophic harm and relies only on information for safety"))
        if risk["region_post"] == "UNACCEPTABLE":
            gaps.append(Gap(rule="G6 unacceptable residual risk", level=BLOCKER, subject_id=risk_id, clause="ISO 14971 cl 7.3",
                            message=f"{risk_id} residual risk is UNACCEPTABLE (severity {risk['severity_post']}, probability {risk['probability_post']})"))
        elif risk["region_post"] == "REVIEW":
            gaps.append(Gap(rule="G7 benefit risk analysis required", level=ACTION, subject_id=risk_id, clause="ISO 14971 cl 7.4",
                            message=f"{risk_id} residual risk is in the REVIEW region (severity {risk['severity_post']}, probability {risk['probability_post']})"))
        if risk["probability_basis"] == "field evidence":
            gaps.append(Gap(rule="G8 field data exceeds engineering estimate", level=MAJOR, subject_id=risk_id,
                            clause="ISO 14971 cl 10.4",
                            message=f"{risk_id} engineering probability {risk['engineering_probability']} was raised to "
                                    f"{risk['probability_pre']} by {risk['field_matched_count']} similar incident reports"))

    return sorted(gaps, key=lambda gap: (ORDER[gap.level], gap.rule, gap.subject_id))
