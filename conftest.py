"""Shared fixtures. The full pipeline is built once per test session in offline mode."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("AEGIS_HOME", str(ROOT))

from aegis_rmf.pipeline import PipelineResult, run_pipeline  # noqa: E402
from aegis_rmf.risk import load_harm_catalogue, load_policy  # noqa: E402
from aegis_rmf.settings import load_settings  # noqa: E402

OFFLINE = {"graph_backend": "memory", "embedding_backend": "hashing", "llm_provider": "none", "qdrant_url": "", "qdrant_path": ""}


@pytest.fixture(scope="session")
def settings():
    return load_settings(OFFLINE)


@pytest.fixture(scope="session")
def policy(settings):
    return load_policy(settings.risk_policy_path)


@pytest.fixture(scope="session")
def harms(settings):
    return load_harm_catalogue(settings.harm_catalogue_path)


@pytest.fixture(scope="session")
def result(settings) -> PipelineResult:
    return run_pipeline(settings)


@pytest.fixture(scope="session")
def records(result):
    return {record.risk_id: record for record in result.records}
