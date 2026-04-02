"""Frontend Streamlit de OpsAgent.

Interfaz para diagnostico operativo: el usuario sube un CSV/Excel
y obtiene KPIs, anomalias, diagnostico y recomendaciones.

Requiere que la API FastAPI este corriendo (uvicorn opsagent.api.main:app).

Para correr (desde salidas/opsagent/):
    streamlit run src/opsagent/app.py
"""

import os
import time

import httpx
import pandas as pd
import streamlit as st

from opsagent.auth.login import login_required, is_logged_in, show_login_page, show_user_sidebar, get_access_token

API_BASE_URL = os.environ.get("OPSAGENT_API_URL", "http://localhost:8000")

# ── Page config ───────────────────────────────────────────────────────────

st.set_page_config(
    page_title="OpsAgent - Diagnostico Operativo",
    page_icon="🏭",
    layout="wide",
)

# ── Auth ──────────────────────────────────────────────────────────────────

if login_required() and not is_logged_in():
    show_login_page()
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🏭 OpsAgent")
    st.caption("Diagnostico operativo con IA para PyMEs industriales")

    st.divider()

    st.markdown("### Como funciona")
    st.markdown(
        "1. **Subi** tu archivo CSV o Excel\n"
        "2. **Revisa** la vista previa de datos\n"
        "3. **Hace clic** en Analizar\n"
        "4. **Recibe** diagnostico y recomendaciones"
    )

    st.divider()

    st.markdown("### Dominios soportados")
    st.markdown(
        "- **Manufactura** — OEE, defectos, paradas\n"
        "- **Logistica** — Fill rate, entregas a tiempo\n"
        "- **Alimentos** — Merma, BPM, temperatura"
    )

    if is_logged_in():
        st.divider()
        show_user_sidebar()

    st.divider()

    st.markdown(
        "<div style='text-align:center; color:gray; font-size:0.8em'>"
        "OpsAgent v0.2.0<br>Semana 6"
        "</div>",
        unsafe_allow_html=True,
    )


# ── Helpers ───────────────────────────────────────────────────────────────


def _load_file(uploaded_file) -> pd.DataFrame | None:
    """Cargar CSV o Excel a DataFrame."""
    try:
        name = uploaded_file.name.lower()
        if name.endswith(".csv"):
            return pd.read_csv(uploaded_file)
        elif name.endswith((".xlsx", ".xls")):
            return pd.read_excel(uploaded_file)
        else:
            st.error("Formato no soportado. Usa CSV o Excel (.xlsx).")
            return None
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None


def _format_kpi_value(value) -> str:
    """Formatear un valor de KPI para mostrar."""
    if isinstance(value, float):
        if abs(value) < 1:
            return f"{value * 100:.1f}%"
        return f"{value:,.2f}"
    return str(value)


def _severity_icon(severity: str) -> str:
    """Icono segun severidad de anomalia."""
    icons = {
        "critica": "🔴",
        "alta": "🟠",
        "media": "🟡",
        "baja": "🔵",
    }
    return icons.get(severity.lower(), "⚪")


@st.cache_resource
def _get_api_client() -> httpx.Client:
    """Cliente HTTP reutilizable para la API de OpsAgent."""
    return httpx.Client(base_url=API_BASE_URL, timeout=120.0)


def _get_auth_headers() -> dict:
    """Headers de autenticacion si hay token disponible."""
    token = get_access_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _run_pipeline(uploaded_file) -> dict:
    """Llamar POST /diagnose y retornar el resultado como dict."""
    client = _get_api_client()
    try:
        response = client.post(
            "/diagnose",
            files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "application/octet-stream")},
            headers=_get_auth_headers(),
        )
        response.raise_for_status()
        data = response.json()
        data["processing_status"] = data.get("status", "done")
        return data
    except httpx.ConnectError:
        return {"processing_status": "error", "error": "No se pudo conectar a la API. Esta corriendo uvicorn en localhost:8000?"}
    except httpx.HTTPStatusError as e:
        detail = e.response.text
        if e.response.status_code == 401:
            return {"processing_status": "error", "error": "Sesion expirada. Volve a iniciar sesion."}
        return {"processing_status": "error", "error": f"Error de API ({e.response.status_code}): {detail}"}
    except Exception as e:
        return {"processing_status": "error", "error": f"Error inesperado: {e}"}


# ── Main UI ───────────────────────────────────────────────────────────────

st.title("Diagnostico Operativo")
st.markdown("Subi tus datos operativos y recibe un diagnostico completo con recomendaciones accionables.")

# Verificar que la API backend esta corriendo
try:
    _health = _get_api_client().get("/health").json()
    if _health.get("status") == "degraded":
        st.warning(f"API en modo degradado: {_health.get('warning', '')}")
except httpx.ConnectError:
    st.error(
        "**No se pudo conectar a la API backend.** "
        "Asegurate de correr: `uvicorn opsagent.api.main:app --reload --port 8000`"
    )
    st.stop()

# ── Upload ────────────────────────────────────────────────────────────────

uploaded_file = st.file_uploader(
    "Subi tu archivo de datos operativos",
    type=["csv", "xlsx", "xls"],
    help="CSV o Excel con datos de manufactura, logistica o alimentos.",
)

if uploaded_file is None:
    # Estado inicial: mostrar instrucciones
    st.info(
        "**Para empezar**, subi un archivo CSV o Excel con tus datos operativos.\n\n"
        "El sistema detecta automaticamente el dominio (manufactura, logistica, alimentos) "
        "y calcula los KPIs relevantes."
    )
    st.stop()

# ── Preview ───────────────────────────────────────────────────────────────

