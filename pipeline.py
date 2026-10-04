"""End to end pipeline: ingest, index, extract, score, build the graph, trace, check and export."""
from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from aegis_rmf import __version__
from aegis_rmf.agents import RiskScoringAgent
from aegis_rmf.domain import ExtractedScenario, RiskRecord
from aegis_rmf.evaluation import evaluate_incident_matching, evaluate_retrieval, load_golden
from aegis_rmf.extraction import ExtractionIssue, extract_scenarios
from aegis_rmf.extraction.llm import LlamaIndexLLM, build_llm
from aegis_rmf.extraction.llm_extractor import LLMScenarioExtractor
from aegis_rmf.graph import GraphStore, build_graph, build_store
from aegis_rmf.ingestion import DesignCorpus, IncidentRecord, StandardClause, load_design_corpus, load_incidents, load_standards
from aegis_rmf.rag import RagEngine
from aegis_rmf.retrieval import KnowledgeBase
from aegis_rmf.risk import HarmCatalogue, RiskPolicy, load_harm_catalogue, load_policy
from aegis_rmf.settings import Settings, load_settings
from aegis_rmf.traceability import ClauseCoverage, Gap, TraceRow, build_matrix, exporters, find_gaps, standards_coverage, verify_bidirectional


@dataclass
class PipelineResult:
    settings: Settings
    policy: RiskPolicy
    harms: HarmCatalogue
    clauses: dict[str, StandardClause]
    corpus: DesignCorpus
    incidents: list[IncidentRecord]
    scenarios: list[ExtractedScenario]
    issues: list[ExtractionIssue]
    records: list[RiskRecord]
    knowledge_base: KnowledgeBase
    store: GraphStore
    engine: RagEngine
    matrix: list[TraceRow]
    coverage: list[ClauseCoverage]
    gaps: list[Gap]
    bidirectional: dict
    graph_warnings: list[str]
    proposals: list[ExtractedScenario] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)

    def summary(self) -> dict:
        """Headline numbers for reports, the command line and the API."""
        pre = Counter(record.pre.region.value for record in self.records)
        post = Counter(record.post.region.value for record in self.records)
        rpn_pre = sum(record.pre.rpn for record in self.records)
        rpn_post = sum(record.post.rpn for record in self.records)
        return {
            "device": self.settings.device_name,
            "documents": len(self.corpus.documents),
            "components": len(self.corpus.components),
            "requirements": len(self.corpus.requirements),
            "verification_records": len(self.corpus.verifications),
            "incident_reports": len(self.incidents),
            "risks": len(self.records),
            "regions_before_control": dict(sorted(pre.items())),
            "regions_after_control": dict(sorted(post.items())),
            "total_rpn_before_control": rpn_pre,
            "total_rpn_after_control": rpn_post,
            "total_rpn_reduction_pct": round(100.0 * (rpn_pre - rpn_post) / rpn_pre, 1) if rpn_pre else 0.0,
            "field_evidence_escalations": sorted(r.risk_id for r in self.records if r.probability_basis == "field evidence"),
            "gaps_by_level": dict(sorted(Counter(gap.level for gap in self.gaps).items())),
            "traceability_links_checked": self.bidirectional["links_checked"],
            "traceability_bidirectional": self.bidirectional["bidirectional"],
            "extraction_issues": len(self.issues),
            "graph_backend": self.settings.graph_backend,
            "embedding_backend": self.settings.embedding_backend,
            "llm_provider": self.settings.llm_provider,
        }


