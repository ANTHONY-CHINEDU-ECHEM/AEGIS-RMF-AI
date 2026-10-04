"""RAGAS evaluation of generated answers.

RAGAS metrics are judged by a language model, so this runner is only used when llm_provider is
configured. Install the optional dependencies with: pip install ".[llm]"
"""
from __future__ import annotations

from aegis_rmf.rag.engine import RagEngine


def build_samples(engine: RagEngine, golden: list[dict]) -> list[dict]:
    """Answer every golden question and collect the fields RAGAS expects."""
    samples = []
    for item in golden:
        answer = engine.answer(item["question"])
        samples.append({
            "user_input": item["question"],
            "response": answer.answer,
            "retrieved_contexts": answer.graph_facts + [hit.text for hit in answer.contexts],
            "reference": item["reference_answer"],
        })
    return samples


def run_ragas(engine: RagEngine, golden: list[dict]) -> dict:
    """Score faithfulness, answer relevancy, context precision and context recall."""
    if engine.llm is None:
        raise RuntimeError("RAGAS evaluation needs a language model. Set llm_provider in the settings.")
    from ragas import EvaluationDataset, evaluate
    from ragas.embeddings import LlamaIndexEmbeddingsWrapper
    from ragas.llms import LlamaIndexLLMWrapper
    from ragas.metrics import Faithfulness, LLMContextPrecisionWithReference, LLMContextRecall, ResponseRelevancy

    dataset = EvaluationDataset.from_list(build_samples(engine, golden))
    result = evaluate(
        dataset=dataset,
        metrics=[Faithfulness(), ResponseRelevancy(), LLMContextPrecisionWithReference(), LLMContextRecall()],
        llm=LlamaIndexLLMWrapper(engine.llm.llm),
        embeddings=LlamaIndexEmbeddingsWrapper(engine.kb.embedding),
    )
    frame = result.to_pandas()
    metric_columns = [c for c in frame.columns if c not in ("user_input", "response", "retrieved_contexts", "reference")]
    return {
        "questions": len(frame),
        "metrics": {column: round(float(frame[column].mean()), 3) for column in metric_columns},
    }
