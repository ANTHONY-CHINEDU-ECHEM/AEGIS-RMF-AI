"""Risk acceptability policy: rating scales, the acceptability matrix and the action priority tensor.

Everything here is a lookup. No rating is ever produced by a language model.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml
from pydantic import BaseModel

from aegis_rmf.domain import ActionPriority, ControlType, Dimension, RiskRegion

LEVELS = (1, 2, 3, 4, 5)
REGION_CODES = {"A": RiskRegion.ACCEPTABLE, "R": RiskRegion.REVIEW, "U": RiskRegion.UNACCEPTABLE}
PRIORITY_RANK = {ActionPriority.LOW: 0, ActionPriority.MEDIUM: 1, ActionPriority.HIGH: 2}


class PolicyError(ValueError):
    """Raised when the policy file is incomplete or internally inconsistent."""


class RiskPolicy(BaseModel):
    policy_id: str
    title: str
    revision: str
    severity_labels: dict[int, str]
    probability_labels: dict[int, str]
    probability_rate_bounds: dict[int, float | None]
    detectability_labels: dict[int, str]
    detection_methods: dict[str, int]
    matrix: dict[int, list[RiskRegion]]
    rpn_low_max: int
    rpn_medium_max: int
    priority_rules: list[dict]
    priority_default: ActionPriority
    require_verification: bool
    per_control_max: dict[ControlType, dict[Dimension, int]]
    information_total_cap: int
    dimension_caps: dict[Dimension, int]
    exposure_device_years: float
    evidence_top_k: int

    def region(self, severity: int, probability: int) -> RiskRegion:
        """Acceptability depends on severity and probability of harm only, as ISO 14971 defines risk."""
        _check_levels(severity, probability)
        return self.matrix[severity][probability - 1]

    def action_priority(self, severity: int, probability: int, detectability: int) -> ActionPriority:
        """Three dimensional lookup. The first rule whose lower bounds are all met decides."""
        _check_levels(severity, probability, detectability)
        for rule in self.priority_rules:
            if severity >= rule["s"] and probability >= rule["p"] and detectability >= rule["d"]:
                return ActionPriority(rule["priority"])
        return self.priority_default

    def priority_tensor(self) -> np.ndarray:
        """Materialise the lookup as a 5 x 5 x 5 array of ranks (0 low, 1 medium, 2 high)."""
        tensor = np.zeros((5, 5, 5), dtype=int)
        for s in LEVELS:
            for p in LEVELS:
                for d in LEVELS:
                    tensor[s - 1, p - 1, d - 1] = PRIORITY_RANK[self.action_priority(s, p, d)]
        return tensor

    def rpn_band(self, rpn: int) -> str:
        if rpn <= self.rpn_low_max:
            return "LOW"
        return "MEDIUM" if rpn <= self.rpn_medium_max else "HIGH"

    def probability_from_term(self, term: str) -> int:
        lookup = {label.lower(): level for level, label in self.probability_labels.items()}
        key = term.strip().lower()
        if key not in lookup:
            raise PolicyError(f"Unknown probability term: {term!r}")
        return lookup[key]

    def detectability_from_method(self, method: str) -> int:
        key = method.strip().lower()
        if key not in self.detection_methods:
            raise PolicyError(f"Unknown detection method: {method!r}")
        return self.detection_methods[key]

    def probability_from_rate(self, rate_per_100k_device_years: float) -> int:
        """Map an observed incident rate to a probability rating using the policy bounds."""
        for level in LEVELS:
            bound = self.probability_rate_bounds[level]
            if bound is None or rate_per_100k_device_years < bound:
                return level
        return 5


class HarmEntry(BaseModel):
    id: str
    name: str
    severity: int
    aliases: list[str]


class HarmCatalogue(BaseModel):
    harms: dict[str, HarmEntry]

    def resolve(self, harm_text: str) -> HarmEntry:
        """Map free text to a catalogue harm. The longest matching alias wins."""
        text = harm_text.strip().lower()
        best: tuple[int, HarmEntry] | None = None
        for entry in self.harms.values():
            for alias in [entry.name.lower(), *entry.aliases]:
                if alias in text and (best is None or len(alias) > best[0]):
                    best = (len(alias), entry)
        if best is None:
            raise PolicyError(f"Harm text does not match the harm catalogue: {harm_text!r}")
        return best[1]


def _check_levels(*levels: int) -> None:
    for level in levels:
        if level not in LEVELS:
            raise PolicyError(f"Rating {level} is outside the range 1 to 5")


def load_policy(path: Path) -> RiskPolicy:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf8"))
    matrix = {int(s): [REGION_CODES[c] for c in row] for s, row in raw["acceptability_matrix"].items()}
    credit = raw["control_credit"]
    policy = RiskPolicy(
        policy_id=raw["policy"]["id"],
        title=raw["policy"]["title"],
        revision=str(raw["policy"]["revision"]),
        severity_labels={int(k): v["label"] for k, v in raw["severity"].items()},
        probability_labels={int(k): v["label"] for k, v in raw["probability"].items()},
        probability_rate_bounds={int(k): v["rate_upper_bound"] for k, v in raw["probability"].items()},
        detectability_labels={int(k): v["label"] for k, v in raw["detectability"].items()},
        detection_methods={v["method"].lower(): int(k) for k, v in raw["detectability"].items()},
        matrix=matrix,
        rpn_low_max=raw["rpn_bands"]["low_max"],
        rpn_medium_max=raw["rpn_bands"]["medium_max"],
        priority_rules=raw["action_priority_rules"],
        priority_default=ActionPriority(raw["action_priority_default"]),
        require_verification=credit["require_verification"],
        per_control_max={ControlType(t): {Dimension(d): n for d, n in dims.items()} for t, dims in credit["per_control_max"].items()},
        information_total_cap=credit["information_for_safety_total_cap"],
        dimension_caps={Dimension(d): n for d, n in credit["dimension_caps"].items()},
        exposure_device_years=float(raw["field_evidence"]["exposure_device_years"]),
        evidence_top_k=int(raw["field_evidence"]["evidence_top_k"]),
    )
    validate_policy(policy)
    return policy


def validate_policy(policy: RiskPolicy) -> None:
    """Reject policies that are incomplete or that would let a worse rating score better."""
    rank = {RiskRegion.ACCEPTABLE: 0, RiskRegion.REVIEW: 1, RiskRegion.UNACCEPTABLE: 2}
    for s in LEVELS:
        if s not in policy.matrix or len(policy.matrix[s]) != 5:
            raise PolicyError(f"Acceptability matrix row {s} must have five entries")
    for s in LEVELS:
        for p in LEVELS:
            here = rank[policy.matrix[s][p - 1]]
            if p < 5 and rank[policy.matrix[s][p]] < here:
                raise PolicyError(f"Acceptability matrix is not monotone in probability at severity {s}")
            if s < 5 and rank[policy.matrix[s + 1][p - 1]] < here:
                raise PolicyError(f"Acceptability matrix is not monotone in severity at probability {p}")
    tensor = policy.priority_tensor()
    for axis in range(3):
        if (np.diff(tensor, axis=axis) < 0).any():
            raise PolicyError("Action priority tensor is not monotone")
    bounds = [policy.probability_rate_bounds[level] for level in LEVELS[:4]]
    if any(b is None for b in bounds) or bounds != sorted(bounds):
        raise PolicyError("Probability rate bounds must increase with the rating")


def load_harm_catalogue(path: Path) -> HarmCatalogue:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf8"))
    return HarmCatalogue(harms={hid: HarmEntry(id=hid, **spec) for hid, spec in raw["harms"].items()})
