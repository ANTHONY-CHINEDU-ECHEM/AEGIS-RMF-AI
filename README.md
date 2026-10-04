# Aegis RMF AI

**Automated Medical Device ISO 14971 Risk Analysis Engine**

An end to end retrieval augmented system that reads medical device design documents, builds an FMEA knowledge graph, scores every risk before and after mitigation with deterministic policy lookups, grounds probability estimates in historical incident data, and generates a fully traceable ISO 14971 risk management file.

![Architecture](docs/images/architecture.png)

## Project brief

Every medical device sold in a regulated market must be supported by a risk management file. Under ISO 14971 the manufacturer has to show, for each component of the device, how it can fail, what hazardous situation the failure creates, what harm could follow, how severe and how likely that harm is, what was done to control it, and what evidence proves the control works. An auditor then picks a single line in that file and pulls the thread in both directions: forward from a component to the test report that verifies its risk control, and backward from a failed test to every risk that depended on it. A broken thread is a nonconformity, and enough of them will stop a product launch or trigger a recall.

In most companies this file lives in spreadsheets that are maintained by hand across systems, hardware, software, human factors and quality teams. The spreadsheets drift away from the design documents within weeks. Controls are credited before their verification has passed. Probability estimates made at the design stage are never revisited when complaints arrive. The cost is counted in months of remediation before a submission, and the risk is counted in patient harm when a known failure pattern in the field is never connected back to the hazard analysis.

Standard retrieval augmented generation does not solve this, and it can make it worse. Vector search returns passages that sound similar. It cannot guarantee that a requirement is linked to exactly the risks it mitigates, it cannot enforce a rule such as no credit without passing verification, and a language model asked to multiply three ratings or read a five by five matrix will sometimes get it wrong with complete confidence. Risk evaluation is a strict lookup problem over structured relationships, and an error in one cell is a regulatory finding.

Aegis RMF AI separates the two kinds of work. Retrieval is used where similarity is the right tool: finding historical incidents that resemble a failure scenario and finding the evidence that answers a question. Everything that must be exact is done by a knowledge graph and by deterministic code: the chain from component to failure mode to hazardous situation to harm to control, the severity, probability and detectability ratings, the risk priority number, the acceptability decision and the traceability matrix. A language model is optional. When present it proposes scenarios for human review and writes answers from retrieved evidence. It is never asked for a number.

The repository ships with a complete worked example: six design documents for a fictional insulin infusion pump, a synthetic corpus of 10024 adverse event reports, a risk policy, a harm catalogue and a clause catalogue covering six standards. One command turns these inputs into the risk management file described below.

## What the engine found

The sample device was written with realistic defects in its documentation. The findings below are the output of the engine on the shipped inputs and can be reproduced with `aegis run`.

### 1. Mitigation removes 63 percent of the total risk priority number, but one risk still blocks release

Thirty nine risks were extracted and scored. Before risk control 4 were acceptable, 28 needed review and 7 were unacceptable. After verified controls were credited, 23 are acceptable, 15 need review and 1 is unacceptable. The total risk priority number falls from 1919 to 703.

![Risk matrix before and after](docs/images/risk_matrix_before_after.png)

The matrix shows where the residual risk sits. Eleven risks remain in the top left cell: catastrophic severity at the lowest probability. No control can move them further, because the policy never treats a risk of death as acceptable on probability alone. For an insulin pump this is the expected shape of the file, and it tells the clinical team exactly which eleven risks the benefit risk analysis under clause 7.4 has to address.

### 2. A failed regression test is traced to the one risk it invalidates

The verification summary records that the regression test for requirement REQ_SW_005 failed. The engine walks the graph backward from that test record to the control it supports, the risk that control mitigates and the component responsible.

![Knowledge graph trace](docs/images/knowledge_graph_trace.png)

