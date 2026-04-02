"""Analysis Agent — Nodo 2 del pipeline OpsAgent.

Responsabilidad: Calcular KPIs especificos del dominio y detectar anomalias.

1. Calcula KPIs segun el dominio detectado por el Ingestion Agent
2. Detecta anomalias estadisticas en cada columna numerica (regla 2-3 sigma)
3. Identifica tendencias temporales (primera mitad vs segunda mitad)
4. Todo es deterministico — no usa LLM

Input del estado: cleaned_data, detected_domain
Output al estado: kpis, anomalies, trends, processing_status
"""

import logging

import pandas as pd

from opsagent.state import OpsAgentState

logger = logging.getLogger("opsagent.analysis")
from opsagent.tools.analysis_tools import (
    calcular_kpis_manufactura,
    calcular_kpis_logistica,
    detectar_anomalias_estadisticas,
)


def analysis_node(state: OpsAgentState) -> dict:
    """Nodo de analisis: calcula KPIs y detecta anomalias."""
    cleaned_data = state["cleaned_data"]
    domain = state["detected_domain"]

    if cleaned_data is None or len(cleaned_data) == 0:
        logger.warning("No hay datos limpios para analizar")
        return {
            "kpis": {},
            "anomalies": [],
            "trends": [],
            "processing_status": "error",
            "error": "No hay datos limpios para analizar",
        }

    logger.info("Analizando %d filas, dominio=%s", len(cleaned_data), domain)

    # Calcular KPIs segun dominio
    if domain == "manufactura":
        kpis = calcular_kpis_manufactura(cleaned_data)
    elif domain == "logistica":
        kpis = calcular_kpis_logistica(cleaned_data)
    else:
        logger.info("Dominio '%s' no tiene KPIs especificos", domain)
        kpis = {}

    # Detectar anomalias en cada columna numerica
    all_anomalies: list[dict] = []
    for col in cleaned_data.select_dtypes(include="number").columns:
        serie = cleaned_data[col].dropna().tolist()
        anomalias = detectar_anomalias_estadisticas(serie, col)
        all_anomalies.extend(anomalias)

    # Calcular tendencias simples
    trends = _calcular_tendencias(cleaned_data)

    return {
        "kpis": kpis,
        "anomalies": all_anomalies,
        "trends": trends,
        "processing_status": "recommending",
    }


def _calcular_tendencias(df: pd.DataFrame) -> list[dict]:
    """Comparar promedio de primera mitad vs segunda mitad para cada metrica numerica.

    Si el cambio es > 10%, registrar como tendencia.
    """
    trends: list[dict] = []

    # Buscar columna de fecha para ordenar
    fecha_col = None
    for col in df.columns:
        if "fecha" in col.lower():
            fecha_col = col
            break

    if fecha_col is not None and pd.api.types.is_datetime64_any_dtype(df[fecha_col]):
        df = df.sort_values(fecha_col)

    mitad = len(df) // 2
    if mitad < 2:
        return trends

    primera = df.iloc[:mitad]
    segunda = df.iloc[mitad:]

    for col in df.select_dtypes(include="number").columns:
        prom_1 = primera[col].dropna().mean()
        prom_2 = segunda[col].dropna().mean()

        if pd.isna(prom_1) or pd.isna(prom_2) or prom_1 == 0:
            continue

        cambio = (prom_2 - prom_1) / abs(prom_1)

        if abs(cambio) > 0.10:
            direccion = "ascendente" if cambio > 0 else "descendente"
            trends.append({
                "metrica": col,
                "direccion": direccion,
                "magnitud": round(abs(cambio), 3),
            })

    return trends
