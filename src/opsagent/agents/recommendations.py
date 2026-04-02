"""Recommendations Agent — Nodo 3 del pipeline OpsAgent.

Responsabilidad: Generar diagnostico y recomendaciones usando Claude.

1. Recibe KPIs, anomalias y tendencias del Analysis Agent
2. Invoca Claude con contexto industrial (Lean, Six Sigma, BPMN)
3. Claude devuelve DiagnosticOutput estructurado via with_structured_output
4. Formatea la salida para el estado del grafo

Input del estado: kpis, anomalies, trends, detected_domain
Output al estado: diagnosis, recommendations, executive_summary, processing_status
"""

import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from opsagent.models import DiagnosticOutput
from opsagent.prompts.system_prompts import build_system_prompt
from opsagent.state import OpsAgentState


def _get_llm() -> ChatAnthropic:
    """Crear instancia de ChatAnthropic configurada para recommendations."""
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        max_tokens=4096,
        temperature=0.3,
    )


def _build_context_message(state: OpsAgentState) -> str:
    """Construir mensaje de contexto con los datos del Analysis Agent.

    Formatea KPIs, anomalias y tendencias en texto legible para Claude.
    """
    parts = []

    # Dominio
    domain = state.get("detected_domain", "desconocido")
    parts.append(f"DOMINIO DETECTADO: {domain}")

    # Metadata del archivo
    metadata = state.get("file_metadata", {})
    if metadata:
        parts.append(f"ARCHIVO: {metadata.get('nombre', 'desconocido')} ({metadata.get('filas', '?')} filas)")

    # Calidad de datos
    quality = state.get("data_quality_report", {})
    if quality:
        parts.append(f"CALIDAD DE DATOS: {quality.get('filas_validas', '?')}/{quality.get('filas_originales', '?')} filas validas")
        problemas = quality.get("problemas", [])
        if problemas:
            parts.append("Problemas encontrados: " + "; ".join(problemas))

    # KPIs que son ratios (0-1) y deben mostrarse como porcentaje
    _RATIO_KPIS = {"oee", "tasa_defectos", "fill_rate", "on_time_delivery"}

    # KPIs
    kpis = state.get("kpis", {})
    if kpis:
        parts.append("\nKPIs CALCULADOS:")
        for k, v in kpis.items():
            if isinstance(v, float) and k in _RATIO_KPIS:
                parts.append(f"  - {k}: {v:.4f} ({v*100:.1f}%)")
            elif isinstance(v, float):
                parts.append(f"  - {k}: {v:.1f}")
            elif isinstance(v, dict):
                parts.append(f"  - {k}:")
                for sub_k, sub_v in v.items():
                    parts.append(f"      {sub_k}: {sub_v}")
            else:
                parts.append(f"  - {k}: {v}")

    # Anomalias
    anomalies = state.get("anomalies", [])
    if anomalies:
        parts.append(f"\nANOMALIAS DETECTADAS ({len(anomalies)}):")
        for a in anomalies:
            parts.append(f"  - [{a.get('severidad', '?').upper()}] {a.get('detalle', 'sin detalle')}")
    else:
        parts.append("\nANOMALIAS: Ninguna detectada")

    # Tendencias
    trends = state.get("trends", [])
    if trends:
        parts.append(f"\nTENDENCIAS ({len(trends)}):")
        for t in trends:
            mag = t.get("magnitud", 0)
            parts.append(f"  - {t.get('metrica', '?')}: {t.get('direccion', '?')} (magnitud: {mag:.1%})")
    else:
        parts.append("\nTENDENCIAS: Ninguna significativa detectada")

    parts.append("\nCon base en estos datos, genera tu diagnostico, recomendaciones priorizadas y resumen ejecutivo.")

    return "\n".join(parts)


def recommendations_node(state: OpsAgentState) -> dict:
    """Nodo de recomendaciones: genera diagnostico con Claude.

    Args:
        state: Estado actual con kpis, anomalies, trends, detected_domain

    Returns:
        Diccionario con los campos a actualizar en el estado:
        - diagnosis: diagnostico completo en lenguaje natural
        - recommendations: lista de recomendaciones priorizadas
        - executive_summary: resumen ejecutivo para dueno de PyME
        - processing_status: "done"
    """
    # Verificar que hay datos para analizar
    kpis = state.get("kpis", {})
    anomalies = state.get("anomalies", [])
    if not kpis and not anomalies:
        return {
            "diagnosis": "",
            "recommendations": [],
            "executive_summary": "",
            "processing_status": "error",
            "error": "No hay KPIs ni anomalias para generar recomendaciones",
        }

    try:
        # Construir prompt y contexto
        domain = state.get("detected_domain", "desconocido")
        system_prompt = build_system_prompt(domain)
        context_message = _build_context_message(state)

        # Invocar Claude con structured output
        llm = _get_llm()
        structured_llm = llm.with_structured_output(DiagnosticOutput)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_message),
        ]

        result: DiagnosticOutput = structured_llm.invoke(messages)

        # Convertir recommendations de Pydantic a dicts para el estado
        recs = [r.model_dump() for r in result.recommendations]

        return {
            "diagnosis": result.diagnosis,
            "recommendations": recs,
            "executive_summary": result.executive_summary,
            "processing_status": "done",
        }

    except Exception as e:
        return {
            "diagnosis": "",
            "recommendations": [],
            "executive_summary": "",
            "processing_status": "error",
            "error": f"Error al generar recomendaciones: {str(e)}",
        }