Because the control RCM_SW_03 is implemented by two requirements and only one passed, the control earns no credit. RISK_SW_02 (insulin on board not subtracted from a correction bolus) stays at a risk priority number of 80 in the UNACCEPTABLE region and the disposition is that design release is blocked. In a spreadsheet this control would very likely have been credited, because the row for the control and the row for the test result sit in different files owned by different teams.

Two further controls are denied credit for the same reason: one whose verification is still pending and one whose requirement has no verification record at all.

### 3. Field data overturns two engineering estimates

For every scenario the agent searches the incident corpus and converts the number of similar reports into a rate and then into a probability rating. Where the field rating is higher than the engineering estimate, the field rating is used.

![Field evidence](docs/images/field_evidence.png)

* Infusion set connector detachment was estimated as Occasional. 695 similar reports imply Probable. With the engineering estimate, the two controls would have brought the residual risk into the acceptable region. With the field rating, it remains in REVIEW.
* A bolus command executed twice was estimated as Remote. 52 similar reports imply Occasional, and again the residual risk moves from acceptable to REVIEW.

This is the production and post production feedback loop of clause 10 working automatically. Both risks would have been closed on paper while complaints were accumulating.

### 4. A component with no hazard analysis has 260 incident reports

The belt clip and holster is listed in the architecture specification but has no failure analysis. The gap check flags the omission and, by searching the incident corpus for the component, shows that 260 similar reports exist. An unanalysed component is a routine audit finding. An unanalysed component with a visible complaint history is a serious one.

### 5. The complete gap report

<table>
<tr><th>Level</th><th>Count</th><th>What it contains</th></tr>
<tr><td>BLOCKER</td><td>2</td><td>The failed verification and the unacceptable residual risk it causes</td></tr>
<tr><td>MAJOR</td><td>6</td><td>One component without hazard analysis, one risk with no control, one control without a verification record, one control with pending verification, two field evidence escalations</td></tr>
<tr><td>ACTION</td><td>15</td><td>Residual risks in the REVIEW region that need a benefit risk analysis</td></tr>
</table>

The standards coverage check adds one more insight. Of the 46 clauses in the catalogue, 36 have evidence in the file. The 10 without evidence are mostly management system clauses such as competence of personnel and management responsibilities, which are normally evidenced by quality system records and not by design documents. The engine reports them so that nobody assumes the design history covers them.

## How it works

### FMEA knowledge graph

The device is modelled as a property graph with twelve node labels and fifteen relationship types. The core chain follows the blueprint: Component, FailureMode, HazardousSituation, Harm, ControlMeasure. Requirements, verification records, standard clauses, document sections and incident reports are attached so that one traversal answers an audit question. The sample device produces 638 nodes and 1194 relationships.

One modelling decision goes beyond the blueprint. Harms are shared between scenarios (nine harms serve thirty nine scenarios), so attaching controls directly to a harm would let a trace from one component reach controls that belong to another. Controls and scores are therefore attached to a RiskItem node, which represents one row of the hazard analysis. The reasoning is set out in [docs/architecture.md](docs/architecture.md).

The graph layer has two interchangeable backends behind one interface: Neo4j for production and an in memory networkx store for tests and offline runs. Traversal logic is written once against the interface.

### Deterministic risk scoring agent

The agent runs a fixed plan for each scenario: resolve the component, resolve the harm in the catalogue (which fixes severity), rate detectability and engineering probability from policy terms, search incidents, select the higher probability, score, check the verification status of each control, credit controls, score again and decide the disposition. Every step is written to an audit trail that is stored with the record.

![Risk priority number before and after](docs/images/rpn_before_after.png)

Two decisions are kept apart on purpose.

* **Acceptability** uses severity and probability only, because that is how ISO 14971 defines risk. Detectability cannot make an unacceptable risk acceptable.
* **Prioritisation** uses all three ratings. The risk priority number is S x P x D, and a three dimensional lookup of 125 cells assigns an action priority, which avoids the well known problem that very different risks can share one risk priority number.

