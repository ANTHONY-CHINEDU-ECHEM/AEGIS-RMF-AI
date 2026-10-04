"""Graph store primitives and the knowledge graph built by the pipeline."""
import os

import pytest

from aegis_rmf.graph import MemoryGraphStore, build_graph, build_store
from aegis_rmf.graph.base import BACKWARD, FORWARD


def small_store():
    store = MemoryGraphStore()
    store.upsert_node("Component", "C1", {"name": "Pump"})
    store.upsert_node("FailureMode", "F1", {"name": "Stall"})
    store.upsert_node("FailureMode", "F2", {"name": "Leak"})
    store.upsert_edge("C1", "HAS_FAILURE_MODE", "F1", {"weight": 1})
    store.upsert_edge("C1", "HAS_FAILURE_MODE", "F2")
    return store


def test_upsert_merges_properties():
    store = small_store()
    store.upsert_node("Component", "C1", {"subsystem": "Drive"})
    assert store.get_node("C1") == {"id": "C1", "name": "Pump", "subsystem": "Drive", "label": "Component"}
    assert store.get_node("missing") is None


def test_edges_are_idempotent_and_directed():
    store = small_store()
    store.upsert_edge("C1", "HAS_FAILURE_MODE", "F1", {"weight": 2})
    forward = store.neighbors("C1", "HAS_FAILURE_MODE", FORWARD)
    assert [(node["id"], rel, props) for node, rel, props in forward] == [("F1", "HAS_FAILURE_MODE", {"weight": 2}), ("F2", "HAS_FAILURE_MODE", {})]
    assert [node["id"] for node in store.into("F1", "HAS_FAILURE_MODE")] == ["C1"]
    assert store.neighbors("F1", None, FORWARD) == []


def test_unknown_labels_relationships_and_nodes_are_rejected():
    store = small_store()
    with pytest.raises(ValueError):
        store.upsert_node("Gadget", "G1", {})
    with pytest.raises(ValueError):
        store.upsert_edge("C1", "LIKES", "F1")
    with pytest.raises(KeyError):
        store.upsert_edge("C1", "HAS_FAILURE_MODE", "F9")
    with pytest.raises(KeyError):
        store.trace("F9")


def test_stats_and_clear():
    store = small_store()
    assert store.stats() == {"nodes": {"Component": 1, "FailureMode": 2}, "relationships": {"HAS_FAILURE_MODE": 2}}
    store.clear()
    assert store.stats() == {"nodes": {}, "relationships": {}}


def test_pipeline_graph_shape(result):
    stats = result.store.stats()
    assert stats["nodes"]["Component"] == 23
    assert stats["nodes"]["RiskItem"] == stats["nodes"]["FailureMode"] == stats["nodes"]["HazardousSituation"] == 39
    assert stats["nodes"]["Harm"] == 9 and stats["nodes"]["ControlMeasure"] == 53
    assert stats["relationships"]["HAS_FAILURE_MODE"] == stats["relationships"]["LEADS_TO"] == stats["relationships"]["RESULTS_IN"] == 39
    assert stats["relationships"]["VERIFIED_BY"] == 57


def test_blueprint_chain_can_be_walked(result):
    store = result.store
    failure_modes = store.out("CMP_SW_01", "HAS_FAILURE_MODE")
    assert [node["id"] for node in failure_modes] == ["FM_SW_01", "FM_SW_02"]
    situation = store.out("FM_SW_02", "LEADS_TO")[0]
    assert store.out(situation["id"], "RESULTS_IN")[0]["id"] == "HARM_HYPO_MODERATE"
    risk = store.out(situation["id"], "ASSESSED_AS")[0]
    control, _, edge = store.neighbors(risk["id"], "CONTROLLED_BY", FORWARD)[0]
    assert control["id"] == "RCM_SW_03" and edge["verification_status"] == "FAIL" and edge["credited_occurrence"] == 0
    assert [node["id"] for node in store.out("RCM_SW_03", "IMPLEMENTED_BY")] == ["REQ_SW_004", "REQ_SW_005"]


def test_forward_and_backward_trace(result):
    forward = result.store.trace("CMP_SW_01", FORWARD)
    assert forward["RiskItem"] == ["RISK_SW_01", "RISK_SW_02"]
    assert "VER_SW_005" in forward["Verification"] and "HARM_HYPO_SEVERE" in forward["Harm"]
    backward = result.store.trace("VER_SW_005", BACKWARD)
    assert backward["Requirement"] == ["REQ_SW_005"] and backward["ControlMeasure"] == ["RCM_SW_03"]
    assert backward["RiskItem"] == ["RISK_SW_02"] and backward["Component"] == ["CMP_SW_01"]


def test_shared_control_traces_back_to_every_risk_it_mitigates(result):
    backward = result.store.trace("RCM_MCU_03", BACKWARD)
    assert backward["RiskItem"] == ["RISK_DRV_01", "RISK_MCU_02"]


def test_shared_harm_does_not_leak_controls_between_risks(result):
    """Controls hang off the risk item, so a harm shared by many risks cannot mix their controls."""
    store = result.store
    assert len(store.into("HARM_DKA", "FOR_HARM")) > 5
    assert store.neighbors("HARM_DKA", None, FORWARD) == []


def test_rebuild_is_idempotent(result):
    store = MemoryGraphStore()
    build_graph(store, result.corpus, result.records, result.clauses)
    first = store.stats()
    build_graph(store, result.corpus, result.records, result.clauses)
    assert store.stats() == first == result.store.stats()


def test_unknown_backend_is_rejected(settings):
    with pytest.raises(ValueError):
        build_store(settings.model_copy(update={"graph_backend": "papyrus"}))


@pytest.mark.skipif(not os.environ.get("AEGIS_TEST_NEO4J_URI"), reason="Set AEGIS_TEST_NEO4J_URI to run against a live Neo4j server")
def test_neo4j_store_matches_memory_store(result):
    """Integration test: the Neo4j backend must reproduce the in memory graph exactly."""
    from aegis_rmf.graph.neo4j_store import Neo4jGraphStore
    from aegis_rmf.traceability import build_matrix, verify_bidirectional

    store = Neo4jGraphStore(
        os.environ["AEGIS_TEST_NEO4J_URI"], os.environ.get("AEGIS_TEST_NEO4J_USER", "neo4j"),
        os.environ.get("AEGIS_TEST_NEO4J_PASSWORD", "aegis_password"),
    )
    try:
        build_graph(store, result.corpus, result.records, result.clauses)
        assert store.stats() == result.store.stats()
        assert store.trace("VER_SW_005", BACKWARD) == result.store.trace("VER_SW_005", BACKWARD)
        assert [row.model_dump() for row in build_matrix(store)] == [row.model_dump() for row in result.matrix]
        assert verify_bidirectional(store)["bidirectional"]
    finally:
        store.clear()
        store.close()
