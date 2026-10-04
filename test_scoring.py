"""Risk arithmetic and control credit rules."""
import pytest

from aegis_rmf.domain import ControlClaim, ControlType, Dimension, VerificationStatus
from aegis_rmf.risk.scoring import apply_controls, score

O, D, S = Dimension.OCCURRENCE, Dimension.DETECTABILITY, Dimension.SEVERITY
PASS, FAIL = VerificationStatus.PASS, VerificationStatus.FAIL


def claim(control_id, control_type, **effects):
    lookup = {"occurrence": O, "detectability": D, "severity": S}
    return ControlClaim(control_id=control_id, description=control_id, control_type=control_type,
                        effects={lookup[k]: v for k, v in effects.items()}, requirement_ids=[])


def test_rpn_is_the_product_for_every_cell(policy):
    for s in range(1, 6):
        for p in range(1, 6):
            for d in range(1, 6):
                result = score(policy, s, p, d)
                assert result.rpn == s * p * d
                assert result.region is policy.region(s, p)
                assert result.action_priority is policy.action_priority(s, p, d)


@pytest.mark.parametrize("rpn, band", [(1, "LOW"), (20, "LOW"), (21, "MEDIUM"), (60, "MEDIUM"), (61, "HIGH"), (125, "HIGH")])
def test_rpn_bands(policy, rpn, band):
    assert policy.rpn_band(rpn) == band


def test_verified_protective_measure_is_credited(policy):
    pre = score(policy, 4, 3, 5)
    post, credits = apply_controls(policy, pre, [claim("C1", ControlType.PROTECTIVE, occurrence=2, detectability=3)], {"C1": PASS})
    assert (post.severity, post.probability, post.detectability, post.rpn) == (4, 1, 2, 8)
    assert credits[0].credited == {O: 2, D: 3}


@pytest.mark.parametrize("status", [FAIL, VerificationStatus.PENDING, VerificationStatus.MISSING])
def test_unverified_control_earns_no_credit(policy, status):
    pre = score(policy, 4, 4, 5)
    post, credits = apply_controls(policy, pre, [claim("C1", ControlType.PROTECTIVE, occurrence=2)], {"C1": status})
    assert post == pre
    assert credits[0].credited == {O: 0}
    assert status.value in credits[0].notes[0]


def test_control_without_status_is_treated_as_missing(policy):
    pre = score(policy, 3, 3, 3)
    post, credits = apply_controls(policy, pre, [claim("C1", ControlType.INHERENT, occurrence=1)], {})
    assert post == pre
    assert credits[0].verification_status is VerificationStatus.MISSING


def test_protective_measure_cannot_reduce_severity(policy):
    pre = score(policy, 5, 2, 2)
    post, credits = apply_controls(policy, pre, [claim("C1", ControlType.PROTECTIVE, severity=2)], {"C1": PASS})
    assert post.severity == 5
    assert credits[0].notes


def test_inherent_design_can_reduce_severity(policy):
    pre = score(policy, 5, 2, 2)
    post, _ = apply_controls(policy, pre, [claim("C1", ControlType.INHERENT, severity=1)], {"C1": PASS})
    assert post.severity == 4


def test_information_for_safety_is_capped_across_the_risk(policy):
    pre = score(policy, 3, 5, 5)
    claims = [claim("I1", ControlType.INFORMATION, occurrence=1), claim("I2", ControlType.INFORMATION, occurrence=1, detectability=1)]
    post, credits = apply_controls(policy, pre, claims, {"I1": PASS, "I2": PASS})
    assert (post.probability, post.detectability) == (4, 5)
    assert sum(sum(c.credited.values()) for c in credits) == policy.information_total_cap


def test_dimension_cap_and_floor(policy):
    pre = score(policy, 4, 5, 2)
    claims = [claim("A", ControlType.INHERENT, occurrence=3), claim("B", ControlType.PROTECTIVE, occurrence=2, detectability=3)]
    post, credits = apply_controls(policy, pre, claims, {"A": PASS, "B": PASS})
    assert post.probability == 2
    assert post.detectability == 1
    by_id = {c.control_id: c for c in credits}
    assert by_id["A"].credited[O] == 3 and by_id["B"].credited[O] == 0


def test_inherent_design_is_credited_before_other_types(policy):
    """Clause 7.1 priority: the order of claims in the document must not change who gets the credit."""
    pre = score(policy, 4, 5, 5)
    first = [claim("P", ControlType.PROTECTIVE, occurrence=2), claim("I", ControlType.INHERENT, occurrence=3)]
    post_a, credits_a = apply_controls(policy, pre, first, {"P": PASS, "I": PASS})
    post_b, credits_b = apply_controls(policy, pre, list(reversed(first)), {"P": PASS, "I": PASS})
    assert post_a == post_b
    assert [c.control_id for c in credits_a] == ["P", "I"]
    assert {c.control_id: c.credited[O] for c in credits_a} == {c.control_id: c.credited[O] for c in credits_b} == {"I": 3, "P": 0}


def test_scoring_is_deterministic(policy):
    pre = score(policy, 5, 3, 4)
    claims = [claim("A", ControlType.INHERENT, occurrence=2), claim("B", ControlType.INFORMATION, occurrence=1)]
    runs = {apply_controls(policy, pre, claims, {"A": PASS, "B": PASS})[0].model_dump_json() for _ in range(5)}
    assert len(runs) == 1