![Action priority lookup](docs/images/action_priority_cube.png)

Control credit follows five rules that are enforced in code: no credit without passing verification, credit in the clause 7.1 priority order, limits by control type, a shared limit for information for safety, and limits by dimension. The full method with a worked example is in [docs/risk_methodology.md](docs/risk_methodology.md).

### Traceability matrix generator

The matrix is produced by walking the graph, one row per risk item with 36 columns. Each row carries exact cross references in both regulatory directions: design specification references such as `SRS_003 section 4.1 (DFC_SW_02)` and `REQ_SW_005 at SRS_003 section 4.1`, and standard clause references such as `ISO 14971 cl 7.2` and `IEC 62304 cl 7.4`.

![Traceability matrix extract](docs/images/traceability_matrix_preview.png)

After the matrix is built, every link from component to requirement and verification record is walked forward and then backward. On the sample device 113 links were checked and none was broken.

### Retrieval and question answering

LlamaIndex handles chunking, indexing and retrieval over a Qdrant collection that holds design text, clause summaries, incident reports and the scored risk records. Questions are answered from graph facts for any identifier named in the question plus retrieved passages, each with its reference.

## Results

<table>
<tr><th>Measure</th><th>Value</th></tr>
<tr><td>Design documents, components, requirements, verification records</td><td>6, 23, 58, 57</td></tr>
<tr><td>Incident reports indexed</td><td>10024</td></tr>
<tr><td>Risks extracted and scored</td><td>39, with 0 extraction issues</td></tr>
<tr><td>Residual regions</td><td>23 acceptable, 15 review, 1 unacceptable</td></tr>
<tr><td>Total risk priority number</td><td>1919 before control, 703 after control</td></tr>
<tr><td>Traceability links verified in both directions</td><td>113 of 113</td></tr>
<tr><td>Gap findings</td><td>23</td></tr>
<tr><td>Pipeline run time, offline mode</td><td>About 25 seconds on a standard CPU</td></tr>
</table>

### Evaluation

<table>
<tr><th>Evaluation</th><th>Metric</th><th>Value</th></tr>
<tr><td rowspan="4">Retrieval on 26 golden questions, top 6</td><td>Hit rate</td><td>0.962</td></tr>
<tr><td>Mean reciprocal rank</td><td>0.812</td></tr>
<tr><td>Reference recall</td><td>0.962</td></tr>
<tr><td>Reference token support</td><td>0.925</td></tr>
<tr><td rowspan="2">Incident matching on 39 scenarios against labelled problem codes</td><td>Macro precision</td><td>0.982</td></tr>
<tr><td>Macro recall</td><td>0.810</td></tr>
<tr><td>RAGAS (faithfulness, answer relevancy, context precision, context recall)</td><td colspan="2">Not run in the shipped results. These metrics need a judge model. See the limitations section.</td></tr>
</table>

One golden question is missed by retrieval and is left in the set on purpose. The numbers are reported as measured.

## Repository layout

```
aegis_rmf_ai
    configs                 risk policy, harm catalogue, standards catalogue, settings
    data
        design_docs         six design documents for the sample device
        incidents           synthetic adverse event corpus and its data card
        evaluation          golden questions and incident relevance labels
    docs                    architecture, risk methodology, API reference
        images              figures rendered from a real pipeline run
    outputs
        risk_management_file    traceability matrix (CSV, Excel, HTML), risk register, coverage, gaps, summary
        evaluation              evaluation report
    scripts                 corpus generator, openFDA downloader
    src/aegis_rmf
        ingestion           document, standards and incident loaders
        retrieval           embeddings and the Qdrant knowledge base
        extraction          rule based extractor and optional language model proposals
        risk                policy lookups and scoring
        agents              risk scoring agent
        graph               graph store interface, Neo4j and memory backends, Cypher
        traceability        matrix, coverage, gaps, exporters
        rag                 question answering
        evaluation          retrieval metrics and RAGAS runner
        reporting           summary report and figures
        api                 FastAPI service
    tests                   115 tests
```

