"""Language model assisted discovery of failure scenarios in narrative text.

Proposals are constrained to the policy vocabulary and validated before they are kept. They are
written to a review file and are never entered into the risk management file automatically,
because a risk analysis record needs a human owner.
"""
from __future__ import annotations

import json
import re

from aegis_rmf.domain import ExtractedScenario
from aegis_rmf.extraction.llm import TextLLM
from aegis_rmf.extraction.rule_extractor import ExtractionIssue
from aegis_rmf.ingestion.design_docs import DesignCorpus, DocUnit
from aegis_rmf.risk.policy import HarmCatalogue, PolicyError, RiskPolicy

PROMPT = """You are a medical device risk analyst working under ISO 14971.
Read the component description below and list failure scenarios that the text implies
but that are not already recorded. Do not invent ratings or numbers.

Component: {component_id} {component_name}
Already recorded failure modes:
{known}

Allowed harms (use the exact name): {harms}
Allowed detection methods (use the exact name): {detections}
Allowed occurrence terms (use the exact name): {occurrences}

Text:
{text}

Reply with a JSON array only. Each item must have the keys
failure_mode, cause, hazard, hazardous_situation, harm, detection, occurrence.
Reply with [] when the text implies nothing new."""

JSON_ARRAY = re.compile(r"\[.*\]", re.DOTALL)


class LLMScenarioExtractor:
    def __init__(self, llm: TextLLM, policy: RiskPolicy, harms: HarmCatalogue, corpus: DesignCorpus) -> None:
        self.llm, self.policy, self.harms, self.corpus = llm, policy, harms, corpus

    def propose(self, unit: DocUnit, known_failure_modes: list[str]) -> tuple[list[ExtractedScenario], list[ExtractionIssue]]:
        """Ask the model for scenarios in one component section and keep only valid proposals."""
        component = self.corpus.components.get(unit.component_id)
        if component is None:
            return [], []
        prompt = PROMPT.format(
            component_id=component.id, component_name=component.name,
            known="\n".join(f"* {mode}" for mode in known_failure_modes) or "* none",
            harms="; ".join(entry.name for entry in self.harms.harms.values()),
            detections="; ".join(sorted(self.policy.detection_methods)),
            occurrences="; ".join(self.policy.probability_labels.values()),
            text=unit.text,
        )
        reply = self.llm.complete(prompt)
        match = JSON_ARRAY.search(reply)
        if not match:
            return [], [ExtractionIssue(ref_id=unit.ref_id, message="Model reply contained no JSON array")]
        try:
            items = json.loads(match.group(0))
        except json.JSONDecodeError as error:
            return [], [ExtractionIssue(ref_id=unit.ref_id, message=f"Model reply was not valid JSON: {error}")]

        proposals: list[ExtractedScenario] = []
        issues: list[ExtractionIssue] = []
        suffix = component.id.replace("CMP_", "")
        for index, item in enumerate(items, start=1):
            try:
                self.harms.resolve(item["harm"])
                self.policy.detectability_from_method(item["detection"])
                self.policy.probability_from_term(item["occurrence"])
                proposals.append(ExtractedScenario(
                    dfc_id=f"LLM_{suffix}_{index:02d}", title=item["failure_mode"], component_id=component.id,
                    failure_mode=item["failure_mode"], cause=item["cause"], hazard=item["hazard"],
                    hazardous_situation=item["hazardous_situation"], harm_text=item["harm"],
                    detection_text=item["detection"], occurrence_text=item["occurrence"],
                    controls=[], source=unit.source, origin="llm",
                ))
            except (KeyError, TypeError, PolicyError) as error:
                issues.append(ExtractionIssue(ref_id=unit.ref_id, message=f"Proposal {index} rejected: {error}"))
        return proposals, issues
