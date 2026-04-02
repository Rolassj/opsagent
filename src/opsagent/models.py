"""Modelos Pydantic para structured output de OpsAgent.

DiagnosticOutput define la estructura exacta que Claude debe devolver
cuando genera un diagnostico operativo.
"""

from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    """Una recomendacion accionable para la PyME."""

    prioridad: int = Field(description="Orden de prioridad (1 = mas urgente)")
    accion: str = Field(description="Accion concreta a tomar")
    impacto: str = Field(description="Impacto esperado de implementar esta accion")
    plazo: str = Field(description="Plazo estimado para implementar (ej: '1 semana', '2-3 dias')")


class DiagnosticOutput(BaseModel):
    """Salida estructurada del Recommendations Agent.

    Claude genera estos 3 campos basandose en los KPIs,
    anomalias y tendencias del Analysis Agent.
    """

    diagnosis: str = Field(
        description="Diagnostico completo en lenguaje natural. "
        "Explica que esta pasando en la operacion, por que, "
        "y cuales son los problemas principales. "
        "Usa lenguaje simple para un dueno de PyME."
    )
    recommendations: list[Recommendation] = Field(
        description="Lista de recomendaciones priorizadas y accionables. "
        "Ordenadas de mayor a menor prioridad. Minimo 2, maximo 5."
    )
    executive_summary: str = Field(
        description="Resumen ejecutivo de 2-3 oraciones para el dueno de la PyME. "
        "Sin tecnicismos. Responde: que esta mal y que hacer al respecto."
    )
