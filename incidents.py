"""Load historical incident reports from JSON lines files."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


class IncidentRecord(BaseModel):
    report_number: str
    date_received: str = ""
    event_type: str = "Malfunction"
    product_problem_code: str = ""
    product_problem: str = ""
    patient_problem: str = ""
    narrative: str
    software_version: str = ""
    device_age_months: int = 0
    source: str = "synthetic"

    def embedding_text(self) -> str:
        return f"{self.product_problem}. {self.narrative}"


def from_native(record: dict) -> IncidentRecord:
    device = record.get("device", {})
    return IncidentRecord(
        report_number=record["report_number"],
        date_received=record.get("date_received", ""),
        event_type=record.get("event_type", "Malfunction"),
        product_problem_code=record.get("product_problem_code", ""),
        product_problem=record.get("product_problem", ""),
        patient_problem=record.get("patient_problem", ""),
        narrative=record["narrative"],
        software_version=device.get("software_version", ""),
        device_age_months=int(device.get("device_age_months", 0)),
        source=record.get("source", "synthetic"),
    )


def load_incidents(path: Path, limit: int = 0) -> list[IncidentRecord]:
    """Load incident reports. A positive limit keeps only the first records, which is useful in tests."""
    records: list[IncidentRecord] = []
    with Path(path).open(encoding="utf8") as handle:
        for line in handle:
            if line.strip():
                records.append(from_native(json.loads(line)))
                if limit and len(records) >= limit:
                    break
    return records
