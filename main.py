"""HTTP interface to the risk management file.

Start the service with the command aegis serve, or with: uvicorn aegis_rmf.api.main:app
"""
from __future__ import annotations

import csv
import io
from threading import Lock

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse

from aegis_rmf import __version__
from aegis_rmf.api.schemas import IncidentSearchRequest, PipelineRunRequest, QueryRequest, RiskBrief, ScoreRequest
from aegis_rmf.domain import RiskRecord, RiskScore
from aegis_rmf.graph.base import BACKWARD, FORWARD
from aegis_rmf.pipeline import PipelineResult, run_pipeline
from aegis_rmf.rag import Answer
from aegis_rmf.retrieval.knowledge_base import INCIDENT
from aegis_rmf.risk.scoring import score
from aegis_rmf.traceability import exporters

app = FastAPI(
    title="Aegis RMF AI",
    version=__version__,
    description="Automated ISO 14971 risk analysis engine with a traceable knowledge graph.",
)
_state: dict[str, PipelineResult] = {}
_lock = Lock()


def state(rebuild: bool = False, export: bool = False) -> PipelineResult:
    """Build the risk management file on first use and reuse it afterwards."""
    with _lock:
        if rebuild or "result" not in _state:
            _state["result"] = run_pipeline(export=export)
        return _state["result"]


def reset_state() -> None:
    with _lock:
        _state.clear()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "loaded": "result" in _state}


@app.get("/summary")
def summary() -> dict:
    return state().summary()


@app.post("/pipeline/run")
def pipeline_run(request: PipelineRunRequest) -> dict:
    result = state(rebuild=True, export=request.export)
    return {"summary": result.summary(), "timings_seconds": result.timings}


@app.get("/risks", response_model=list[RiskBrief])
def list_risks(region: str | None = None, component_id: str | None = None) -> list[RiskBrief]:
    """List risks, optionally filtered by residual region or component."""
    records = state().records
    if region:
        records = [r for r in records if r.post.region.value == region.upper()]
    if component_id:
        records = [r for r in records if r.component_id == component_id]
    return [
        RiskBrief(
            risk_id=r.risk_id, title=r.title, component_id=r.component_id, harm=r.harm,
            rpn_before=r.pre.rpn, region_before=r.pre.region.value, rpn_after=r.post.rpn,
            region_after=r.post.region.value, action_priority=r.post.action_priority.value, disposition=r.disposition,
        )
        for r in records
    ]


@app.get("/risks/{risk_id}", response_model=RiskRecord)
def get_risk(risk_id: str) -> RiskRecord:
    """Full record for one risk, including the audit trail of the scoring agent."""
    for record in state().records:
        if record.risk_id == risk_id:
            return record
    raise HTTPException(status_code=404, detail=f"Unknown risk {risk_id}")


@app.post("/score", response_model=RiskScore)
def score_risk(request: ScoreRequest) -> RiskScore:
    """Deterministic lookup of RPN, acceptability region and action priority."""
    return score(state().policy, request.severity, request.probability, request.detectability)


@app.get("/trace/{node_id}")
def trace(node_id: str, direction: str = Query(default=FORWARD, pattern="^(forward|backward)$")) -> dict:
    store = state().store
    node = store.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Unknown node {node_id}")
    return {"node": node, "direction": direction, "reachable": store.trace(node_id, FORWARD if direction == FORWARD else BACKWARD)}


@app.get("/traceability/matrix")
def matrix(format: str = Query(default="json", pattern="^(json|csv|html)$")):
    result = state()
    if format == "json":
        return [row.model_dump() for row in result.matrix]
    if format == "html":
        path = result.settings.output_dir / "risk_management_file"
        path.mkdir(parents=True, exist_ok=True)
        title = f"ISO 14971 Traceability Matrix. {result.settings.device_name}"
        exporters.write_html(path / "traceability_matrix.html", title, result.matrix, "Served by the Aegis RMF AI API")
        return HTMLResponse((path / "traceability_matrix.html").read_text(encoding="utf8"))
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([header for header, _, _ in exporters.MATRIX_COLUMNS])
    for row in result.matrix:
        writer.writerow([exporters._cell(getattr(row, key)) for _, key, _ in exporters.MATRIX_COLUMNS])
    return PlainTextResponse(buffer.getvalue(), media_type="text/csv")


@app.get("/traceability/gaps")
def gaps() -> list[dict]:
    return [gap.model_dump() for gap in state().gaps]


@app.get("/traceability/coverage")
def coverage() -> list[dict]:
    return [clause.model_dump() for clause in state().coverage]


@app.get("/traceability/verification")
def verification() -> dict:
    return state().bidirectional


@app.post("/incidents/search")
def incident_search(request: IncidentSearchRequest) -> dict:
    """Vector search over the incident corpus with the implied probability rating."""
    result = state()
    matches = result.knowledge_base.matching_incidents(request.query)
    rate = len(matches) / result.policy.exposure_device_years * 100000.0
    hits = result.knowledge_base.search(request.query, [INCIDENT], request.top_k)
    return {
        "matched_count": len(matches),
        "rate_per_100k_device_years": round(rate, 3),
        "implied_probability": result.policy.probability_from_rate(rate) if matches else 1,
        "top_reports": [hit.model_dump() for hit in hits],
    }


@app.post("/query", response_model=Answer)
def query(request: QueryRequest) -> Answer:
    """Answer a question with graph facts and retrieved evidence."""
    return state().engine.answer(request.question)


@app.get("/graph/stats")
def graph_stats() -> dict:
    return state().store.stats()
