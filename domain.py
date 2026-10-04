"""Domain model for the risk management file. All records are plain validated data."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ControlType(str, Enum):
    """Risk control options in the priority order of ISO 14971 clause 7.1."""

    INHERENT = "inherent_safety_by_design"
    PROTECTIVE = "protective_measure"
    INFORMATION = "information_for_safety"


CONTROL_PRIORITY = [ControlType.INHERENT, ControlType.PROTECTIVE, ControlType.INFORMATION]


class Dimension(str, Enum):
    SEVERITY = "severity"
    OCCURRENCE = "occurrence"
    DETECTABILITY = "detectability"


class RiskRegion(str, Enum):
    ACCEPTABLE = "ACCEPTABLE"
    REVIEW = "REVIEW"
    UNACCEPTABLE = "UNACCEPTABLE"


class ActionPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class VerificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"
    MISSING = "MISSING"


class SourceRef(BaseModel):
    """Exact location of a statement inside a design document."""

    doc_id: str
    section: str
    anchor: str = ""
    line: int = 0

    @property
    def ref_id(self) -> str:
        return f"{self.doc_id}:{self.section}" + (f":{self.anchor}" if self.anchor else "")

    def label(self) -> str:
        text = f"{self.doc_id} section {self.section}"
        return f"{text} ({self.anchor})" if self.anchor else text


class Component(BaseModel):
    id: str
    name: str
    subsystem: str
    doc_id: str
    section: str
    software_class: str = ""


class Requirement(BaseModel):
    id: str
    text: str
    component_id: str
    source: SourceRef
    verification_id: str = ""
    standards: list[str] = Field(default_factory=list)


class VerificationRecord(BaseModel):
    id: str
    requirement_id: str
    method: str
    result: VerificationStatus
    report: str


class ControlClaim(BaseModel):
    """A risk control measure as claimed in a design failure consideration."""

    control_id: str
    description: str
    control_type: ControlType
    effects: dict[Dimension, int]
    requirement_ids: list[str]


class ExtractedScenario(BaseModel):
    """One failure scenario extracted from a design document."""

    dfc_id: str
    title: str
    component_id: str
    failure_mode: str
    cause: str
    hazard: str
    hazardous_situation: str
    harm_text: str
    detection_text: str
    occurrence_text: str
    controls: list[ControlClaim] = Field(default_factory=list)
    source: SourceRef
    origin: str = "rule"


class RiskScore(BaseModel):
    severity: int
    probability: int
    detectability: int
    rpn: int
    rpn_band: str
    region: RiskRegion
    action_priority: ActionPriority


class ControlCredit(BaseModel):
    """The outcome of evaluating one control claim against the credit policy."""

    control_id: str
    description: str
    control_type: ControlType
    requirement_ids: list[str]
    verification_ids: list[str] = Field(default_factory=list)
    verification_status: VerificationStatus
    claimed: dict[Dimension, int]
    credited: dict[Dimension, int]
    notes: list[str] = Field(default_factory=list)


class IncidentEvidence(BaseModel):
    report_number: str
    similarity: float
    event_type: str
    product_problem: str
    excerpt: str


class FieldEvidence(BaseModel):
    """Field data for a scenario, gathered by vector search over the incident corpus."""

    matched_count: int = 0
    injury_count: int = 0
    death_count: int = 0
    rate_per_100k_device_years: float = 0.0
    implied_probability: int = 1
    evidence: list[IncidentEvidence] = Field(default_factory=list)


class AgentStep(BaseModel):
    order: int
    tool: str
    detail: str


class RiskRecord(BaseModel):
    """One row of the hazard analysis with scores before and after risk control."""

    risk_id: str
    dfc_id: str
    title: str
    component_id: str
    component_name: str
    failure_mode_id: str
    failure_mode: str
    cause: str
    hazard_id: str
    hazard: str
    hazardous_situation_id: str
    hazardous_situation: str
    harm_id: str
    harm: str
    detection_method: str
    engineering_probability: int
    field: FieldEvidence
    probability_basis: str
    pre: RiskScore
    controls: list[ControlCredit]
    post: RiskScore
    rpn_reduction_pct: float
    benefit_risk_required: bool
    disposition: str
    source: SourceRef
    clause_refs: list[str]
    audit: list[AgentStep] = Field(default_factory=list)

    def summary_text(self) -> str:
        """Plain language summary that is indexed for retrieval."""
        controls = "; ".join(
            f"{c.control_id} {c.description} ({c.control_type.value.replace('_', ' ')}, verification {c.verification_status.value})"
            for c in self.controls
        ) or "none"
        return (
            f"Risk {self.risk_id} for component {self.component_id} {self.component_name}. "
            f"Failure mode: {self.failure_mode}. Cause: {self.cause}. Hazard: {self.hazard}. "
            f"Hazardous situation: {self.hazardous_situation}. Harm: {self.harm}. "
            f"Before risk control the severity is {self.pre.severity}, probability {self.pre.probability} "
            f"and detectability {self.pre.detectability}, giving a risk priority number of {self.pre.rpn} "
            f"in the {self.pre.region.value} region. Risk controls: {controls}. "
            f"After risk control the severity is {self.post.severity}, probability {self.post.probability} "
            f"and detectability {self.post.detectability}, giving a residual risk priority number of {self.post.rpn} "
            f"in the {self.post.region.value} region. Disposition: {self.disposition}. "
            f"Field data matched {self.field.matched_count} similar incident reports. "
            f"Source: {self.source.label()}."
        )
