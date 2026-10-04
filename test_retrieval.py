"""Embedding determinism and vector retrieval over the Qdrant knowledge base."""
import numpy as np
import pytest

from aegis_rmf.retrieval.embeddings import HashingEmbedding, build_embedding, tokenize
from aegis_rmf.retrieval.knowledge_base import DESIGN, INCIDENT, RISK, STANDARD


def test_tokenizer_stems_and_drops_stopwords():
    assert tokenize("The motors stalled while delivering") == ["motor", "stall", "deliver"]


def test_hashing_embedding_is_deterministic_and_normalised():
    model = HashingEmbedding(model_name="test", dim=256)
    first = model.get_text_embedding("Battery depletes without warning")
    second = model.get_text_embedding("Battery depletes without warning")
    assert first == second and len(first) == 256
    assert np.isclose(np.linalg.norm(first), 1.0)


def test_hashing_embedding_ranks_related_text_higher():
    model = HashingEmbedding(model_name="test", dim=1024)
    query = np.array(model.get_query_embedding("battery depleted without a low battery warning"))
    related = np.array(model.get_text_embedding("The battery depleted suddenly and no low battery warning was given"))
    unrelated = np.array(model.get_text_embedding("The infusion set connector detached from the reservoir"))
    assert query @ related > 0.4 > query @ unrelated


def test_empty_text_gives_zero_vector():
    assert not any(HashingEmbedding(model_name="test", dim=64).get_text_embedding("the of and"))


def test_unknown_embedding_backend_is_rejected(settings):
    with pytest.raises(ValueError):
        build_embedding(settings.model_copy(update={"embedding_backend": "telepathy"}))


def test_index_holds_all_four_evidence_types(result):
    counts = result.knowledge_base.counts
    assert counts[INCIDENT] == len(result.incidents) == 10024
    assert counts[STANDARD] == len(result.clauses)
    assert counts[RISK] == 39
    assert counts[DESIGN] >= len(result.corpus.units)


def test_search_respects_source_type_filter(result):
    hits = result.knowledge_base.search("verification of risk control measures", [STANDARD], top_k=3)
    assert len(hits) == 3 and {hit.source_type for hit in hits} == {STANDARD}
    assert hits[0].ref_id == "IEC 62304 cl 7.3"
    assert [hit.score for hit in hits] == sorted((hit.score for hit in hits), reverse=True)


def test_design_search_returns_exact_section_reference(result):
    hits = result.knowledge_base.search("battery depletes suddenly without a low battery warning", [DESIGN], top_k=3)
    assert hits[0].ref_id == "HDS_002:6.1:DFC_PWR_02"
    assert hits[0].metadata["doc_id"] == "HDS_002" and hits[0].metadata["section"] == "6.1"


def test_threshold_matching_counts_incidents(result):
    kb = result.knowledge_base
    matches = kb.matching_incidents("The infusion set connector detached from the reservoir and insulin leaked onto the skin")
    assert len(matches) > 400
    assert all(match["score"] >= kb.settings.similarity_threshold for match in matches)
    assert kb.matching_incidents("quantum flux capacitor misalignment in the warp nacelle") == []
    assert len(kb.matching_incidents("connector detached", threshold=0.99)) == 0
