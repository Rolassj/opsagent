"""Estado compartido del grafo LangGraph de OpsAgent.

OpsAgentState es el TypedDict que fluye por todos los nodos.
Cada agente lee lo que necesita y escribe solo sus outputs.

Flujo del estado:
  Input → [Ingestion Agent] → [Analysis Agent] → [Recommendations Agent] → Output
"""

from typing import TypedDict, Optional, Annotated
from langgraph.graph.message import add_messages
import pandas as pd


class OpsAgentState(TypedDict):
    """Estado compartido que fluye por todos los nodos del grafo.

    Los campos se agrupan por etapa del pipeline. Cada agente
    es responsable de completar sus campos de output.
    """

    # ── INPUT ──────────────────────────────────────────────────────────────
    raw_data: Optional[pd.DataFrame]
    """Datos crudos cargados desde el CSV/Excel del usuario."""

    file_metadata: dict
    """Metadatos del archivo: {"nombre": str, "filas": int, "columnas": list[str]}"""

    # ── INGESTION AGENT OUTPUT ─────────────────────────────────────────────
    cleaned_data: Optional[pd.DataFrame]
    """Datos normalizados y limpios, listos para análisis."""

    data_quality_report: dict
    """Reporte de calidad: {"filas_validas": int, "filas_eliminadas": int, "problemas": list[str]}"""

    detected_domain: str
    """Dominio industrial detectado: "manufactura" | "logistica" | "alimentos" | "desconocido" """

    # ── ANALYSIS AGENT OUTPUT ──────────────────────────────────────────────
    kpis: dict
    """KPIs calculados según el dominio detectado.
    Manufactura: {"oee": float, "tasa_defectos": float, "throughput": float}
    Logística: {"fill_rate": float, "on_time_delivery": float, "rotacion_inventario": float}
    """

    anomalies: list[dict]
    """Lista de anomalías detectadas.
    Cada item: {"campo": str, "severidad": "critica"|"alta"|"media"|"baja", "detalle": str}
    """

    trends: list[dict]
    """Tendencias identificadas en las métricas clave.
    Cada item: {"metrica": str, "direccion": "ascendente"|"descendente"|"estable", "magnitud": float}
    """

    # ── RECOMMENDATIONS AGENT OUTPUT ───────────────────────────────────────
    diagnosis: str
    """Diagnóstico completo en lenguaje natural, generado por Claude."""

    recommendations: list[dict]
    """Recomendaciones priorizadas y accionables.
    Cada item: {"prioridad": int, "accion": str, "impacto": str, "plazo": str}
    """

    executive_summary: str
    """Resumen ejecutivo de 2-3 oraciones para el dueño de la PyME.
    Sin tecnicismos. Responde: ¿qué está mal? ¿qué hacer?
    """

    # ── METADATA ───────────────────────────────────────────────────────────
    messages: Annotated[list, add_messages]
    """Historial de mensajes del grafo (requerido para usar LLM en los nodos)."""

    processing_status: str
    """Estado actual del procesamiento: "ingesting" | "analyzing" | "recommending" | "done" | "error" """

    error: Optional[str]
    """Mensaje de error si algo falla. None si todo está OK."""


def initial_state(raw_data: pd.DataFrame, file_name: str) -> OpsAgentState:
    """Crear estado inicial para una nueva ejecución del grafo.

    Args:
        raw_data: DataFrame cargado desde el archivo del usuario
        file_name: Nombre del archivo original

    Returns:
        Estado inicial con todos los campos opcionales en None/vacío
    """
    return OpsAgentState(
        raw_data=raw_data,
        file_metadata={
            "nombre": file_name,
            "filas": len(raw_data),
            "columnas": list(raw_data.columns),
        },
        cleaned_data=None,
        data_quality_report={},
        detected_domain="",
        kpis={},
        anomalies=[],
        trends=[],
        diagnosis="",
        recommendations=[],
        executive_summary="",
        messages=[],
        processing_status="ingesting",
        error=None,
    )
