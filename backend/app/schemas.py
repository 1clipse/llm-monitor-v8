from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=20000)
    relay: str | None = Field(default="mock")
    metadata: dict[str, Any] = Field(default_factory=dict)


class RelayConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    type: str = "openai_compatible"
    url: str | None = None
    api_key: str | None = None
    api_key_env: str | None = None
    model: str | None = None


class IngestRequest(BaseModel):
    prompt: str | None = Field(default="", max_length=20000)
    text: str = Field(..., min_length=1, max_length=200000)
    relay: str = Field(default="external", min_length=1, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalysisResult(BaseModel):
    vector: list[float]
    anomaly_label: int
    anomaly_score: float
    cluster: int
    drift_score: float
    model_probabilities: dict[str, float]
    mixed_model: bool
    risk_score: float
    risk_label: str
    reasons: list[str]


class LogResponse(BaseModel):
    id: int | None = None
    time: datetime
    relay: str
    prompt: str
    text: str
    analysis: AnalysisResult


class StatsResponse(BaseModel):
    total: int
    high_risk: int
    medium_risk: int
    low_risk: int
    average_risk_score: float
    latest_drift_score: float
    model_probabilities: dict[str, float]
