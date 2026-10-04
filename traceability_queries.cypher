// Aegis RMF AI reference queries for the Neo4j Browser.
// Run one statement at a time. Parameters are shown with example values.

// 1. Forward trace: full FMEA chain for one component.
MATCH (c:Component {id: 'CMP_SW_01'})-[:HAS_FAILURE_MODE]->(fm:FailureMode)-[:LEADS_TO]->(hs:HazardousSituation)-[:RESULTS_IN]->(h:Harm)
MATCH (hs)-[:ASSESSED_AS]->(r:RiskItem)
OPTIONAL MATCH (r)-[cb:CONTROLLED_BY]->(cm:ControlMeasure)-[:IMPLEMENTED_BY]->(req:Requirement)
OPTIONAL MATCH (req)-[:VERIFIED_BY]->(v:Verification)
RETURN c.id, fm.name, hs.name, h.name, r.id, r.rpn_pre, r.rpn_post, r.region_post, cm.id, cb.verification_status, req.id, v.id, v.result
ORDER BY r.id, cm.id, req.id;

// 2. Backward trace: which risks and components depend on one verification record.
MATCH (v:Verification {id: 'VER_SW_005'})<-[:VERIFIED_BY]-(req:Requirement)<-[:IMPLEMENTED_BY]-(cm:ControlMeasure)<-[:CONTROLLED_BY]-(r:RiskItem)
MATCH (c:Component)-[:HAS_FAILURE_MODE]->(:FailureMode)-[:LEADS_TO]->(:HazardousSituation)-[:ASSESSED_AS]->(r)
RETURN v.id, v.result, req.id, cm.id, r.id, r.region_post, c.id, c.name;

// 3. Residual risks that are not acceptable, highest residual risk priority number first.
MATCH (r:RiskItem) WHERE r.region_post <> 'ACCEPTABLE'
RETURN r.id, r.title, r.severity_post, r.probability_post, r.detectability_post, r.rpn_post, r.region_post, r.disposition
ORDER BY r.rpn_post DESC;

// 4. Controls credited without complete verification. This must return no rows.
MATCH (r:RiskItem)-[cb:CONTROLLED_BY]->(cm:ControlMeasure)
WHERE cb.verification_status <> 'PASS' AND (cb.credited_occurrence + cb.credited_detectability + cb.credited_severity) > 0
RETURN r.id, cm.id, cb.verification_status;

// 5. Components with no failure mode analysis.
MATCH (c:Component) WHERE NOT (c)-[:HAS_FAILURE_MODE]->() RETURN c.id, c.name;

// 6. Harm centred view: every component that can contribute to one harm.
MATCH (c:Component)-[:HAS_FAILURE_MODE]->(fm:FailureMode)-[:LEADS_TO]->(hs:HazardousSituation)-[:RESULTS_IN]->(h:Harm {id: 'HARM_HYPO_SEVERE'})
RETURN h.name, c.id, c.name, fm.name ORDER BY c.id;

// 7. Regulatory cross reference: clauses of one standard and the requirements that cite them.
MATCH (req:Requirement)-[:COMPLIES_WITH]->(s:StandardClause {designation: 'IEC 62304'})
RETURN s.clause, s.topic, collect(req.id) AS requirements ORDER BY s.clause;

// 8. Risks whose probability was raised by field evidence.
MATCH (r:RiskItem {probability_basis: 'field evidence'})-[sb:SUPPORTED_BY]->(i:Incident)
RETURN r.id, r.engineering_probability, r.probability_pre, r.field_matched_count, collect(i.id) AS sample_reports