def run_pipeline(settings: Settings | None = None, export: bool = False) -> PipelineResult:
    """Build the complete risk management file from the configured inputs."""
    settings = settings or load_settings()
    timings: dict[str, float] = {}
    clock = time.perf_counter()

    def lap(name: str) -> None:
        nonlocal clock
        timings[name] = round(time.perf_counter() - clock, 2)
        clock = time.perf_counter()

    policy = load_policy(settings.risk_policy_path)
    harms = load_harm_catalogue(settings.harm_catalogue_path)
    clauses = load_standards(settings.standards_catalogue_path)
    corpus = load_design_corpus(settings.design_docs_dir)
    incidents = load_incidents(settings.incidents_path, settings.incident_limit)
    lap("ingest")

    knowledge_base = KnowledgeBase(settings)
    knowledge_base.reset()
    knowledge_base.index_design_units(corpus.units)
    knowledge_base.index_standards(clauses.values())
    knowledge_base.index_incidents(incidents)
    lap("index")

    scenarios, issues = extract_scenarios(corpus)
    agent = RiskScoringAgent(policy, harms, corpus, knowledge_base)
    records = [agent.assess(scenario) for scenario in scenarios]
    knowledge_base.index_risk_records(records)
    lap("extract_and_score")

    store = build_store(settings)
    graph_warnings = build_graph(store, corpus, records, clauses)
    lap("graph")

    matrix = build_matrix(store)
    coverage = standards_coverage(store)
    gaps = find_gaps(store, field_lookup=lambda text: len(knowledge_base.matching_incidents(text)))
    bidirectional = verify_bidirectional(store)
    lap("traceability")

    llm = build_llm(settings)
    proposals: list[ExtractedScenario] = []
    if llm is not None:
        extractor = LLMScenarioExtractor(llm, policy, harms, corpus)
        for unit in corpus.units:
            if unit.component_id and unit.level == 3:
                known = [s.failure_mode for s in scenarios if s.component_id == unit.component_id]
                found, proposal_issues = extractor.propose(unit, known)
                proposals.extend(found)
                issues.extend(proposal_issues)
        lap("llm_proposals")

    engine = RagEngine(knowledge_base, store, llm, settings.retrieval_top_k)
    result = PipelineResult(
        settings=settings, policy=policy, harms=harms, clauses=clauses, corpus=corpus, incidents=incidents,
        scenarios=scenarios, issues=issues, records=records, knowledge_base=knowledge_base, store=store,
        engine=engine, matrix=matrix, coverage=coverage, gaps=gaps, bidirectional=bidirectional,
        graph_warnings=graph_warnings, proposals=proposals, timings=timings,
    )
    if export:
        export_outputs(result)
    return result


def run_evaluation(result: PipelineResult) -> dict:
    """Run the deterministic evaluations, and RAGAS when a language model is configured."""
    evaluation_dir = result.settings.evaluation_dir
    golden = load_golden(evaluation_dir / "golden_questions.jsonl")
    gold_codes = json.loads((evaluation_dir / "incident_relevance.json").read_text(encoding="utf8"))
    report = {
        "retrieval": evaluate_retrieval(result.engine, golden),
        "incident_matching": evaluate_incident_matching(result.knowledge_base, result.scenarios, result.incidents, gold_codes),
    }
    if isinstance(result.engine.llm, LlamaIndexLLM):
        from aegis_rmf.evaluation.ragas_runner import run_ragas

        report["ragas"] = run_ragas(result.engine, golden)
    else:
        report["ragas"] = {"status": "skipped", "reason": "No language model configured. RAGAS metrics need a judge model."}
    return report


def export_outputs(result: PipelineResult, output_dir: Path | None = None) -> dict[str, Path]:
    """Write every deliverable of the risk management file and return the paths."""
    from aegis_rmf.reporting.summary import write_summary

    root = Path(output_dir or result.settings.output_dir)
    rmf, evaluation = root / "risk_management_file", root / "evaluation"
    rmf.mkdir(parents=True, exist_ok=True)
    evaluation.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).strftime("Generated on %d %B %Y by Aegis RMF AI ") + __version__
    title = f"ISO 14971 Traceability Matrix. {result.settings.device_name}"

    paths = {
        "matrix_csv": exporters.write_csv(rmf / "traceability_matrix.csv", result.matrix, exporters.MATRIX_COLUMNS),
        "matrix_xlsx": exporters.write_xlsx(rmf / "traceability_matrix.xlsx", result.matrix, result.coverage, result.gaps),
        "matrix_html": exporters.write_html(rmf / "traceability_matrix.html", title, result.matrix, generated),
        "risk_register": exporters.write_risk_register(rmf / "risk_register.json", result.records),
        "coverage_csv": exporters.write_csv(rmf / "standards_coverage.csv", result.coverage, exporters.COVERAGE_COLUMNS),
        "gap_csv": exporters.write_csv(rmf / "gap_report.csv", result.gaps, exporters.GAP_COLUMNS),
        "summary": write_summary(rmf / "risk_management_summary.md", result, generated),
    }
    if result.proposals:
        paths["proposals"] = rmf / "llm_proposals_for_review.json"
        paths["proposals"].write_text(json.dumps([p.model_dump(mode="json") for p in result.proposals], indent=2), encoding="utf8")

    paths["evaluation"] = evaluation / "evaluation_report.json"
    paths["evaluation"].write_text(json.dumps(run_evaluation(result), indent=2), encoding="utf8")
    manifest = {
        "generated": generated, "summary": result.summary(), "graph": result.store.stats(),
        "vector_index": result.knowledge_base.counts, "timings_seconds": result.timings,
        "graph_warnings": result.graph_warnings, "extraction_issues": [issue.model_dump() for issue in result.issues],
        "policy": {"id": result.policy.policy_id, "revision": result.policy.revision},
    }
    paths["manifest"] = root / "run_manifest.json"
    paths["manifest"].write_text(json.dumps(manifest, indent=2), encoding="utf8")
    return paths
