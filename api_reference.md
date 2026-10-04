# API Reference

Start the service with `aegis serve`. Interactive documentation is served at `/docs` by FastAPI. The risk management file is built on the first request, which takes roughly half a minute in offline mode, and is then held in memory.

## Endpoints

### GET /health

Service status, version and whether the risk management file has been built.

### GET /summary

Headline numbers: counts of documents, components, requirements and risks, regions before and after control, total risk priority number, field evidence escalations, gap counts and backend names.

### POST /pipeline/run

Rebuilds the risk management file. Body: `{"export": true}` also writes all files to the output directory.

### GET /risks

Lists risks. Optional query parameters: `region` (ACCEPTABLE, REVIEW or UNACCEPTABLE, applied to the residual region) and `component_id`.

### GET /risks/{risk_id}

The full risk record: scenario text, scores before and after control, control credits with notes, field evidence, clause references, source reference and the audit trail of the scoring agent.

### POST /score

Deterministic scoring of three ratings. Body: `{"severity": 4, "probability": 3, "detectability": 5}`. Returns the risk priority number, band, acceptability region and action priority. Ratings outside 1 to 5 are rejected.

### GET /trace/{node_id}

Trace from any graph node. Query parameter `direction` is `forward` or `backward`. Returns reachable node identifiers grouped by label.

### GET /traceability/matrix

The traceability matrix. Query parameter `format` is `json`, `csv` or `html`.

### GET /traceability/gaps

Gap findings ordered by level.

### GET /traceability/coverage

Evidence per standard clause.

### GET /traceability/verification

Result of the bidirectional link check.

### POST /incidents/search

Vector search over the incident corpus. Body: `{"query": "battery depleted without warning", "top_k": 5}`. Returns the number of reports above the similarity threshold, the implied rate and probability rating, and the top reports.

### POST /query

Question answering. Body: `{"question": "Why is the residual risk of RISK_SW_02 unacceptable?"}`. Returns the answer, the mode (`extractive` or `llm`), graph facts and retrieved contexts with references.

### GET /graph/stats

Node counts by label and relationship counts by type.

## Example

```python
import httpx

api = "http://localhost:8000"
print(httpx.get(f"{api}/trace/VER_SW_005", params={"direction": "backward"}).json()["reachable"])
print(httpx.post(f"{api}/score", json={"severity": 5, "probability": 1, "detectability": 2}).json())
answer = httpx.post(f"{api}/query", json={"question": "Which risks depend on REQ_SW_005?"}, timeout=120).json()
print(answer["answer"])
```
