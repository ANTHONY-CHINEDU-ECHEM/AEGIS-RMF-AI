"""Hybrid retrieval augmented question answering.

Evidence comes from two places. Vector search over Qdrant finds relevant design text, standard
clauses, scored risk records and incident reports. The knowledge graph supplies exact trace
facts for any identifier named in the question. With a language model configured the evidence
is synthesised into an answer. Without one the engine returns the evidence itself.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from aegis_rmf.extraction.llm import TextLLM
from aegis_rmf.graph.base import BACKWARD, FORWARD, GraphStore
from aegis_rmf.retrieval.knowledge_base import DESIGN, INCIDENT, RISK, STANDARD, Hit, KnowledgeBase

IDENTIFIER = re.compile(r"\b(?:RISK|CMP|REQ|RCM|VER|HARM|FM|HS)_[A-Z0-9_]+\b")
FIELD_WORDS = re.compile(r"\b(incident|incidents|complaint|complaints|field|adverse|reports?|reported)\b", re.IGNORECASE)
TRACE_LABELS = ["Component", "FailureMode", "RiskItem", "Harm", "ControlMeasure", "Requirement", "Verification"]

PROMPT = """You are a regulatory affairs assistant for a medical device manufacturer.
Answer the question using only the evidence below. Quote identifiers exactly.
Cite the reference of each piece of evidence you rely on in square brackets.
If the evidence does not contain the answer, say so.

Graph facts:
{facts}

Retrieved evidence:
{evidence}

Question: {question}
Answer:"""


class Answer(BaseModel):
    question: str
    answer: str
    mode: str
    graph_facts: list[str]
    contexts: list[Hit]


def describe_node(store: GraphStore, node_id: str) -> str | None:
    """One sentence of exact trace facts for a graph node."""
    node = store.get_node(node_id)
    if node is None:
        return None
    parts = [f"{node_id} is a {node['label']}"]
    if node.get("name") and node["name"] != node_id:
        parts[0] += f" named {node['name']}"
    for key, text in (("text", "Text"), ("result", "Result"), ("control_type", "Control type"), ("disposition", "Disposition")):
        if node.get(key):
            parts.append(f"{text}: {str(node[key]).replace('_', ' ')}")
    if node["label"] == "RiskItem":
        parts.append(
            f"Title: {node['title']}. Before control severity {node['severity_pre']}, probability {node['probability_pre']}, "
            f"detectability {node['detectability_pre']}, RPN {node['rpn_pre']} ({node['region_pre']}). After control severity "
            f"{node['severity_post']}, probability {node['probability_post']}, detectability {node['detectability_post']}, "
            f"RPN {node['rpn_post']} ({node['region_post']}). Probability basis: {node['probability_basis']} with "
            f"{node['field_matched_count']} similar incident reports"
        )
        for control, _, edge in store.neighbors(node_id, "CONTROLLED_BY", FORWARD):
            note = f" ({edge['notes']})" if edge.get("notes") else ""
            parts.append(f"Control {control['id']} {control['name']} has verification status {edge['verification_status']}{note}")
    for direction, phrase in ((BACKWARD, "Traces back to"), (FORWARD, "Traces forward to")):
        trace = store.trace(node_id, direction)
        found = [f"{label} {', '.join(trace[label][:8])}" for label in TRACE_LABELS if trace.get(label)]
        if found:
            parts.append(f"{phrase} {'; '.join(found)}")
    return ". ".join(parts) + "."


class RagEngine:
    def __init__(self, knowledge_base: KnowledgeBase, store: GraphStore, llm: TextLLM | None = None, top_k: int = 6) -> None:
        self.kb, self.store, self.llm, self.top_k = knowledge_base, store, llm, top_k

    def retrieve(self, question: str) -> tuple[list[Hit], list[str]]:
        facts = []
        for node_id in dict.fromkeys(IDENTIFIER.findall(question)):
            fact = describe_node(self.store, node_id)
            if fact:
                facts.append(fact)
        hits = self.kb.search(question, [DESIGN, STANDARD, RISK], self.top_k)
        if FIELD_WORDS.search(question):
            hits += self.kb.search(question, [INCIDENT], 3)
        return hits, facts

    def answer(self, question: str) -> Answer:
        hits, facts = self.retrieve(question)
        if self.llm is not None:
            evidence = "\n\n".join(f"[{hit.ref_id}] {hit.text}" for hit in hits)
            text = self.llm.complete(PROMPT.format(facts="\n".join(facts) or "none", evidence=evidence, question=question))
            mode = "llm"
        else:
            lines = list(facts)
            lines += [f"[{hit.ref_id}] {hit.text}" for hit in hits[:2]]
            text = "\n".join(lines) if lines else "No evidence was found for this question."
            mode = "extractive"
        return Answer(question=question, answer=text.strip(), mode=mode, graph_facts=facts, contexts=hits)