df = _load_file(uploaded_file)
if df is None:
    st.stop()

st.subheader("Vista previa")
col_info, col_preview = st.columns([1, 3])

with col_info:
    st.metric("Filas", len(df))
    st.metric("Columnas", len(df.columns))
    st.caption(f"**Archivo:** {uploaded_file.name}")

with col_preview:
    st.dataframe(df.head(10), use_container_width=True)

# ── Analyze button ────────────────────────────────────────────────────────

st.divider()

if st.button("🔍 Analizar", type="primary", use_container_width=True):
    start_time = time.time()

    with st.spinner("Ejecutando pipeline de diagnostico... (puede tardar 15-30s)"):
        result = _run_pipeline(uploaded_file)

    elapsed = result.get("processing_time_seconds", time.time() - start_time)

    # Guardar resultado en session_state para persistencia
    st.session_state["result"] = result
    st.session_state["elapsed"] = elapsed

# ── Results ───────────────────────────────────────────────────────────────

if "result" not in st.session_state:
    st.stop()

result = st.session_state["result"]
elapsed = st.session_state.get("elapsed", 0)

# Error check
if result.get("processing_status") == "error":
    st.error(f"**Error en el pipeline:** {result.get('error', 'Error desconocido')}")
    st.stop()

st.divider()

# ── Executive Summary ─────────────────────────────────────────────────────

st.subheader("Resumen Ejecutivo")
st.info(result.get("executive_summary", "Sin resumen disponible."))

# ── KPIs ──────────────────────────────────────────────────────────────────

st.subheader("KPIs")

kpis = result.get("kpis", {})
if kpis:
    # Separar KPIs simples de KPIs compuestos (dicts)
    simple_kpis = {k: v for k, v in kpis.items() if not isinstance(v, dict)}
    compound_kpis = {k: v for k, v in kpis.items() if isinstance(v, dict)}

    # Mostrar KPIs simples como metricas
    if simple_kpis:
        cols = st.columns(len(simple_kpis))
        for col, (name, value) in zip(cols, simple_kpis.items()):
            label = name.replace("_", " ").title()
            col.metric(label, _format_kpi_value(value))

    # Mostrar KPIs compuestos (ej: throughput_por_linea)
    for name, sub_kpis in compound_kpis.items():
        with st.expander(f"📊 {name.replace('_', ' ').title()}", expanded=False):
            sub_cols = st.columns(min(len(sub_kpis), 4))
            for col, (sub_name, sub_value) in zip(sub_cols, sub_kpis.items()):
                col.metric(str(sub_name), _format_kpi_value(sub_value))
else:
    st.caption("No se calcularon KPIs.")

# ── Anomalies ─────────────────────────────────────────────────────────────

anomalies = result.get("anomalies", [])
st.subheader(f"Anomalias ({len(anomalies)})")

if anomalies:
    for a in anomalies:
        severity = a.get("severidad", "baja")
        icon = _severity_icon(severity)
        detail = a.get("detalle", "Sin detalle")
        campo = a.get("campo", "")

        if severity in ("critica", "alta"):
            st.warning(f"{icon} **[{severity.upper()}]** {detail}")
        else:
            st.caption(f"{icon} **[{severity.upper()}]** {detail}")
else:
    st.success("No se detectaron anomalias.")

# ── Trends ────────────────────────────────────────────────────────────────

trends = result.get("trends", [])
if trends:
    st.subheader(f"Tendencias ({len(trends)})")
    for t in trends:
        direction = t.get("direccion", "estable")
        metric = t.get("metrica", "?")
        magnitude = t.get("magnitud", 0)

        arrow = "📈" if direction == "ascendente" else "📉" if direction == "descendente" else "➡️"
        st.caption(f"{arrow} **{metric}**: {direction} ({magnitude:.1%})")

# ── Diagnosis ─────────────────────────────────────────────────────────────

st.subheader("Diagnostico Completo")
st.markdown(result.get("diagnosis", "Sin diagnostico disponible."))

# ── Recommendations ───────────────────────────────────────────────────────

recommendations = result.get("recommendations", [])
st.subheader(f"Recomendaciones ({len(recommendations)})")

if recommendations:
    for rec in recommendations:
        priority = rec.get("prioridad", 0)
        action = rec.get("accion", "")
        impact = rec.get("impacto", "")
        timeline = rec.get("plazo", "")

        with st.container(border=True):
            st.markdown(f"**#{priority} — {action}**")
            r_col1, r_col2 = st.columns(2)
            r_col1.caption(f"💡 **Impacto:** {impact}")
            r_col2.caption(f"⏱️ **Plazo:** {timeline}")
else:
    st.caption("No se generaron recomendaciones.")

# ── PDF Download ──────────────────────────────────────────────────────────

st.divider()

diagnose_id = result.get("id", "")
if diagnose_id:
    try:
        pdf_response = _get_api_client().get(
            f"/diagnose/{diagnose_id}/pdf",
            headers=_get_auth_headers(),
        )
        if pdf_response.status_code == 200:
            st.download_button(
                label="📄 Descargar Reporte PDF",
                data=pdf_response.content,
                file_name=f"diagnostico-{diagnose_id[:8]}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
    except Exception:
        pass

# ── Footer ────────────────────────────────────────────────────────────────

st.divider()

domain = result.get("detected_domain", "desconocido")
quality = result.get("data_quality_report", {})
valid_rows = quality.get("filas_validas", "?")
original_rows = quality.get("filas_originales", "?")

st.caption(
    f"Dominio detectado: **{domain}** | "
    f"Datos: {valid_rows}/{original_rows} filas validas | "
    f"Tiempo de ejecucion: {elapsed:.1f}s"
)
