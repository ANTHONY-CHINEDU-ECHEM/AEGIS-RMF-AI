"""Deterministic risk scoring agent.

For every extracted failure scenario the agent runs a fixed plan of tool calls and records each
call in an audit trail. Retrieval supplies field evidence. All ratings come from catalogue and
policy lookups and all arithmetic is done in code, so the same inputs always give the same file.
"""
from __future__ import annotations

import re

from aegis_rmf.domain import (
    AgentStep,
    ControlClaim,
    ExtractedScenario,
    FieldEvidence,
    IncidentEvidence,
    RiskRecord,
    RiskRegion,
    VerificationStatus,
)
from aegis_rmf.ingestion.design_docs import DesignCorpus
from aegis_rmf.retrieval.knowledge_base import INCIDENT, KnowledgeBase
from aegis_rmf.risk.policy import HarmCatalogue, RiskPolicy
from aegis_rmf.risk.scoring import apply_controls, score

STATUS_ORDER = [VerificationStatus.FAIL, VerificationStatus.MISSING, VerificationStatus.PENDING, VerificationStatus.PASS]
DISPOSITIONS = {
    RiskRegion.ACCEPTABLE: "Residual risk acceptable",
    RiskRegion.REVIEW: "Benefit risk analysis required",
    RiskRegion.UNACCEPTABLE: "Design release blocked",
}


def hazard_id(hazard: str) -> str:
    return "HAZ_" + re.sub(r"[^A-Z0-9]+", "_", hazard.upper()).strip("_")


class RiskScoringAgent:
    def __init__(self, policy: RiskPolicy, harms: HarmCatalogue, corpus: DesignCorpus, knowledge_base: KnowledgeBase) -> None:
        self.policy, self.harms, self.corpus, self.kb = policy, harms, corpus, knowledge_base

    def field_evidence(self, query: str) -> FieldEvidence:
        """Tool: count similar incident reports and convert the rate into a probability rating."""
        matches = self.kb.matching_incidents(query)
        rate = len(matches) / self.policy.exposure_device_years * 100000.0
        top = self.kb.search(query, [INCIDENT], top_k=self.policy.evidence_top_k) if matches else []
        threshold = self.kb.settings.similarity_threshold
        return FieldEvidence(
            matched_count=len(matches),
            injury_count=sum(1 for m in matches if m.get("event_type") == "Injury"),
            death_count=sum(1 for m in matches if m.get("event_type") == "Death"),
            rate_per_100k_device_years=round(rate, 3),
            implied_probability=self.policy.probability_from_rate(rate) if matches else 1,
            evidence=[
                IncidentEvidence(
                    report_number=hit.ref_id, similarity=round(hit.score, 4), event_type=hit.metadata.get("event_type", ""),
                    product_problem=hit.metadata.get("product_problem", ""), excerpt=hit.text[:240],
                )
                for hit in top if hit.score >= threshold
            ],
        )

    def control_status(self, claim: ControlClaim) -> tuple[VerificationStatus, list[str]]:
        """Tool: a control is verified only when every implementing requirement has a passing record."""
        statuses, verification_ids = [], []
        for requirement_id in claim.requirement_ids:
            requirement = self.corpus.requirements[requirement_id]
            record = self.corpus.verifications.get(requirement.verification_id)
            if record is None:
                statuses.append(VerificationStatus.MISSING)
            else:
                statuses.append(record.result)
                verification_ids.append(record.id)
        worst = min(statuses, key=STATUS_ORDER.index) if statuses else VerificationStatus.MISSING
        return worst, verification_ids

    def assess(self, scenario: ExtractedScenario) -> RiskRecord:
        """Run the scoring plan for one scenario and return the completed risk record."""
        audit: list[AgentStep] = []

        def log(tool: str, detail: str) -> None:
            audit.append(AgentStep(order=len(audit) + 1, tool=tool, detail=detail))

        component = self.corpus.components[scenario.component_id]
        log("resolve_component", f"{component.id} {component.name}, specified in {component.doc_id} section {component.section}")

        harm = self.harms.resolve(scenario.harm_text)
        log("resolve_harm", f"{scenario.harm_text!r} resolved to {harm.id} with severity {harm.severity}")

        detectability = self.policy.detectability_from_method(scenario.detection_text)
        log("rate_detectability", f"{scenario.detection_text!r} rated {detectability}")

        engineering = self.policy.probability_from_term(scenario.occurrence_text)
        log("rate_engineering_probability", f"{scenario.occurrence_text!r} rated {engineering}")

        query = f"{scenario.failure_mode}. {scenario.cause}. {scenario.hazardous_situation}."
        field = self.field_evidence(query)
        log("search_incidents", f"{field.matched_count} similar reports, rate {field.rate_per_100k_device_years} "
                                f"per 100000 device years, implied probability {field.implied_probability}")

        probability = max(engineering, field.implied_probability)
        basis = "field evidence" if field.implied_probability > engineering else "engineering estimate"
        log("select_probability", f"Probability {probability} taken from the {basis}")

        pre = score(self.policy, harm.severity, probability, detectability)
        log("score_before_control", f"RPN {harm.severity} x {probability} x {detectability} = {pre.rpn}, region {pre.region.value}")

        statuses, verification_ids = {}, {}
        for claim in scenario.controls:
            statuses[claim.control_id], verification_ids[claim.control_id] = self.control_status(claim)
            log("verify_control", f"{claim.control_id} verification status {statuses[claim.control_id].value}")

        post, credits = apply_controls(self.policy, pre, scenario.controls, statuses, verification_ids)
        log("score_after_control", f"RPN {post.severity} x {post.probability} x {post.detectability} = {post.rpn}, region {post.region.value}")

        clause_refs = ["ISO 14971 cl 5.4", "ISO 14971 cl 5.5", "ISO 14971 cl 6"]
        if scenario.controls:
            clause_refs += ["ISO 14971 cl 7.1", "ISO 14971 cl 7.2", "ISO 14971 cl 7.3"]
        benefit_risk = post.region is RiskRegion.REVIEW
        if benefit_risk:
            clause_refs.append("ISO 14971 cl 7.4")
        if field.matched_count:
            clause_refs.append("ISO 14971 cl 10.3")
        if basis == "field evidence":
            clause_refs.append("ISO 14971 cl 10.4")
        log("decide_disposition", DISPOSITIONS[post.region])

        suffix = scenario.dfc_id.split("_", 1)[1]
        return RiskRecord(
            risk_id=f"RISK_{suffix}", dfc_id=scenario.dfc_id, title=scenario.title,
            component_id=component.id, component_name=component.name,
            failure_mode_id=f"FM_{suffix}", failure_mode=scenario.failure_mode, cause=scenario.cause,
            hazard_id=hazard_id(scenario.hazard), hazard=scenario.hazard,
            hazardous_situation_id=f"HS_{suffix}", hazardous_situation=scenario.hazardous_situation,
            harm_id=harm.id, harm=harm.name, detection_method=scenario.detection_text,
            engineering_probability=engineering, field=field, probability_basis=basis,
            pre=pre, controls=credits, post=post,
            rpn_reduction_pct=round(100.0 * (pre.rpn - post.rpn) / pre.rpn, 1),
            benefit_risk_required=benefit_risk, disposition=DISPOSITIONS[post.region],
            source=scenario.source, clause_refs=clause_refs, audit=audit,
        )
