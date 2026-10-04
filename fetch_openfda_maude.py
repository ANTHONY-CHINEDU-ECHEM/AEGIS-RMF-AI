"""Download real adverse event reports from the openFDA device event API.

The result is written in the JSON lines layout used by the engine, so it can replace the
synthetic corpus by pointing incidents_path in configs/settings.yaml at the new file.

Usage:
    python scripts/fetch_openfda_maude.py "insulin pump" 2000

The first argument is the generic device name to search for and the second is the number of
reports to fetch. openFDA serves at most 1000 records per request and limits anonymous clients
to 240 requests per minute. This script was written against the published API description and
could not be exercised in the offline build environment of this project. The field mapping
itself is covered by tests/test_ingestion.py.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis_rmf.ingestion.openfda import from_openfda, to_native  # noqa: E402

ENDPOINT = "https://api.fda.gov/device/event.json"
PAGE_SIZE = 100
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "incidents" / "openfda_adverse_events.jsonl"


def fetch_page(generic_name: str, skip: int) -> list[dict]:
    query = urllib.parse.urlencode({
        "search": f'device.generic_name:"{generic_name}"', "limit": PAGE_SIZE, "skip": skip,
    })
    with urllib.request.urlopen(f"{ENDPOINT}?{query}", timeout=60) as response:
        return json.load(response).get("results", [])


def main() -> None:
    generic_name = sys.argv[1] if len(sys.argv) > 1 else "insulin pump"
    total = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    written = 0
    with OUTPUT.open("w", encoding="utf8") as handle:
        for skip in range(0, total, PAGE_SIZE):
            results = fetch_page(generic_name, skip)
            if not results:
                break
            for result in results:
                record = from_openfda(result)
                if record is not None:
                    handle.write(json.dumps(to_native(record)) + "\n")
                    written += 1
            time.sleep(0.3)
    print(f"Wrote {written} reports to {OUTPUT}")


if __name__ == "__main__":
    main()
