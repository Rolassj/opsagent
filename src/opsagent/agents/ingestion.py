"""Ingestion Agent — Nodo 1 del pipeline OpsAgent.

Responsabilidad: Recibir datos crudos y entregarlos limpios y estructurados.

1. Normaliza nombres de columnas a snake_case
2. Limpia datos: elimina filas con >50% nulos, reporta nulos aislados
3. Detecta el dominio industrial ("manufactura", "logistica", "alimentos")
4. Genera reporte de calidad de datos
5. Rechaza datasets con <50% de filas validas

Input del estado: raw_data, file_metadata
Output al estado: cleaned_data, data_quality_report, detected_domain, processing_status
"""

import logging

from opsagent.state import OpsAgentState
from opsagent.tools.data_tools import normalizar_columnas, limpiar_dataframe, detectar_dominio, mapear_columnas

logger = logging.getLogger("opsagent.ingestion")


def ingestion_node(state: OpsAgentState) -> dict:
    """Nodo de ingestion: limpia y clasifica los datos operativos."""
    raw_data = state["raw_data"]

    # Normalizar columnas
    df = normalizar_columnas(raw_data)

    # Mapear columnas con nombres no estandar al schema interno
    cols_before = set(df.columns)
    df = mapear_columnas(df)
    mapped = set(df.columns) - cols_before
    if mapped:
        logger.info("Columnas mapeadas automaticamente: %s", mapped)

    # Limpiar datos
    cleaned_data, quality_report = limpiar_dataframe(df)

    # Verificar calidad minima
    if quality_report["filas_originales"] > 0:
        pct_validas = (quality_report["filas_validas"] / quality_report["filas_originales"]) * 100
    else:
        pct_validas = 0

    if pct_validas < 50:
        return {
            "cleaned_data": None,
            "data_quality_report": quality_report,
            "detected_domain": "desconocido",
            "processing_status": "error",
            "error": f"Calidad de datos insuficiente: solo {pct_validas:.0f}% de filas validas (minimo 50%)",
        }

    # Detectar dominio
    domain = detectar_dominio(list(cleaned_data.columns))

    return {
        "cleaned_data": cleaned_data,
        "data_quality_report": quality_report,
        "detected_domain": domain,
        "processing_status": "analyzing",
    }
