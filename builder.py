"""Write the design corpus and the scored risk records into the knowledge graph.

The core chain is Component, FailureMode, HazardousSituation, Harm. Harm nodes are shared between
scenarios, so risk controls hang off a RiskItem node (one per hazard analysis row) rather than off
the harm. That keeps every control traceable to exactly the scenarios it mitigates.
"""
from __future__ import annotations

from aegis_rmf.domain import Dimension, RiskRecord
from aegis_rmf.graph.base import GraphStore
from aegis_rmf.ingestion.design_docs import DesignCorpus
from aegis_rmf.ingestion.standards import StandardClause


def section_id(doc_id: str, section: str) -> str:
    return f"SEC_{doc_id}_{section.replace('.', '_')}"


def risk_properties(record: RiskRecord) -> dict:
    properties = {
        "title": record.title, "dfc_id": record.dfc_id, "component_id": record.component_id,
        "detection_method": record.detection_method, "engineering_probability": record.engineering_probability,
        "probability_basis": record.probability_basis, "field_matched_count": record.field.matched_count,
        "field_injury_count": record.field.injury_count, "field_death_count": record.field.death_count,
        "field_rate_per_100k": record.field.rate_per_100k_device_years,
        "field_implied_probability": record.field.implied_probability,
        "rpn_reduction_pct": record.rpn_reduction_pct, "benefit_risk_required": record.benefit_risk_required,
        "disposition": record.disposition, "source_ref": record.source.label(),
    }
    for stage, risk_score in (("pre", record.pre), ("post", record.post)):
        properties.update({
            f"severity_{stage}": risk_score.severity, f"probability_{stage}": risk_score.probability,
            f"detectability_{stage}": risk_score.detectability, f"rpn_{stage}": risk_score.rpn,
            f"rpn_band_{stage}": risk_score.rpn_band, f"region_{stage}": risk_score.region.value,
            f"priority_{stage}": risk_score.action_priority.value,
        })
    return properties


def build_graph(
    store: GraphStore, corpus: DesignCorpus, records: list[RiskRecord], clauses: dict[str, StandardClause],
) -> list[str]:
    """Populate the store. Returns warnings for references that could not be resolved."""
    warnings: list[str] = []
    store.clear()

    for clause in clauses.values():
        store.upsert_node("StandardClause", clause.node_id, {
            "key": clause.key, "designation": clause.designation, "clause": clause.clause,
            "topic": clause.topic, "name": f"{clause.designation} cl {clause.clause} {clause.topic}",
        })

    def link_clause(source_id: str, relationship: str, key: str) -> None:
        if key in clauses:
            store.upsert_edge(source_id, relationship, clauses[key].node_id)
        else:
            warnings.append(f"{source_id} cites {key}, which is not in the standards catalogue")

    for unit in corpus.units:
        if unit.level > 3:
            continue
        node_id = section_id(unit.doc_id, unit.section)
        store.upsert_node("DocumentSection", node_id, {
            "doc_id": unit.doc_id, "section": unit.section, "heading": unit.heading,
            "name": f"{unit.doc_id} section {unit.section}",
        })
    for unit in corpus.units:
        for key in unit.citations():
            link_clause(section_id(unit.doc_id, unit.section), "CITES", key)

    for component in corpus.components.values():
        store.upsert_node("Component", component.id, {
            "name": component.name, "subsystem": component.subsystem, "software_class": component.software_class,
        })
        target = section_id(component.doc_id, component.section)
        if store.get_node(target):
            store.upsert_edge(component.id, "DOCUMENTED_IN", target)
        else:
            warnings.append(f"{component.id} points to missing section {component.doc_id} {component.section}")

    for verification in corpus.verifications.values():
        store.upsert_node("Verification", verification.id, {
            "name": verification.id, "method": verification.method,
            "result": verification.result.value, "report": verification.report,
        })

    for requirement in corpus.requirements.values():
        store.upsert_node("Requirement", requirement.id, {
            "name": requirement.id, "text": requirement.text, "component_id": requirement.component_id,
            "source_ref": requirement.source.label(),
        })
        if requirement.component_id in corpus.components:
            store.upsert_edge(requirement.component_id, "HAS_REQUIREMENT", requirement.id)
        store.upsert_edge(requirement.id, "DOCUMENTED_IN", section_id(requirement.source.doc_id, requirement.source.section))
        for key in requirement.standards:
            link_clause(requirement.id, "COMPLIES_WITH", key)
        if requirement.verification_id:
            if requirement.verification_id in corpus.verifications:
                store.upsert_edge(requirement.id, "VERIFIED_BY", requirement.verification_id)
            else:
                warnings.append(f"{requirement.id} cites missing verification record {requirement.verification_id}")

    for record in records:
        store.upsert_node("FailureMode", record.failure_mode_id, {"name": record.failure_mode, "cause": record.cause})
        store.upsert_node("HazardousSituation", record.hazardous_situation_id, {"name": record.hazardous_situation})
        store.upsert_node("Hazard", record.hazard_id, {"name": record.hazard})
        store.upsert_node("Harm", record.harm_id, {"name": record.harm, "severity": record.pre.severity})
        store.upsert_node("RiskItem", record.risk_id, {"name": record.risk_id, **risk_properties(record)})
        store.upsert_edge(record.component_id, "HAS_FAILURE_MODE", record.failure_mode_id)
        store.upsert_edge(record.failure_mode_id, "LEADS_TO", record.hazardous_situation_id)
        store.upsert_edge(record.hazardous_situation_id, "RESULTS_IN", record.harm_id)
        store.upsert_edge(record.hazardous_situation_id, "INVOLVES_HAZARD", record.hazard_id)
        store.upsert_edge(record.hazardous_situation_id, "ASSESSED_AS", record.risk_id)
        store.upsert_edge(record.risk_id, "FOR_HARM", record.harm_id)
        store.upsert_edge(record.failure_mode_id, "DOCUMENTED_IN", section_id(record.source.doc_id, record.source.section))
        for key in record.clause_refs:
            link_clause(record.risk_id, "GOVERNED_BY", key)
        for credit in record.controls:
            store.upsert_node("ControlMeasure", credit.control_id, {
                "name": credit.description, "control_type": credit.control_type.value,
            })
            edge = {"verification_status": credit.verification_status.value, "notes": "; ".join(credit.notes)}
            for dimension in Dimension:
                edge[f"claimed_{dimension.value}"] = credit.claimed.get(dimension, 0)
                edge[f"credited_{dimension.value}"] = credit.credited.get(dimension, 0)
            store.upsert_edge(record.risk_id, "CONTROLLED_BY", credit.control_id, edge)
            for requirement_id in credit.requirement_ids:
                store.upsert_edge(credit.control_id, "IMPLEMENTED_BY", requirement_id)
        for evidence in record.field.evidence:
            store.upsert_node("Incident", evidence.report_number, {
                "name": evidence.report_number, "event_type": evidence.event_type,
                "product_problem": evidence.product_problem,
            })
            store.upsert_edge(record.risk_id, "SUPPORTED_BY", evidence.report_number, {"similarity": evidence.similarity})
    return warnings
