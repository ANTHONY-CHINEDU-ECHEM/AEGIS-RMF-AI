"""The risk scoring agent: field evidence, verification gating and the audit trail."""
from aegis_rmf.domain import RiskRegion, VerificationStatus


def test_every_scenario_becomes_one_risk_record(result, records):
    assert len(records) == len(result.scenarios) == 39


def test_record_identifiers_follow_the_source(records):
    record = records["RISK_PWR_02"]
    assert (record.dfc_id, record.failure_mode_id, record.hazardous_situation_id) == ("DFC_PWR_02", "FM_PWR_02", "HS_PWR_02")
    assert record.hazard_id == "HAZ_LOSS_OF_THERAPY" and record.harm_id == "HARM_DKA"
    assert record.source.label() == "HDS_002 section 6.1 (DFC_PWR_02)"


def test_scores_are_consistent_with_the_policy(result, records):
    for record in records.values():
        for stage in (record.pre, record.post):
            assert stage.rpn == stage.severity * stage.probability * stage.detectability
            assert stage.region is result.policy.region(stage.severity, stage.probability)
        assert record.post.rpn <= record.pre.rpn
        assert record.pre.probability == max(record.engineering_probability, record.field.implied_probability)


def test_verified_controls_reduce_the_risk(records):
    record = records["RISK_PWR_02"]
    assert (record.pre.severity, record.pre.probability, record.pre.detectability, record.pre.rpn) == (4, 3, 5, 60)
    assert (record.post.probability, record.post.detectability, record.post.rpn) == (1, 2, 8)
    assert record.post.region is RiskRegion.ACCEPTABLE and not record.benefit_risk_required


def test_failed_verification_blocks_credit(records):
    record = records["RISK_SW_02"]
    control = record.controls[0]
    assert control.control_id == "RCM_SW_03" and control.verification_status is VerificationStatus.FAIL
    assert sum(control.credited.values()) == 0
    assert record.post == record.pre and record.post.region is RiskRegion.UNACCEPTABLE
    assert record.disposition == "Design release blocked"


def test_pending_and_missing_verification_block_credit(records):
    pending = {c.control_id: c for c in records["RISK_COM_01"].controls}
    assert pending["RCM_COM_02"].verification_status is VerificationStatus.PENDING
    assert sum(pending["RCM_COM_02"].credited.values()) == 0
    assert sum(pending["RCM_COM_01"].credited.values()) == 1
    missing = {c.control_id: c for c in records["RISK_RSV_01"].controls}
    assert missing["RCM_IFU_02"].verification_status is VerificationStatus.MISSING
    assert records["RISK_RSV_01"].post.detectability == records["RISK_RSV_01"].pre.detectability


def test_field_evidence_raises_probability(records):
    escalated = sorted(r.risk_id for r in records.values() if r.probability_basis == "field evidence")
    assert escalated == ["RISK_INF_01", "RISK_SW_05"]
    record = records["RISK_INF_01"]
    assert record.engineering_probability == 3 and record.pre.probability == 4
    assert record.field.matched_count > 500 and record.field.injury_count > 0
    assert "ISO 14971 cl 10.4" in record.clause_refs
    assert len(record.field.evidence) == 5 and record.field.evidence[0].report_number.startswith("MDR_")


def test_catastrophic_residual_risk_requires_benefit_risk_analysis(records):
    for record in records.values():
        if record.post.severity == 5:
            assert record.post.region is not RiskRegion.ACCEPTABLE
            assert record.benefit_risk_required == (record.post.region is RiskRegion.REVIEW)
            if record.benefit_risk_required:
                assert "ISO 14971 cl 7.4" in record.clause_refs


def test_audit_trail_records_every_tool_call(records):
    record = records["RISK_DRV_01"]
    tools = [step.tool for step in record.audit]
    assert tools[:7] == ["resolve_component", "resolve_harm", "rate_detectability", "rate_engineering_probability",
                         "search_incidents", "select_probability", "score_before_control"]
    assert tools.count("verify_control") == len(record.controls) == 2
    assert tools[len(tools) - 2:] == ["score_after_control", "decide_disposition"]
    assert [step.order for step in record.audit] == list(range(1, len(tools) + 1))
    assert "5 x 2 x 5 = 50" in record.audit[6].detail


def test_summary_text_is_indexable(records):
    text = records["RISK_SW_02"].summary_text()
    assert "RISK_SW_02" in text and "UNACCEPTABLE" in text and "verification FAIL" in text
