"""Deterministic evaluation metrics that need no language model."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from aegis_rmf.domain import ExtractedScenario
from aegis_rmf.ingestion.incidents import IncidentRecord
from aegis_rmf.rag.engine import RagEngine
from aegis_rmf.retrieval.embeddings import tokenize
from aegis_rmf.retrieval.knowledge_base import KnowledgeBase


def load_golden(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _satisfies(ref: str, want: str) -> bool:
    return ref == want or ref.startswith(f"{want}:")


def evaluate_retrieval(engine: RagEngine, golden: list[dict]) -> dict:
    """Hit rate, mean reciprocal rank and reference recall of the retrieval stage.

    A context counts as relevant when its reference equals an expected reference or lies beneath
    it, so HDS_002:3.1:DFC_DRV_01 satisfies the expected reference HDS_002:3.1.
    """
    per_question, hit_total, reciprocal_total, recall_total, support_total = [], 0, 0.0, 0.0, 0.0
    for item in golden:
        hits, facts = engine.retrieve(item["question"])
        retrieved = [hit.ref_id for hit in hits]
        expected = item["expected_refs"]

        ranks = [rank for rank, ref in enumerate(retrieved, start=1) if any(_satisfies(ref, want) for want in expected)]
        found = sum(1 for want in expected if any(_satisfies(ref, want) for ref in retrieved))
        evidence_tokens = set(tokenize(" ".join([hit.text for hit in hits] + facts)))
        reference_tokens = set(tokenize(item["reference_answer"]))
        support = len(reference_tokens & evidence_tokens) / len(reference_tokens) if reference_tokens else 0.0
        hit_total += 1 if ranks else 0
        reciprocal_total += 1.0 / ranks[0] if ranks else 0.0
        recall_total += found / len(expected)
        support_total += support
        per_question.append({
            "id": item["id"], "first_relevant_rank": ranks[0] if ranks else None,
            "reference_recall": round(found / len(expected), 3), "reference_token_support": round(support, 3),
        })
    count = len(golden)
    return {
        "questions": count,
        "top_k": engine.top_k,
        "hit_rate": round(hit_total / count, 3),
        "mean_reciprocal_rank": round(reciprocal_total / count, 3),
        "reference_recall": round(recall_total / count, 3),
        "reference_token_support": round(support_total / count, 3),
        "per_question": per_question,
    }


def evaluate_incident_matching(
    knowledge_base: KnowledgeBase, scenarios: list[ExtractedScenario], incidents: list[IncidentRecord], gold: dict[str, str],
) -> dict:
    """Precision and recall of threshold matching against the labelled problem codes of the corpus."""
    truth = Counter(record.product_problem_code for record in incidents)
    per_scenario, precision_total, recall_total, scored = [], 0.0, 0.0, 0
    for scenario in scenarios:
        code = gold.get(scenario.dfc_id)
        if not code or not truth.get(code):
            continue
        query = f"{scenario.failure_mode}. {scenario.cause}. {scenario.hazardous_situation}."
        matches = knowledge_base.matching_incidents(query)
        correct = sum(1 for match in matches if match.get("product_problem_code") == code)
        precision = correct / len(matches) if matches else 0.0
        recall = correct / truth[code]
        precision_total += precision
        recall_total += recall
        scored += 1
        per_scenario.append({
            "dfc_id": scenario.dfc_id, "problem_code": code, "matched": len(matches), "labelled": truth[code],
            "precision": round(precision, 3), "recall": round(recall, 3),
        })
    return {
        "scenarios": scored,
        "similarity_threshold": knowledge_base.settings.similarity_threshold,
        "macro_precision": round(precision_total / scored, 3) if scored else 0.0,
        "macro_recall": round(recall_total / scored, 3) if scored else 0.0,
        "per_scenario": per_scenario,
    }
