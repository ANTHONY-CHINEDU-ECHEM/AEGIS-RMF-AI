"""Rule based extraction and validation of language model proposals."""
from aegis_rmf.domain import ControlType, Dimension
from aegis_rmf.extraction.llm_extractor import LLMScenarioExtractor
from aegis_rmf.extraction.rule_extractor import parse_unit


def test_all_failure_considerations_are_extracted(result):
    assert len(result.scenarios) == 39
    assert result.issues == []
    assert len({scenario.dfc_id for scenario in result.scenarios}) == 39


def test_scenario_fields_and_controls(result):
    scenario = next(s for s in result.scenarios if s.dfc_id == "DFC_DRV_01")
    assert scenario.component_id == "CMP_DRV_01"
    assert scenario.harm_text == "Severe hypoglycemia with loss of consciousness"
    assert scenario.source.ref_id == "HDS_002:3.1:DFC_DRV_01"
    first, second = scenario.controls
    assert first.control_id == "RCM_DRV_01" and first.control_type is ControlType.PROTECTIVE
    assert first.effects == {Dimension.OCCURRENCE: 1, Dimension.DETECTABILITY: 3}
    assert first.requirement_ids == ["REQ_DRV_001"]
    assert second.control_id == "RCM_MCU_03"


def test_scenario_without_controls(result):
    scenario = next(s for s in result.scenarios if s.dfc_id == "DFC_SNS_03")
    assert scenario.controls == []


def _unit(result, text):
    unit = result.corpus.unit("HDS_002:3.1:DFC_DRV_01")
    return unit.model_copy(update={"text": text})


def test_missing_field_is_reported_and_block_is_dropped(result):
    text = "\n".join(line for line in result.corpus.unit("HDS_002:3.1:DFC_DRV_01").text.splitlines() if not line.startswith("* Harm:"))
    scenario, issues = parse_unit(_unit(result, text), result.corpus)
    assert scenario is None
    assert "Harm" in issues[0].message


def test_unknown_requirement_drops_only_that_control(result):
    text = result.corpus.unit("HDS_002:3.1:DFC_DRV_01").text.replace("| REQ_DRV_001", "| REQ_NOPE_999")
    scenario, issues = parse_unit(_unit(result, text), result.corpus)
    assert [c.control_id for c in scenario.controls] == ["RCM_MCU_03"]
    assert "REQ_NOPE_999" in issues[0].message


def test_unknown_control_type_is_reported(result):
    text = result.corpus.unit("HDS_002:3.1:DFC_DRV_01").text.replace("| protective measure |", "| wishful thinking |", 1)
    scenario, issues = parse_unit(_unit(result, text), result.corpus)
    assert len(scenario.controls) == 1 and "unknown control type" in issues[0].message


class FakeLLM:
    def __init__(self, reply):
        self.reply, self.prompts = reply, []

    def complete(self, prompt):
        self.prompts.append(prompt)
        return self.reply


VALID = ('{"failure_mode": "Gear train seizes", "cause": "Debris", "hazard": "Underdelivery of insulin", '
         '"hazardous_situation": "No insulin is delivered", "harm": "Hyperglycemia progressing to diabetic ketoacidosis", '
         '"detection": "No detection", "occurrence": "Remote"}')
INVALID = VALID.replace("Remote", "Now and then")


def test_llm_proposals_are_validated_against_the_policy_vocabulary(result):
    llm = FakeLLM(f"Here you go:\n[{VALID}, {INVALID}]")
    extractor = LLMScenarioExtractor(llm, result.policy, result.harms, result.corpus)
    proposals, issues = extractor.propose(result.corpus.unit("HDS_002:3.1"), ["Motor stalls"])
    assert len(proposals) == 1 and len(issues) == 1
    proposal = proposals[0]
    assert proposal.origin == "llm" and proposal.dfc_id == "LLM_DRV_01_01" and proposal.controls == []
    assert "Motor stalls" in llm.prompts[0] and "Do not invent ratings" in llm.prompts[0]


def test_llm_reply_without_json_is_an_issue(result):
    extractor = LLMScenarioExtractor(FakeLLM("I cannot help"), result.policy, result.harms, result.corpus)
    proposals, issues = extractor.propose(result.corpus.unit("HDS_002:3.1"), [])
    assert proposals == [] and "no JSON" in issues[0].message


def test_offline_pipeline_makes_no_llm_proposals(result):
    assert result.proposals == [] and result.engine.llm is None
