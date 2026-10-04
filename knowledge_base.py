"""Qdrant backed knowledge base built with LlamaIndex.

One collection holds four kinds of evidence, separated by the source_type payload field:
design document chunks, standard clause summaries, incident reports and scored risk records.
"""
from __future__ import annotations

import uuid
import warnings
from collections.abc import Iterable

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores import FilterOperator, MetadataFilter, MetadataFilters
from llama_index.vector_stores.qdrant import QdrantVectorStore
from pydantic import BaseModel
from qdrant_client import QdrantClient, models

from aegis_rmf.domain import RiskRecord
from aegis_rmf.ingestion.design_docs import DocUnit
from aegis_rmf.ingestion.incidents import IncidentRecord
from aegis_rmf.ingestion.standards import StandardClause
from aegis_rmf.retrieval.embeddings import build_embedding
from aegis_rmf.settings import Settings

warnings.filterwarnings("ignore", message="Payload indexes have no effect in the local Qdrant")

NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "aegis_rmf")
DESIGN, STANDARD, INCIDENT, RISK = "design_doc", "standard", "incident", "risk_record"
MATCH_LIMIT = 20000


class Hit(BaseModel):
    ref_id: str
    source_type: str
    score: float
    text: str
    metadata: dict


def build_client(settings: Settings) -> QdrantClient:
    if settings.qdrant_url:
        return QdrantClient(url=settings.qdrant_url)
    if settings.qdrant_path:
        return QdrantClient(path=settings.qdrant_path)
    return QdrantClient(location=":memory:")


class KnowledgeBase:
    def __init__(self, settings: Settings, embedding: BaseEmbedding | None = None, client: QdrantClient | None = None) -> None:
        self.settings = settings
        self.embedding = embedding or build_embedding(settings)
        self.client = client or build_client(settings)
        self.collection = settings.qdrant_collection
        self.splitter = SentenceSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
        self.counts: dict[str, int] = {}
        self._index: VectorStoreIndex | None = None

    def reset(self) -> None:
        """Drop the collection so that a pipeline run always starts from a clean index."""
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self._index, self.counts = None, {}

    def _add(self, source_type: str, nodes: list[TextNode]) -> int:
        if not nodes:
            return 0
        if self._index is None:
            store = QdrantVectorStore(client=self.client, collection_name=self.collection)
            self._index = VectorStoreIndex(
                nodes=nodes, storage_context=StorageContext.from_defaults(vector_store=store),
                embed_model=self.embedding,
            )
        else:
            self._index.insert_nodes(nodes)
        self.counts[source_type] = self.counts.get(source_type, 0) + len(nodes)
        return len(nodes)

    @staticmethod
    def _node(source_type: str, ref_id: str, part: int, text: str, metadata: dict) -> TextNode:
        payload = {"source_type": source_type, "ref_id": ref_id, **metadata}
        return TextNode(
            text=text, id_=str(uuid.uuid5(NAMESPACE, f"{source_type}|{ref_id}|{part}")), metadata=payload,
            excluded_embed_metadata_keys=list(payload), excluded_llm_metadata_keys=list(payload),
        )

    def index_design_units(self, units: Iterable[DocUnit]) -> int:
        nodes = []
        for unit in units:
            for part, chunk in enumerate(self.splitter.split_text(unit.text)):
                text = chunk if chunk.startswith(unit.heading) else f"{unit.heading}\n{chunk}"
                nodes.append(self._node(DESIGN, unit.ref_id, part, f"{unit.doc_title}. {text}", {
                    "doc_id": unit.doc_id, "section": unit.section, "heading": unit.heading,
                    "component_id": unit.component_id, "dfc_id": unit.dfc_id,
                }))
        return self._add(DESIGN, nodes)

    def index_standards(self, clauses: Iterable[StandardClause]) -> int:
        nodes = [self._node(STANDARD, clause.key, 0, clause.text(), {"designation": clause.designation, "clause": clause.clause})
                 for clause in clauses]
        return self._add(STANDARD, nodes)

    def index_incidents(self, incidents: Iterable[IncidentRecord]) -> int:
        nodes = [self._node(INCIDENT, record.report_number, 0, record.embedding_text(), {
            "event_type": record.event_type, "product_problem": record.product_problem,
            "product_problem_code": record.product_problem_code, "date_received": record.date_received,
        }) for record in incidents]
        return self._add(INCIDENT, nodes)

    def index_risk_records(self, records: Iterable[RiskRecord]) -> int:
        nodes = [self._node(RISK, record.risk_id, 0, record.summary_text(), {
            "component_id": record.component_id, "dfc_id": record.dfc_id,
        }) for record in records]
        return self._add(RISK, nodes)

    def search(self, query: str, source_types: list[str], top_k: int | None = None) -> list[Hit]:
        """Return the most similar items of the given source types."""
        if self._index is None:
            return []
        filters = MetadataFilters(filters=[MetadataFilter(key="source_type", value=source_types, operator=FilterOperator.IN)])
        retriever = self._index.as_retriever(similarity_top_k=top_k or self.settings.retrieval_top_k, filters=filters)
        return [
            Hit(ref_id=item.node.metadata["ref_id"], source_type=item.node.metadata["source_type"],
                score=float(item.score or 0.0), text=item.node.get_content(), metadata=dict(item.node.metadata))
            for item in retriever.retrieve(query)
        ]

    def matching_incidents(self, query: str, threshold: float | None = None) -> list[dict]:
        """Return the payloads of all incident reports whose similarity to the query meets the threshold."""
        if not self.counts.get(INCIDENT):
            return []
        response = self.client.query_points(
            self.collection,
            query=self.embedding.get_query_embedding(query),
            query_filter=models.Filter(must=[models.FieldCondition(key="source_type", match=models.MatchValue(value=INCIDENT))]),
            score_threshold=self.settings.similarity_threshold if threshold is None else threshold,
            limit=MATCH_LIMIT,
            with_payload=["ref_id", "event_type", "product_problem", "product_problem_code"],
        )
        return [{"score": float(point.score), **(point.payload or {})} for point in response.points]
