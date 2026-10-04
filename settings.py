"""Runtime settings loaded from configs/settings.yaml with environment overrides."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

ENV_PREFIX = "AEGIS_"


class Settings(BaseModel):
    home: Path
    device_name: str = "Medical device"
    design_docs_dir: Path
    incidents_path: Path
    evaluation_dir: Path
    output_dir: Path
    risk_policy_path: Path
    harm_catalogue_path: Path
    standards_catalogue_path: Path

    graph_backend: str = "memory"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    qdrant_url: str = ""
    qdrant_path: str = ""
    qdrant_collection: str = "aegis_knowledge"

    embedding_backend: str = "hashing"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 1024
    similarity_threshold: float = 0.30

    llm_provider: str = "none"
    llm_model: str = ""

    chunk_size: int = 320
    chunk_overlap: int = 40
    retrieval_top_k: int = 6
    incident_limit: int = 0


PATH_KEYS = {
    "design_docs_dir", "incidents_path", "evaluation_dir", "output_dir",
    "risk_policy_path", "harm_catalogue_path", "standards_catalogue_path",
}


def project_home() -> Path:
    """Return the project root, taken from AEGIS_HOME or found by walking up from the working directory."""
    explicit = os.environ.get(f"{ENV_PREFIX}HOME")
    if explicit:
        return Path(explicit).resolve()
    here = Path.cwd().resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "configs" / "settings.yaml").exists():
            return candidate
    return here


def load_settings(overrides: dict[str, Any] | None = None) -> Settings:
    """Load settings in priority order: explicit overrides, environment, YAML file."""
    home = project_home()
    config_file = home / "configs" / "settings.yaml"
    values: dict[str, Any] = {}
    if config_file.exists():
        values.update(yaml.safe_load(config_file.read_text(encoding="utf8")) or {})
    for key in Settings.model_fields:
        env_value = os.environ.get(f"{ENV_PREFIX}{key.upper()}")
        if env_value is not None and key != "home":
            values[key] = env_value
    values.update(overrides or {})
    for key in PATH_KEYS:
        path = Path(str(values[key]))
        values[key] = path if path.is_absolute() else home / path
    values["home"] = home
    return Settings(**values)
