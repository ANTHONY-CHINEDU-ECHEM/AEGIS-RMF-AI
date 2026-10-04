"""HTTP interface and command line interface."""
import json

import pytest
from fastapi.testclient import TestClient

from aegis_rmf import cli
from aegis_rmf.api import main as api


@pytest.fixture()
def client(result):
    api._state["result"] = result
    yield TestClient(api.app)
    api.reset_state()


def test_health_and_summary(client):
    assert client.get("/health").json()["status"] == "ok"
    summary = client.get("/summary").json()
    assert summary["risks"] == 39 and summary["traceability_bidirectional"] is True


def test_list_and_filter_risks(client):
    assert len(client.get("/risks").json()) == 39
    blocked = client.get("/risks", params={"region": "unacceptable"}).json()
    assert [risk["risk_id"] for risk in blocked] == ["RISK_SW_02"]
    by_component = client.get("/risks", params={"component_id": "CMP_SW_01"}).json()
    assert [risk["risk_id"] for risk in by_component] == ["RISK_SW_01", "RISK_SW_02"]


def test_risk_detail_includes_audit_trail(client):
    body = client.get("/risks/RISK_INF_01").json()
    assert body["probability_basis"] == "field evidence" and body["audit"][0]["tool"] == "resolve_component"
    assert client.get("/risks/RISK_NOPE_01").status_code == 404


def test_score_endpoint(client):
    body = client.post("/score", json={"severity": 4, "probability": 3, "detectability": 5}).json()
    assert body == {"severity": 4, "probability": 3, "detectability": 5, "rpn": 60, "rpn_band": "MEDIUM",
                    "region": "REVIEW", "action_priority": "HIGH"}
    assert client.post("/score", json={"severity": 6, "probability": 3, "detectability": 5}).status_code == 422


def test_trace_endpoint(client):
    backward = client.get("/trace/VER_SW_005", params={"direction": "backward"}).json()
    assert backward["reachable"]["Component"] == ["CMP_SW_01"]
    forward = client.get("/trace/CMP_SW_01").json()
    assert forward["direction"] == "forward" and "RISK_SW_02" in forward["reachable"]["RiskItem"]
    assert client.get("/trace/CMP_NOPE").status_code == 404
    assert client.get("/trace/CMP_SW_01", params={"direction": "sideways"}).status_code == 422


def test_matrix_formats(client):
    assert len(client.get("/traceability/matrix").json()) == 39
    table = client.get("/traceability/matrix", params={"format": "csv"})
    assert table.headers["content-type"].startswith("text/csv") and table.text.splitlines()[0].startswith("Risk ID,Title")
    assert len(table.text.strip().splitlines()) >= 40


def test_gap_coverage_and_verification_endpoints(client):
    gaps = client.get("/traceability/gaps").json()
    assert gaps[0]["level"] == "BLOCKER"
    assert len(client.get("/traceability/coverage").json()) == 46
    assert client.get("/traceability/verification").json()["bidirectional"] is True
    assert client.get("/graph/stats").json()["nodes"]["RiskItem"] == 39


def test_incident_search_endpoint(client):
    body = client.post("/incidents/search", json={"query": "battery depleted suddenly without low battery warning and pump shut down", "top_k": 3}).json()
    assert body["matched_count"] > 100 and body["implied_probability"] == 3
    assert len(body["top_reports"]) == 3 and body["top_reports"][0]["source_type"] == "incident"


def test_query_endpoint(client):
    body = client.post("/query", json={"question": "Why is the residual risk of RISK_SW_02 unacceptable?"}).json()
    assert body["mode"] == "extractive" and "verification status FAIL" in body["answer"]
    assert client.post("/query", json={"question": "?"}).status_code == 422


def test_cli_score(capsys):
    assert cli.main(["score", "5", "1", "2"]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["rpn"] == 10 and body["region"] == "REVIEW" and body["action_priority"] == "MEDIUM"


def test_cli_trace_and_ask(capsys, monkeypatch, result):
    monkeypatch.setattr(cli, "run_pipeline", lambda: result)
    assert cli.main(["trace", "VER_SW_005", "backward"]) == 0
    assert json.loads(capsys.readouterr().out)["RiskItem"] == ["RISK_SW_02"]
    assert cli.main(["trace", "CMP_NOPE"]) == 1
    capsys.readouterr()
    assert cli.main(["ask", "What ingress protection rating must the enclosure meet?"]) == 0
    assert "IPX8" in capsys.readouterr().out
