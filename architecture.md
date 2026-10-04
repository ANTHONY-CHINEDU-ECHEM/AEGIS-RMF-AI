# Architecture

![Architecture](images/architecture.png)

## Design goals

Aegis RMF AI is built around four rules that follow from how a risk management file is audited.

* Numbers never come from a language model. Severity, probability, detectability, the risk priority number, the acceptability region and the action priority are all lookups or arithmetic in code.
* Every statement has an address. Each record carries the document identifier, section number and anchor it came from, and each regulatory reference is a key into a clause catalogue.
* The graph is the system of record. The traceability matrix is produced by walking the graph, so the export is exactly what a query against the database returns.
* The same code runs offline and in production. Storage backends are interchangeable behind small interfaces, so tests and air gapped validation use the same logic as the Neo4j and Qdrant deployment.

## Pipeline stages

### 1. Ingestion (`aegis_rmf.ingestion`)

Design documents are markdown files. The parser splits each file at every heading into units and records the section number, the component tag in the heading and the starting line. From the units it builds the component registry (from the architecture specification), the requirement register with verification and standards tags, and the verification register. The standards catalogue and the incident corpus are loaded alongside.

### 2. Indexing (`aegis_rmf.retrieval`)

One Qdrant collection holds four kinds of evidence, separated by a `source_type` payload field: design document chunks, standard clause summaries, incident reports and, later, the scored risk records. Chunking uses the LlamaIndex sentence splitter. Nodes are inserted through a LlamaIndex `VectorStoreIndex` over a `QdrantVectorStore`. Node identifiers are derived deterministically from the reference, so a second run overwrites the same points.

Two embedding backends are available. The default hashing embedding is a deterministic lexical embedding with no model download. A sentence embedding model from Hugging Face can be selected in the settings.

### 3. Scenario extraction (`aegis_rmf.extraction`)

The rule based extractor parses the design failure consideration blocks. A block with a missing field, an unknown component, an unknown control type or an unknown requirement is reported as an extraction issue and is not silently repaired.

When a language model is configured, a second extractor asks it to propose failure scenarios implied by narrative text. Proposals are restricted to the vocabulary of the policy and the harm catalogue, validated, and written to a review file. They never enter the risk management file without a human decision.

### 4. Risk scoring agent (`aegis_rmf.agents`)

For each scenario the agent runs a fixed plan and logs each step.

1. Resolve the component in the registry
2. Resolve the harm text against the harm catalogue, which fixes severity
3. Rate detectability from the stated detection method
4. Rate the engineering probability from the stated occurrence term
5. Search the incident corpus and count reports above the similarity threshold
6. Convert the count into a rate per 100000 device years and then into a probability rating
7. Take the higher of the engineering and field ratings
8. Compute the score before control
9. Establish the verification status of every control from its implementing requirements
10. Credit controls under the policy and compute the residual score
11. Decide the disposition

The audit trail is stored with the record and returned by the API.

### 5. Knowledge graph (`aegis_rmf.graph`)

Node labels: Component, FailureMode, HazardousSituation, Hazard, Harm, RiskItem, ControlMeasure, Requirement, Verification, StandardClause, DocumentSection, Incident.

Relationships:

* Component HAS_FAILURE_MODE FailureMode
* FailureMode LEADS_TO HazardousSituation
* HazardousSituation RESULTS_IN Harm
* HazardousSituation INVOLVES_HAZARD Hazard
* HazardousSituation ASSESSED_AS RiskItem
* RiskItem FOR_HARM Harm
* RiskItem CONTROLLED_BY ControlMeasure (carries claimed credit, credited credit and verification status)
* ControlMeasure IMPLEMENTED_BY Requirement
* Requirement VERIFIED_BY Verification
* Requirement COMPLIES_WITH StandardClause
* RiskItem GOVERNED_BY StandardClause
* RiskItem SUPPORTED_BY Incident (carries similarity)
* Component HAS_REQUIREMENT Requirement
* Component, FailureMode and Requirement DOCUMENTED_IN DocumentSection
* DocumentSection CITES StandardClause

![Graph trace](images/knowledge_graph_trace.png)

#### Why controls attach to a risk item and not to a harm

The project blueprint describes a chain that ends Harm to Control Measure. Harm nodes are shared: nine harms serve thirty nine scenarios. If controls hung directly off a harm, a trace from one component would reach controls that belong to unrelated components that happen to cause the same harm. The RiskItem node represents one row of the hazard analysis, which is the unit that ISO 14971 asks to be estimated, controlled and evaluated, so controls and scores attach there. The blueprint chain is still present and can be walked, and a test confirms that shared harms do not leak controls between risks.

#### Backends

`GraphStore` defines seven primitives. `MemoryGraphStore` implements them on networkx. `Neo4jGraphStore` implements them in Cypher with a shared `Entity` label and a uniqueness constraint on `Entity.id`. Traversals are written once against the primitives. Reference Cypher for analysts is in `src/aegis_rmf/graph/cypher/traceability_queries.cypher`.

### 6. Traceability (`aegis_rmf.traceability`)

* `build_matrix` walks from each RiskItem to its component, failure mode, hazardous situation, hazard, harm, controls, requirements, verification records, clauses, design references and incident evidence.
* `verify_bidirectional` walks every link from component to requirement and verification forward, then walks it backward, and reports any link that cannot be completed in both directions.
* `standards_coverage` lists, for every clause in the catalogue, the risk items, requirements and document sections that address it.
* `find_gaps` applies eight audit rules and grades findings as BLOCKER, MAJOR or ACTION.

### 7. Question answering (`aegis_rmf.rag`)

A question is answered from two sources of evidence. Identifiers named in the question are resolved in the graph and described with exact trace facts. Vector search adds design text, clause summaries and risk records, plus incident reports when the question concerns field data. With a language model configured the evidence is passed to the model with an instruction to answer only from it and to cite references. Without one, the engine returns the evidence itself.

### 8. Evaluation (`aegis_rmf.evaluation`)

Deterministic metrics run on every pipeline run: retrieval hit rate, mean reciprocal rank and reference recall on a golden question set, and precision and recall of incident matching against the labelled corpus. RAGAS metrics (faithfulness, answer relevancy, context precision, context recall) run when a language model is configured, because they need a judge model.

## Deployment

`compose.yaml` starts Neo4j, Qdrant and the API. The API builds the risk management file on the first request and keeps it in memory. `POST /pipeline/run` rebuilds it.
