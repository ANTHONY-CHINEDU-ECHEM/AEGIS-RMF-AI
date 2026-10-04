// Aegis RMF AI graph schema for Neo4j 5.
// Every node carries the shared label Entity and one specific label.
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE;
CREATE INDEX risk_region IF NOT EXISTS FOR (n:RiskItem) ON (n.region_post);
CREATE INDEX component_subsystem IF NOT EXISTS FOR (n:Component) ON (n.subsystem);
CREATE INDEX requirement_component IF NOT EXISTS FOR (n:Requirement) ON (n.component_id)
