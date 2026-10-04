"""Traceability matrix, standards coverage and gap analysis built from the knowledge graph."""
from aegis_rmf.traceability.gaps import Gap, find_gaps
from aegis_rmf.traceability.matrix import (
    ClauseCoverage,
    TraceRow,
    build_matrix,
    standards_coverage,
    verify_bidirectional,
)

__all__ = [
    "ClauseCoverage", "Gap", "TraceRow", "build_matrix", "find_gaps", "standards_coverage", "verify_bidirectional",
]
