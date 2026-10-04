"""Parse design documents into addressable units, components, requirements and verification records.

Every unit keeps its document identifier, section number and line number so that each statement
in the risk management file can cite the exact place in the design history it came from.
"""
from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

from aegis_rmf.domain import Component, Requirement, SourceRef, VerificationRecord, VerificationStatus

HEADING = re.compile(r"^(#{2,4}) (.+)$")
NUMBERED = re.compile(r"^(\d+(?:\.\d+)*) (.+)$")
COMPONENT_TAG = re.compile(r"\((CMP_\w+)\)$")
DFC_HEADING = re.compile(r"^(DFC_\w+) (.+)$")
COMPONENT_LINE = re.compile(
    r"^\* \*\*(CMP_\w+)\*\* (.+?)\. Subsystem: (.+?)\. Specified in: (\w+) section ([\d.]+)\. "
    r"Software safety class: (.+?)\.$"
)
REQUIREMENT_LINE = re.compile(r"^\* \*\*(REQ_\w+)\*\* (.+?)((?: \[[^\]]+\])*)$")
VERIFIED_TAG = re.compile(r"\[Verified by: (VER_\w+)\]")
STANDARDS_TAG = re.compile(r"\[Standards: ([^\]]+)\]")
VERIFICATION_LINE = re.compile(
    r"^\* \*\*(VER_\w+)\*\* Verifies (REQ_\w+)\. Method: (.+?)\. Result: (\w+)\. Report: (\w+)\.$"
)
CLAUSE_CITATION = re.compile(r"((?:ISO|IEC) \d+(?: \d+)*) cl (\d+(?:\.\d+)*)")


class DocUnit(BaseModel):
    """A heading and the text beneath it, up to the next heading."""

    doc_id: str
    doc_title: str
    section: str
    heading: str
    level: int
    line: int
    text: str
    component_id: str = ""
    dfc_id: str = ""

    @property
    def source(self) -> SourceRef:
        return SourceRef(doc_id=self.doc_id, section=self.section, anchor=self.dfc_id, line=self.line)

    @property
    def ref_id(self) -> str:
        return self.source.ref_id

    def citations(self) -> list[str]:
        """Standard clauses cited in this unit, as catalogue keys such as ISO 14971 cl 7.1."""
        return sorted({f"{designation} cl {clause}" for designation, clause in CLAUSE_CITATION.findall(self.text)})


class DocumentMeta(BaseModel):
    doc_id: str
    title: str
    revision: str
    path: str


class DesignCorpus(BaseModel):
    documents: dict[str, DocumentMeta] = Field(default_factory=dict)
    units: list[DocUnit] = Field(default_factory=list)
    components: dict[str, Component] = Field(default_factory=dict)
    requirements: dict[str, Requirement] = Field(default_factory=dict)
    verifications: dict[str, VerificationRecord] = Field(default_factory=dict)

    def unit(self, ref_id: str) -> DocUnit | None:
        return next((unit for unit in self.units if unit.ref_id == ref_id), None)


def parse_clause_list(text: str) -> list[str]:
    return [f"{d} cl {c}" for d, c in CLAUSE_CITATION.findall(text)]


def _parse_document(path: Path) -> tuple[DocumentMeta, list[DocUnit]]:
    lines = path.read_text(encoding="utf8").splitlines()
    title = next((line[2:].strip() for line in lines if line.startswith("# ")), path.stem)
    doc_id = next((line.split(":", 1)[1].strip() for line in lines if line.startswith("* Document ID:")), path.stem)
    revision = next((line.split(":", 1)[1].strip() for line in lines if line.startswith("* Revision:")), "")
    units: list[DocUnit] = []
    current = {"section": "0", "heading": title, "level": 1, "line": 1, "component_id": "", "dfc_id": ""}
    buffer: list[str] = []
    section, component_id = "0", ""

    def flush() -> None:
        text = "\n".join(buffer).strip()
        if text:
            units.append(DocUnit(doc_id=doc_id, doc_title=title, text=text, **current))

    for number, line in enumerate(lines, start=1):
        match = HEADING.match(line)
        if not match:
            buffer.append(line)
            continue
        flush()
        buffer = []
        level, heading = len(match.group(1)), match.group(2).strip()
        dfc_id = ""
        if level == 4:
            dfc = DFC_HEADING.match(heading)
            dfc_id = dfc.group(1) if dfc else ""
        else:
            numbered = NUMBERED.match(heading)
            section = numbered.group(1) if numbered else section
            if level == 2:
                component_id = ""
            tag = COMPONENT_TAG.search(heading)
            if tag:
                component_id = tag.group(1)
        current = {"section": section, "heading": heading, "level": level, "line": number,
                   "component_id": component_id, "dfc_id": dfc_id}
        buffer.append(heading)
    flush()
    return DocumentMeta(doc_id=doc_id, title=title, revision=revision, path=path.name), units


def load_design_corpus(directory: Path) -> DesignCorpus:
    """Read every markdown file in the directory and build the structured corpus."""
    corpus = DesignCorpus()
    for path in sorted(Path(directory).glob("*.md")):
        meta, units = _parse_document(path)
        corpus.documents[meta.doc_id] = meta
        corpus.units.extend(units)
        for unit in units:
            for offset, line in enumerate(unit.text.splitlines()):
                component = COMPONENT_LINE.match(line)
                if component:
                    cid, name, subsystem, doc, section, sw_class = component.groups()
                    corpus.components[cid] = Component(
                        id=cid, name=name, subsystem=subsystem, doc_id=doc, section=section,
                        software_class="" if sw_class == "not applicable" else sw_class,
                    )
                    continue
                requirement = REQUIREMENT_LINE.match(line)
                if requirement:
                    rid, text, tags = requirement.groups()
                    verified = VERIFIED_TAG.search(tags)
                    standards = STANDARDS_TAG.search(tags)
                    corpus.requirements[rid] = Requirement(
                        id=rid, text=text.strip(), component_id=unit.component_id,
                        source=SourceRef(doc_id=unit.doc_id, section=unit.section, anchor=rid, line=unit.line + offset),
                        verification_id=verified.group(1) if verified else "",
                        standards=parse_clause_list(standards.group(1)) if standards else [],
                    )
                    continue
                verification = VERIFICATION_LINE.match(line)
                if verification:
                    vid, rid, method, result, report = verification.groups()
                    corpus.verifications[vid] = VerificationRecord(
                        id=vid, requirement_id=rid, method=method,
                        result=VerificationStatus(result), report=report,
                    )
    return corpus
