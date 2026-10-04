"""Question answering and the deterministic evaluation metrics."""
import json

from aegis_rmf.evaluation import evaluate_incident_matching, evaluate_retrieval, load_golden
from aegis_rmf.pipeline import run_evaluation
from aegis_rmf.rag import RagEngine
from aegis_rmf.rag.engine import describe_node


def test_graph_facts_for_named_identifiers(result):
    hits, facts = result.engine.retrieve("What is the status of REQ_SW_005 and which risk depends on it?")
    assert len(facts) == 1
    assert "RiskItem RISK_SW_02" in facts[0] and "Verification VER_SW_005" in facts[0]
    assert len(hits) == result.settings.retrieval_top_k


def test_risk_fact_explains_missing_credit(result):
    fact = describe_node(result.store, "RISK_SW_02")
    assert "RPN 80 (UNACCEPTABLE)" in fact
    assert "RCM_SW_03" in fact and "verification status FAIL" in fact and "No credit" in fact
    assert describe_node(result.store, "RISK_NOPE_99") is None


def test_incident_evidence_is_added_for_field_questions(result):
    hits, _ = result.engine.retrieve("How many incident reports mention the infusion set connector detaching?")
    assert [hit.source_type for hit in hits[6:]] == ["incident"] * 3
    hits, _ = result.engine.retrieve("What is the ingress protection rating?")
    assert all(hit.source_type != "incident" for hit in hits)


def test_extractive_answer_cites_references(result):
    answer = result.engine.answer("Which IEC 62304 clause covers verification of software risk control measures?")
    assert answer.mode == "extractive"
    assert answer.answer.startswith("[IEC 62304 cl 7.3]")


class EchoLLM:
    def __init__(self):
        self.prompt = ""

    def complete(self, prompt):
        self.prompt = prompt
        return " Clause 7.3 [IEC 62304 cl 7.3] "


def test_llm_answer_receives_facts_and_evidence(result):
    llm = EchoLLM()
    engine = RagEngine(result.knowledge_base, result.store, llm, top_k=4)
    answer = engine.answer("Which clause covers verification, and what is RISK_SW_02?")
    assert answer.mode == "llm" and answer.answer == "Clause 7.3 [IEC 62304 cl 7.3]"
    assert "RISK_SW_02 is a RiskItem" in llm.prompt and "[IEC 62304 cl 7.3]" in llm.prompt
    assert "using only the evidence" in llm.prompt


def test_retrieval_evaluation_meets_the_quality_bar(result, settings):
    golden = load_golden(settings.evaluation_dir / "golden_questions.jsonl")
    report = evaluate_retrieval(result.engine, golden)
    assert report["questions"] == len(golden) == 26
    assert report["hit_rate"] >= 0.9
    assert report["mean_reciprocal_rank"] >= 0.75
    assert report["reference_token_support"] >= 0.85


def test_incident_matching_evaluation_meets_the_quality_bar(result, settings):
    gold = json.loads((settings.evaluation_dir / "incident_relevance.json").read_text(encoding="utf8"))
    report = evaluate_incident_matching(result.knowledge_base, result.scenarios, result.incidents, gold)
    assert report["scenarios"] == 39
    assert report["macro_precision"] >= 0.95
    assert report["macro_recall"] >= 0.75


def test_evaluation_report_skips_ragas_offline(result):
    report = run_evaluation(result)
    assert set(report) == {"retrieval", "incident_matching", "ragas"}
    assert report["ragas"]["status"] == "skipped"
