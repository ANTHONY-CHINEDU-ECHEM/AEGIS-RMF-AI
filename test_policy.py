"""The risk policy is a set of lookups. These tests pin the lookups and the validation rules."""
import numpy as np
import pytest

from aegis_rmf.domain import ActionPriority, RiskRegion
from aegis_rmf.risk.policy import PolicyError, validate_policy


def test_acceptability_matrix_corners(policy):
    assert policy.region(1, 1) is RiskRegion.ACCEPTABLE
    assert policy.region(5, 1) is RiskRegion.REVIEW
    assert policy.region(4, 4) is RiskRegion.UNACCEPTABLE
    assert policy.region(5, 5) is RiskRegion.UNACCEPTABLE


def test_catastrophic_harm_is_never_acceptable(policy):
    assert all(policy.region(5, p) is not RiskRegion.ACCEPTABLE for p in range(1, 6))


def test_acceptability_ignores_detectability(policy):
    """ISO 14971 defines risk from severity and probability, so region takes no detectability argument."""
    with pytest.raises(TypeError):
        policy.region(3, 3, 5)


def test_priority_tensor_shape_and_monotonicity(policy):
    tensor = policy.priority_tensor()
    assert tensor.shape == (5, 5, 5)
    assert all((np.diff(tensor, axis=axis) >= 0).all() for axis in range(3))


def test_priority_lookup_examples(policy):
    assert policy.action_priority(5, 2, 1) is ActionPriority.HIGH
    assert policy.action_priority(5, 1, 1) is ActionPriority.MEDIUM
    assert policy.action_priority(4, 2, 2) is ActionPriority.MEDIUM
    assert policy.action_priority(4, 2, 3) is ActionPriority.HIGH
    assert policy.action_priority(1, 1, 5) is ActionPriority.LOW


@pytest.mark.parametrize("rate, level", [(0.0, 1), (0.49, 1), (0.5, 2), (4.9, 2), (5.0, 3), (49.9, 3), (50.0, 4), (499.0, 4), (500.0, 5)])
def test_probability_from_rate(policy, rate, level):
    assert policy.probability_from_rate(rate) == level


def test_term_and_method_lookups(policy):
    assert policy.probability_from_term("Occasional") == 3
    assert policy.detectability_from_method("No detection") == 5
    assert policy.detectability_from_method("continuous monitoring with alarm") == 2
    with pytest.raises(PolicyError):
        policy.probability_from_term("Sometimes")
    with pytest.raises(PolicyError):
        policy.detectability_from_method("Hope")


def test_out_of_range_rating_is_rejected(policy):
    with pytest.raises(PolicyError):
        policy.region(6, 1)
    with pytest.raises(PolicyError):
        policy.action_priority(1, 0, 1)


def test_non_monotone_matrix_is_rejected(policy):
    broken = policy.model_copy(deep=True)
    broken.matrix[5] = [RiskRegion.ACCEPTABLE] * 5
    with pytest.raises(PolicyError):
        validate_policy(broken)


def test_non_monotone_priority_rules_are_rejected(policy):
    broken = policy.model_copy(deep=True)
    broken.priority_rules = [{"s": 1, "p": 1, "d": 1, "priority": "LOW"}]
    broken.priority_default = ActionPriority.HIGH
    validate_policy(broken)
    broken.priority_rules = [{"s": 3, "p": 3, "d": 3, "priority": "LOW"}]
    with pytest.raises(PolicyError):
        validate_policy(broken)


def test_harm_catalogue_resolution(harms):
    assert harms.resolve("Severe hypoglycemia with loss of consciousness").id == "HARM_HYPO_SEVERE"
    assert harms.resolve("Hyperglycemia progressing to diabetic ketoacidosis").severity == 4
    assert harms.resolve("Minor skin laceration").severity == 1
    with pytest.raises(PolicyError):
        harms.resolve("Mild annoyance")
