"""Request and response models for the API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ScoreRequest(BaseModel):
    severity: int = Field(ge=1, le=5)
    probability: int = Field(ge=1, le=5)
    detectability: int = Field(ge=1, le=5)


class QueryRequest(BaseModel):
    question: str = Field(min_length=3)


class IncidentSearchRequest(BaseModel):
    query: str = Field(min_length=3)
    top_k: int = Field(default=5, ge=1, le=50)


class PipelineRunRequest(BaseModel):
    export: bool = False


class RiskBrief(BaseModel):
    risk_id: str
    title: str
    component_id: str
    harm: str
    rpn_before: int
    region_before: str
    rpn_after: int
    region_after: str
    action_priority: str
    disposition: str