## Quick start

Python 3.10 or later is required. Create and activate a virtual environment, then from the project root:

```
pip install ".[dev]"
aegis run
```

`aegis run` builds the risk management file in offline mode and writes everything under `outputs`. No external service, model download or API key is needed.

Other commands:

```
aegis summary
aegis trace VER_SW_005 backward
aegis trace CMP_SW_01 forward
aegis score 4 3 5
aegis ask "Why is the residual risk of RISK_SW_02 unacceptable?"
aegis evaluate
aegis figures
aegis serve
pytest
```

## Running with Neo4j and Qdrant

```
docker compose up
```

This starts Neo4j, Qdrant and the API on port 8000. To run the command line tool against your own servers, set the environment variables shown in `.env.example`, for example:

```
AEGIS_GRAPH_BACKEND=neo4j AEGIS_QDRANT_URL=http://localhost:6333 aegis run
```

Once the graph is in Neo4j, the reference queries in `src/aegis_rmf/graph/cypher/traceability_queries.cypher` can be run in the Neo4j Browser.

## Optional language model and semantic embeddings

```
pip install ".[llm,semantic]"
AEGIS_LLM_PROVIDER=anthropic AEGIS_LLM_MODEL=your_model_name aegis run
```

With a language model configured the engine additionally writes scenario proposals for human review, answers questions in natural language with citations, and runs RAGAS. Set `AEGIS_EMBEDDING_BACKEND=huggingface` to use a sentence embedding model. The similarity threshold is specific to the embedding and must be tuned again with `aegis evaluate` after any change.

## API

The service exposes the risk register, deterministic scoring, forward and backward traces, the matrix in three formats, gap and coverage reports, incident search and question answering. See [docs/api_reference.md](docs/api_reference.md).

## Testing and quality

The suite contains 115 tests. They cover the policy lookups for all 125 rating combinations, every control credit rule, document parsing, extraction failures, embedding determinism, retrieval filters, the agent audit trail, graph primitives, forward and backward traces, the matrix, the gap rules, every export format, the API and the command line. Evaluation thresholds are asserted in the suite so that a retrieval regression fails the build. The code passes `ruff check`.

## Limitations

These are stated plainly so that the scope of what has been demonstrated is clear.

* **Verified here:** the whole pipeline in offline mode (in memory graph, in process Qdrant, hashing embedding, no language model), the installed command line tool, the API through the FastAPI test client, and 114 passing tests.
* **Written but not executed in the build environment:** the Neo4j backend against a live server (one integration test exists and is skipped unless `AEGIS_TEST_NEO4J_URI` is set), the Docker image and compose stack, the continuous integration workflow, Qdrant in server mode, the sentence embedding backend, the openFDA downloader, and every path that calls a real language model, including RAGAS. The language model paths are tested with stub models and their imports were checked against the pinned versions.
* **Synthetic field data.** The incident corpus is generated and its narratives are more regular than real reports. Matching quality on real data will be lower. Recall of 0.81 means field rates are understated even here.
* **Lexical default embedding.** The hashing embedding matches on shared vocabulary. It was chosen for reproducibility and will miss paraphrases that a sentence embedding model would find.
* **Structured input.** The deterministic extractor depends on the failure consideration block layout used in the sample documents. Free text design documents need the language model path and human review.
* **Illustrative policy.** The acceptability matrix, rate bounds and credit rules are examples. Clause summaries in the standards catalogue are paraphrases written for this project and are not the text of the standards.
* **Not a validated tool.** This is a portfolio project on a fictional device. It must not be used to make regulatory or clinical decisions.

## Tech stack

Python, Neo4j, LlamaIndex, Qdrant, FastAPI, RAGAS, networkx, Pydantic, openpyxl, matplotlib, pytest.

## Licence

MIT. See `LICENSE`.
