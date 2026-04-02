"""Schemas Pydantic para la API REST de OpsAgent."""

from typing import Any, Optional
from pydantic import BaseModel


class RecommendationSchema(BaseModel):
    prioridad: int
    accion: str
    impacto: str
    plazo: str


class DiagnoseResponse(BaseModel):
    id: str
    status: str  # "done" | "error"
    detected_domain: str
    executive_summary: str
    kpis: dict[str, Any]
    anomalies: list[dict[str, Any]]
    trends: list[dict[str, Any]]
    diagnosis: str
    recommendations: list[RecommendationSchema]
    data_quality_report: dict[str, Any]
    processing_time_seconds: float
    error: Optional[str] = None
    filename: str = ""
    created_at: Optional[str] = None
