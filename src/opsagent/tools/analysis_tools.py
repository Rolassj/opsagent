"""Herramientas de calculo de KPIs industriales.

Funciones para calcular metricas operativas. Las decoradas con @tool
seran usadas por el Recommendations Agent via bind_tools (Semana 3).
Las funciones sin @tool son helpers internos del Analysis Agent.

Formulas basadas en estandares industriales:
- OEE: ISO 22400-2
- Tasa de defectos: Six Sigma DPMO
- Fill Rate: APICS standards
"""

import statistics

import pandas as pd
from langchain_core.tools import tool


# ── TOOLS (usadas por Claude en Semana 3 via bind_tools) ──────────────────────


@tool
def calcular_oee(disponibilidad: float, rendimiento: float, calidad: float) -> float:
    """Calcular OEE (Overall Equipment Effectiveness).

    OEE = Disponibilidad x Rendimiento x Calidad
    Benchmark industria: >85% clase mundial, >65% aceptable

    Args:
        disponibilidad: Tiempo productivo / Tiempo planificado (0-1)
        rendimiento: Produccion real / Produccion teorica (0-1)
        calidad: Unidades buenas / Total producidas (0-1)

    Returns:
        OEE como decimal (ej: 0.72 = 72%)
    """
    d = max(0.0, min(1.0, disponibilidad))
    r = max(0.0, min(1.0, rendimiento))
    c = max(0.0, min(1.0, calidad))
    return d * r * c


@tool
def calcular_tasa_defectos(unidades_defectuosas: int, total_producido: int) -> float:
    """Calcular tasa de defectos como porcentaje.

    Args:
        unidades_defectuosas: Cantidad de unidades con defectos
        total_producido: Total de unidades producidas

    Returns:
        Tasa de defectos como decimal (ej: 0.034 = 3.4%)
    """
    if total_producido <= 0:
        return 0.0
    return unidades_defectuosas / total_producido


@tool
def detectar_cuello_de_botella(throughputs: dict[str, float]) -> str:
    """Identificar el cuello de botella en una linea de produccion.

    El cuello de botella es la estacion con menor throughput.

    Args:
        throughputs: Diccionario {"nombre_estacion": throughput_por_hora}

    Returns:
        Nombre de la estacion que es cuello de botella con detalle
    """
    if not throughputs:
        return "No se proporcionaron datos de estaciones."
    cuello = min(throughputs, key=throughputs.get)
    valor = throughputs[cuello]
    return f"{cuello} ({valor} u/h) -- limita la linea"


@tool
def calcular_fill_rate(pedidos_completos: int, total_pedidos: int) -> float:
    """Calcular fill rate (tasa de cumplimiento de pedidos).

    Args:
        pedidos_completos: Pedidos entregados completos y a tiempo
        total_pedidos: Total de pedidos del periodo

    Returns:
        Fill rate como decimal (ej: 0.95 = 95%)
    """
    if total_pedidos <= 0:
        return 0.0
    return pedidos_completos / total_pedidos


# ── FUNCIONES INTERNAS (usadas por analysis_node directamente) ────────────────


def detectar_anomalias_estadisticas(serie: list[float], campo: str) -> list[dict]:
    """Detectar anomalias usando regla de 2-3 desviaciones estandar.

    Returns:
        Lista de anomalias: {"campo", "indice", "valor", "severidad", "detalle"}
    """
    if len(serie) < 3:
        return []

    media = statistics.mean(serie)
    std = statistics.stdev(serie)

    if std == 0:
        return []

    anomalias = []
    for i, valor in enumerate(serie):
        desviaciones = abs(valor - media) / std

        if desviaciones > 3:
            anomalias.append({
                "campo": campo,
                "indice": i,
                "valor": valor,
                "severidad": "critica",
                "detalle": f"{campo}={valor:.1f} esta a {desviaciones:.1f} std de la media ({media:.1f})",
            })
        elif desviaciones > 2:
            anomalias.append({
                "campo": campo,
                "indice": i,
                "valor": valor,
                "severidad": "alta",
                "detalle": f"{campo}={valor:.1f} esta a {desviaciones:.1f} std de la media ({media:.1f})",
            })

    return anomalias


