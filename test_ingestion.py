"""Parsing of design documents, standards and incident reports."""
from aegis_rmf.domain import VerificationStatus
from aegis_rmf.ingestion.incidents import load_incidents
from aegis_rmf.ingestion.openfda import from_openfda, to_native


def test_corpus_counts(result):
    corpus = result.corpus
    assert len(corpus.documents) == 6
    assert len(corpus.components) == 23
    assert len(corpus.requirements) == 58
    assert len(corpus.verifications) == 57


def test_component_registry_comes_from_the_architecture_specification(result):
    component = result.corpus.components["CMP_SW_01"]
    assert component.name == "Dose Calculation Software"
    assert (component.doc_id, component.section, component.software_class) == ("SRS_003", "4.1", "Class C")
    assert result.corpus.components["CMP_DRV_01"].software_class == ""


def test_requirement_tags_and_source(result):
    requirement = result.corpus.requirements["REQ_DRV_001"]
    assert requirement.component_id == "CMP_DRV_01"
    assert requirement.verification_id == "VER_DRV_001"
    assert requirement.standards == ["IEC 62304 cl 7.2", "IEC 60601 1 cl 4.2"]
    assert requirement.source.label() == "HDS_002 section 3.1 (REQ_DRV_001)"
    assert requirement.source.line > 0


def test_requirement_without_verification_tag(result):
    assert result.corpus.requirements["REQ_LBL_002"].verification_id == ""


def test_verification_results(result):
    verifications = result.corpus.verifications
    assert verifications["VER_SW_005"].result is VerificationStatus.FAIL
    assert verifications["VER_COM_002"].result is VerificationStatus.PENDING
    assert verifications["VER_DRV_001"].report.startswith("TR_")


def test_units_carry_exact_references(result):
    unit = result.corpus.unit("HDS_002:6.1:DFC_PWR_02")
    assert unit is not None and unit.component_id == "CMP_PWR_01" and unit.level == 4
    assert result.corpus.unit("RMP_006:5").citations() == ["ISO 14971 cl 7.1", "ISO 14971 cl 7.5"]


def test_every_cited_clause_exists_in_the_catalogue(result):
    cited = {key for unit in result.corpus.units for key in unit.citations()}
    cited |= {key for requirement in result.corpus.requirements.values() for key in requirement.standards}
    assert cited and cited <= set(result.clauses)
    assert result.graph_warnings == []


def test_standards_catalogue(result):
    clause = result.clauses["ISO 14971 cl 7.1"]
    assert clause.topic == "Risk control option analysis"
    assert clause.node_id == "CLAUSE_ISO14971_7_1"
    assert result.clauses["IEC 60601 1 8 cl 6.1"].node_id == "CLAUSE_IEC6060118_6_1"


def test_incident_loader(settings):
    incidents = load_incidents(settings.incidents_path, limit=25)
    assert len(incidents) == 25
    assert all(record.source == "synthetic" and record.narrative for record in incidents)
    assert incidents[0].report_number.startswith("MDR_")


def test_openfda_mapping_round_trip():
    payload = {
        "report_number": "1234567-2024-00042", "date_received": "20240312", "event_type": "Injury",
        "product_problems": ["Failure to Deliver", "Occlusion Within Device"],
        "device": [{"generic_name": "PUMP, INFUSION, INSULIN", "model_number": "X1"}],
        "patient": [{"patient_problems": ["Hyperglycemia"]}],
        "mdr_text": [{"text_type_code": "Description of Event or Problem", "text": "Pump stopped delivering insulin."},
                     {"text_type_code": "Additional Manufacturer Narrative", "text": "Device not returned."}],
    }
    record = from_openfda(payload)
    assert record.report_number == "1234567_2024_00042"
    assert record.product_problem == "Failure to Deliver; Occlusion Within Device"
    assert record.patient_problem == "Hyperglycemia"
    assert record.narrative == "Pump stopped delivering insulin. Device not returned."
    assert to_native(record)["source"] == "openfda"


def test_openfda_report_without_narrative_is_skipped():
    assert from_openfda({"report_number": "1", "mdr_text": []}) is None
