"""Deterministic extraction of design failure considerations.

The extractor reads the structured failure consideration blocks that engineering teams record
in the design documents. It never guesses: a block with a missing field, an unknown component
or an unknown requirement is reported as an issue and left out of the risk management file.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from aegis_rmf.domain import ControlClaim, ControlType, Dimension, ExtractedScenario
from aegis_rmf.ingestion.design_docs import DesignCorpus, DocUnit

FIELD_LINE = re.compile(
    r"^\* (Failure mode|Cause|Hazard|Hazardous situation|Harm|Detection before controls|Occurrence before controls): (.+)$"
)
CONTROL_LINE = re.compile(r"^\* Risk control: (RCM_\w+) \| (.+?) \| (.+?) \| (.+?) \| (.+)$")
EFFECT = re.compile(r"(severity|occurrence|detectability) (\d)")
REQUIRED_FIELDS = [
    "Failure mode", "Cause", "Hazard", "Hazardous situation", "Harm",
    "Detection before controls", "Occurrence before controls",
]


class ExtractionIssue(BaseModel):
    ref_id: str
    message: str


def _parse_control(match: re.Match, corpus: DesignCorpus) -> tuple[ControlClaim | None, str]:
    control_id, description, type_text, effects_text, requirements_text = match.groups()
    try:
        control_type = ControlType(type_text.strip().replace(" ", "_"))
    except ValueError:
        return None, f"{control_id} has unknown control type {type_text!r}"
    effects = {Dimension(name): int(value) for name, value in EFFECT.findall(effects_text)}
    if not effects:
        return None, f"{control_id} declares no effect"
    requirement_ids = [item.strip() for item in requirements_text.split(",") if item.strip()]
    unknown = [rid for rid in requirement_ids if rid not in corpus.requirements]
    if unknown:
        return None, f"{control_id} cites unknown requirements {', '.join(unknown)}"
    return ControlClaim(
        control_id=control_id, description=description.strip(), control_type=control_type,
        effects=effects, requirement_ids=requirement_ids,
    ), ""


def parse_unit(unit: DocUnit, corpus: DesignCorpus) -> tuple[ExtractedScenario | None, list[ExtractionIssue]]:
    """Parse one failure consideration block."""
    issues: list[ExtractionIssue] = []
    fields: dict[str, str] = {}
    controls: list[ControlClaim] = []
    for line in unit.text.splitlines():
        field = FIELD_LINE.match(line)
        if field:
            fields[field.group(1)] = field.group(2).strip()
            continue
        control = CONTROL_LINE.match(line)
        if control:
            claim, problem = _parse_control(control, corpus)
            if claim:
                controls.append(claim)
            else:
                issues.append(ExtractionIssue(ref_id=unit.ref_id, message=problem))
    missing = [name for name in REQUIRED_FIELDS if name not in fields]
    if missing:
        issues.append(ExtractionIssue(ref_id=unit.ref_id, message=f"Missing fields: {', '.join(missing)}"))
        return None, issues
    if unit.component_id not in corpus.components:
        issues.append(ExtractionIssue(ref_id=unit.ref_id, message=f"Unknown component {unit.component_id!r}"))
        return None, issues
    title = unit.heading.split(" ", 1)[1] if " " in unit.heading else unit.heading
    scenario = ExtractedScenario(
        dfc_id=unit.dfc_id, title=title, component_id=unit.component_id,
        failure_mode=fields["Failure mode"], cause=fields["Cause"], hazard=fields["Hazard"],
        hazardous_situation=fields["Hazardous situation"], harm_text=fields["Harm"],
        detection_text=fields["Detection before controls"], occurrence_text=fields["Occurrence before controls"],
        controls=controls, source=unit.source, origin="rule",
    )
    return scenario, issues


def extract_scenarios(corpus: DesignCorpus) -> tuple[list[ExtractedScenario], list[ExtractionIssue]]:
    """Extract every failure scenario in the corpus, in document order."""
    scenarios: list[ExtractedScenario] = []
    issues: list[ExtractionIssue] = []
    for unit in corpus.units:
        if not unit.dfc_id:
            continue
        scenario, unit_issues = parse_unit(unit, corpus)
        issues.extend(unit_issues)
        if scenario:
            scenarios.append(scenario)
    return scenarios, issues
