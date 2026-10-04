"""Deterministic risk arithmetic: the risk priority number and the crediting of risk controls."""
from __future__ import annotations

from aegis_rmf.domain import (
    CONTROL_PRIORITY,
    ControlClaim,
    ControlCredit,
    ControlType,
    Dimension,
    RiskScore,
    VerificationStatus,
)
from aegis_rmf.risk.policy import RiskPolicy


def score(policy: RiskPolicy, severity: int, probability: int, detectability: int) -> RiskScore:
    """Compute the risk priority number and look up region, band and action priority."""
    rpn = severity * probability * detectability
    return RiskScore(
        severity=severity,
        probability=probability,
        detectability=detectability,
        rpn=rpn,
        rpn_band=policy.rpn_band(rpn),
        region=policy.region(severity, probability),
        action_priority=policy.action_priority(severity, probability, detectability),
    )


def apply_controls(
    policy: RiskPolicy,
    pre: RiskScore,
    claims: list[ControlClaim],
    statuses: dict[str, VerificationStatus],
    verification_ids: dict[str, list[str]] | None = None,
) -> tuple[RiskScore, list[ControlCredit]]:
    """Credit each control claim under the policy and return the residual score.

    Controls are processed in the ISO 14971 clause 7.1 priority order. A claim earns credit only
    when its verification status is PASS (if the policy requires verification). Credit is limited
    per control type, per dimension and, for information for safety, across the whole risk.
    """
    verification_ids = verification_ids or {}
    remaining = dict(policy.dimension_caps)
    information_remaining = policy.information_total_cap
    totals = {dimension: 0 for dimension in Dimension}
    credits: dict[str, ControlCredit] = {}

    ordered = sorted(claims, key=lambda claim: CONTROL_PRIORITY.index(claim.control_type))
    for claim in ordered:
        status = statuses.get(claim.control_id, VerificationStatus.MISSING)
        credited = {dimension: 0 for dimension in claim.effects}
        notes: list[str] = []
        if policy.require_verification and status is not VerificationStatus.PASS:
            notes.append(f"No credit because verification status is {status.value}")
        else:
            for dimension, claimed in claim.effects.items():
                allowed = min(claimed, policy.per_control_max[claim.control_type][dimension])
                if allowed < claimed:
                    notes.append(f"{dimension.value} credit limited to {allowed} for control type {claim.control_type.value}")
                if claim.control_type is ControlType.INFORMATION:
                    capped = min(allowed, information_remaining)
                    if capped < allowed:
                        notes.append("Information for safety credit exhausted for this risk")
                    information_remaining -= capped
                    allowed = capped
                capped = min(allowed, remaining[dimension])
                if capped < allowed:
                    notes.append(f"{dimension.value} credit limited by the total cap for that dimension")
                remaining[dimension] -= capped
                credited[dimension] = capped
                totals[dimension] += capped
        credits[claim.control_id] = ControlCredit(
            control_id=claim.control_id,
            description=claim.description,
            control_type=claim.control_type,
            requirement_ids=claim.requirement_ids,
            verification_ids=verification_ids.get(claim.control_id, []),
            verification_status=status,
            claimed=claim.effects,
            credited=credited,
            notes=notes,
        )

    post = score(
        policy,
        max(1, pre.severity - totals[Dimension.SEVERITY]),
        max(1, pre.probability - totals[Dimension.OCCURRENCE]),
        max(1, pre.detectability - totals[Dimension.DETECTABILITY]),
    )
    return post, [credits[claim.control_id] for claim in claims]
