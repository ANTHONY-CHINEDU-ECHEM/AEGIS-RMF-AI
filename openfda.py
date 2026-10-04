"""Map openFDA device adverse event results onto the incident schema.

This lets real MAUDE reports replace the synthetic corpus. See scripts/fetch_openfda_maude.py.
"""
from __future__ import annotations

from aegis_rmf.ingestion.incidents import IncidentRecord


def from_openfda(result: dict) -> IncidentRecord | None:
    """Convert one openFDA result. Returns None when the report carries no narrative text."""
    narrative = " ".join(
        entry.get("text", "").strip() for entry in result.get("mdr_text", []) if entry.get("text")
    ).strip()
    if not narrative:
        return None
    devices = result.get("device") or [{}]
    patients = result.get("patient") or [{}]
    patient_problems = patients[0].get("patient_problems") or []
    return IncidentRecord(
        report_number=str(result.get("report_number", "")).replace("-", "_"),
        date_received=str(result.get("date_received", "")),
        event_type=str(result.get("event_type", "Malfunction")),
        product_problem="; ".join(result.get("product_problems") or []),
        patient_problem="; ".join(patient_problems),
        narrative=narrative,
        software_version=str(devices[0].get("model_number", "")),
        source="openfda",
    )


def to_native(record: IncidentRecord) -> dict:
    """Serialise to the JSON lines layout read by load_incidents."""
    return {
        "report_number": record.report_number,
        "date_received": record.date_received,
        "event_type": record.event_type,
        "device": {"software_version": record.software_version, "device_age_months": record.device_age_months},
        "product_problem_code": record.product_problem_code,
        "product_problem": record.product_problem,
        "patient_problem": record.patient_problem,
        "narrative": record.narrative,
        "source": record.source,
    }