def calcular_kpis_manufactura(df: pd.DataFrame) -> dict:
    """Calcular KPIs agregados para datos de manufactura.

    Espera columnas: produccion_real, capacidad_teorica, defectos,
                     tiempo_parada_min, horas_planificadas

    Robusto ante datos faltantes: calcula lo que puede con las columnas disponibles.
    """
    kpis: dict = {}

    # Asegurar que las columnas numericas sean realmente numericas
    numeric_cols = ["produccion_real", "capacidad_teorica", "defectos",
                    "tiempo_parada_min", "horas_planificadas"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # OEE promedio
    oee_cols = ["produccion_real", "capacidad_teorica", "defectos",
                "tiempo_parada_min", "horas_planificadas"]
    if all(c in df.columns for c in oee_cols):
        filas_oee = df.dropna(subset=oee_cols)

        if len(filas_oee) > 0:
            horas_plan = filas_oee["horas_planificadas"] * 60  # a minutos
            # Evitar division por cero
            horas_plan = horas_plan.replace(0, float("nan"))
            cap = filas_oee["capacidad_teorica"].replace(0, float("nan"))
            prod = filas_oee["produccion_real"].replace(0, float("nan"))

            disponibilidad = (horas_plan - filas_oee["tiempo_parada_min"]) / horas_plan
            rendimiento = filas_oee["produccion_real"] / cap
            calidad = (filas_oee["produccion_real"] - filas_oee["defectos"]) / prod

            # Clampear a 0-1
            disponibilidad = disponibilidad.clip(0, 1)
            rendimiento = rendimiento.clip(0, 1)
            calidad = calidad.clip(0, 1)

            oee_por_fila = disponibilidad * rendimiento * calidad
            oee_mean = oee_por_fila.dropna().mean()
            if not pd.isna(oee_mean):
                kpis["oee"] = round(float(oee_mean), 4)

    # Tasa de defectos global
    if "defectos" in df.columns and "produccion_real" in df.columns:
        total_defectos = df["defectos"].dropna().sum()
        total_producido = df["produccion_real"].dropna().sum()
        if total_producido > 0:
            kpis["tasa_defectos"] = round(float(total_defectos / total_producido), 4)

    # Throughput promedio por linea
    if "produccion_real" in df.columns and "linea" in df.columns:
        valid = df.dropna(subset=["produccion_real"])
        if len(valid) > 0:
            throughput = valid.groupby("linea")["produccion_real"].mean()
            kpis["throughput_por_linea"] = {k: round(float(v), 1) for k, v in throughput.items()}
            kpis["throughput_promedio"] = round(float(valid["produccion_real"].mean()), 1)

    return kpis


def calcular_kpis_logistica(df: pd.DataFrame) -> dict:
    """Calcular KPIs agregados para datos de logistica.

    Espera columnas: items_pedidos, items_entregados,
                     fecha_entrega_prometida, fecha_entrega_real

    Robusto ante datos faltantes: calcula lo que puede con las columnas disponibles.
    """
    kpis: dict = {}

    # Asegurar tipos numericos
    for col in ["items_pedidos", "items_entregados"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Fill rate global
    if "items_pedidos" in df.columns and "items_entregados" in df.columns:
        total_pedidos = df["items_pedidos"].dropna().sum()
        total_entregados = df["items_entregados"].dropna().sum()
        if total_pedidos > 0:
            kpis["fill_rate"] = round(float(total_entregados / total_pedidos), 4)

    # On-time delivery
    if "fecha_entrega_prometida" in df.columns and "fecha_entrega_real" in df.columns:
        prometida = pd.to_datetime(df["fecha_entrega_prometida"], errors="coerce")
        real = pd.to_datetime(df["fecha_entrega_real"], errors="coerce")
        valid = prometida.notna() & real.notna()
        if valid.sum() > 0:
            a_tiempo = (real[valid] <= prometida[valid]).sum()
            kpis["on_time_delivery"] = round(float(a_tiempo / valid.sum()), 4)

    return kpis
