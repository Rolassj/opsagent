"""Generador de reportes PDF profesionales para OpsAgent.

Toma el output del pipeline de diagnostico y genera un PDF descargable
con resumen ejecutivo, KPIs, anomalias y recomendaciones priorizadas.
"""

import io
import re
from datetime import datetime
from html import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)


# ── Estilos ──────────────────────────────────────────────────────────────

_BRAND_COLOR = colors.HexColor("#1a56db")
_BRAND_LIGHT = colors.HexColor("#e8edfb")
_SEVERITY_COLORS = {
    "critica": colors.HexColor("#dc2626"),
    "alta": colors.HexColor("#ea580c"),
    "media": colors.HexColor("#ca8a04"),
    "baja": colors.HexColor("#2563eb"),
}


def _build_styles() -> dict:
    """Crear estilos personalizados para el reporte."""
    base = getSampleStyleSheet()
    styles = {}

    styles["title"] = ParagraphStyle(
        "ReportTitle",
        parent=base["Title"],
        fontSize=22,
        textColor=_BRAND_COLOR,
        spaceAfter=4 * mm,
    )
    styles["subtitle"] = ParagraphStyle(
        "ReportSubtitle",
        parent=base["Normal"],
        fontSize=10,
        textColor=colors.gray,
        spaceAfter=6 * mm,
    )
    styles["heading"] = ParagraphStyle(
        "SectionHeading",
        parent=base["Heading2"],
        fontSize=14,
        textColor=_BRAND_COLOR,
        spaceBefore=8 * mm,
        spaceAfter=3 * mm,
    )
    styles["body"] = ParagraphStyle(
        "BodyText",
        parent=base["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=2 * mm,
    )
    styles["summary_box"] = ParagraphStyle(
        "SummaryBox",
        parent=base["Normal"],
        fontSize=11,
        leading=16,
        spaceAfter=2 * mm,
        backColor=_BRAND_LIGHT,
        borderPadding=8,
    )
    styles["rec_title"] = ParagraphStyle(
        "RecTitle",
        parent=base["Normal"],
        fontSize=11,
        textColor=_BRAND_COLOR,
        fontName="Helvetica-Bold",
    )
    styles["rec_detail"] = ParagraphStyle(
        "RecDetail",
        parent=base["Normal"],
        fontSize=9,
        textColor=colors.gray,
        leftIndent=12,
    )

    return styles


# ── Sanitización de texto para ReportLab ────────────────────────────────


def _sanitize_text_for_reportlab(text: str) -> str:
    """Sanitizar texto para ReportLab: convertir markdown bold/italic a HTML válido.

    ReportLab usa un subconjunto de HTML que requiere tags bien formados.
    Esta función:
    1. Escapa caracteres especiales XML (&, <, >, ")
    2. Convierte markdown bold (**texto**) a <b>texto</b>
    3. Convierte markdown italic (*texto*) a <i>texto</i>
    4. Cierra cualquier tag abierto sin cerrar

    Args:
        text: Texto con posible markdown y caracteres especiales

    Returns:
        Texto sanitizado y HTML-válido para ReportLab
    """
    if not text:
        return ""

    # Escape de caracteres especiales XML (& debe ir primero)
    text = escape(text, quote=True)

    # Convertir markdown bold (**texto**) a HTML bold (<b>texto</b>)
    # Usar regex non-greedy para emparejar pares correctos
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # Convertir markdown italic (*texto*) a HTML italic (<i>texto</i>)
    # Pero evitar conflictos con **
    text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)

    # Validación: cerrar cualquier tag abierto sin cerrar
    # Contar tags abiertos y cerrados
    open_b = text.count('<b>') - text.count('</b>')
    open_i = text.count('<i>') - text.count('</i>')

    if open_b > 0:
        text += '</b>' * open_b
    if open_i > 0:
        text += '</i>' * open_i

    return text


# ── Generador principal ──────────────────────────────────────────────────


def generate_pdf(diagnosis_data: dict, filename: str = "") -> bytes:
    """Generar reporte PDF a partir del output del pipeline.

    Args:
        diagnosis_data: Dict con las claves del DiagnoseResponse
            (status, detected_domain, executive_summary, kpis,
             anomalies, trends, diagnosis, recommendations,
             data_quality_report, processing_time_seconds)
        filename: Nombre del archivo analizado (opcional)

    Returns:
        Bytes del PDF generado, listo para descargar o guardar.
    """
    # Convertir diagnosis_data a dict plano si contiene objetos Pydantic
    if hasattr(diagnosis_data, 'model_dump'):
        diagnosis_data = diagnosis_data.model_dump()
    elif hasattr(diagnosis_data, '__dict__'):
        # Fallback para otros tipos de objetos
        import json
        diagnosis_data = json.loads(json.dumps(diagnosis_data, default=str))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = _build_styles()
    elements = []

    # ── Header ───────────────────────────────────────────────────────
    elements.append(Paragraph("OpsAgent — Reporte de Diagnostico", styles["title"]))

    meta_parts = []
    if filename:
        meta_parts.append(f"Archivo: {str(filename)}")
    domain = str(diagnosis_data.get("detected_domain", "desconocido"))
    meta_parts.append(f"Dominio: {domain.title()}")
    meta_parts.append(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    processing_time = float(diagnosis_data.get("processing_time_seconds", 0) or 0)
    if processing_time:
        meta_parts.append(f"Tiempo de procesamiento: {processing_time:.1f}s")
    elements.append(Paragraph(" | ".join(meta_parts), styles["subtitle"]))

    elements.append(HRFlowable(width="100%", thickness=1, color=_BRAND_COLOR))
    elements.append(Spacer(1, 4 * mm))

    # ── Resumen Ejecutivo ────────────────────────────────────────────
    summary = str(diagnosis_data.get("executive_summary", ""))
    if summary and summary.strip():
        elements.append(Paragraph("Resumen Ejecutivo", styles["heading"]))
        elements.append(Paragraph(_sanitize_text_for_reportlab(summary), styles["summary_box"]))

    # ── KPIs ─────────────────────────────────────────────────────────
    kpis = diagnosis_data.get("kpis", {}) or {}
    if kpis:
        elements.append(Paragraph("KPIs", styles["heading"]))

        # Convertir kpis a dict si es un objeto Pydantic
        if hasattr(kpis, 'model_dump'):
            kpis = kpis.model_dump()
        if not isinstance(kpis, dict):
            kpis = {}

        # Separar KPIs simples de compuestos
        simple = {k: v for k, v in kpis.items() if not isinstance(v, dict)}
        compound = {k: v for k, v in kpis.items() if isinstance(v, dict)}

        if simple:
            kpi_table_data = [["Metrica", "Valor"]]
            for name, value in simple.items():
                label = name.replace("_", " ").title()
                formatted = _format_kpi(value)
                kpi_table_data.append([label, formatted])

            t = Table(kpi_table_data, colWidths=[90 * mm, 60 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), _BRAND_COLOR),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _BRAND_LIGHT]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 3 * mm))

        for group_name, sub_kpis in compound.items():
            elements.append(Paragraph(
                f"{group_name.replace('_', ' ').title()}:",
                styles["body"],
            ))
            sub_data = [["Clave", "Valor"]]
            for k, v in sub_kpis.items():
                sub_data.append([str(k), _format_kpi(v)])
            t = Table(sub_data, colWidths=[90 * mm, 60 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6b7280")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 2 * mm))

    # ── Anomalias ────────────────────────────────────────────────────
    anomalies = diagnosis_data.get("anomalies", [])
    if anomalies:
        elements.append(Paragraph(f"Anomalias ({len(anomalies)})", styles["heading"]))

        anom_data = [["Severidad", "Campo", "Detalle"]]
        for a in anomalies:
            # Convertir dict si es necesario
            if hasattr(a, 'model_dump'):
                a = a.model_dump()
            elif not isinstance(a, dict):
                continue

            sev = str(a.get("severidad", "baja")).upper()
            campo = str(a.get("campo", ""))
            detalle = _sanitize_text_for_reportlab(str(a.get("detalle", "")))
            anom_data.append([sev, campo, Paragraph(detalle, styles["body"])])

        t = Table(anom_data, colWidths=[25 * mm, 35 * mm, 100 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _BRAND_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))

        # Color de fondo por severidad
        if len(anom_data) > 1:
            for i, a in enumerate(anomalies, start=1):
                # Convertir dict si es necesario
                if hasattr(a, 'model_dump'):
                    a = a.model_dump()
                if isinstance(a, dict):
                    sev = str(a.get("severidad", "baja"))
                    bg = _SEVERITY_COLORS.get(sev, colors.white)
                    t.setStyle(TableStyle([
                        ("TEXTCOLOR", (0, i), (0, i), bg),
                        ("FONTNAME", (0, i), (0, i), "Helvetica-Bold"),
                    ]))

            elements.append(t)

    # ── Tendencias ───────────────────────────────────────────────────
    trends = diagnosis_data.get("trends", [])
    if trends:
        elements.append(Paragraph(f"Tendencias ({len(trends)})", styles["heading"]))
        for trend_item in trends:
            # Convertir dict si es necesario
            if hasattr(trend_item, 'model_dump'):
                trend_item = trend_item.model_dump()
            elif not isinstance(trend_item, dict):
                continue

            direction = str(trend_item.get("direccion", "estable"))
            metric = str(trend_item.get("metrica", "?"))
            magnitude = float(trend_item.get("magnitud", 0))
            arrow = "↑" if direction == "ascendente" else "↓" if direction == "descendente" else "→"
            elements.append(Paragraph(
                f"{arrow} <b>{metric.replace('_', ' ').title()}</b>: {direction} ({magnitude:.1%})",
                styles["body"],
            ))

    # ── Diagnostico Completo ─────────────────────────────────────────
    diag_text = str(diagnosis_data.get("diagnosis", ""))
    if diag_text and diag_text.strip():
        elements.append(Paragraph("Diagnostico Completo", styles["heading"]))
        for paragraph in diag_text.split("\n\n"):
            paragraph = paragraph.strip()
            if paragraph:
                # Sanitizar markdown y caracteres especiales
                paragraph = _sanitize_text_for_reportlab(paragraph)
                elements.append(Paragraph(paragraph, styles["body"]))

    # ── Recomendaciones ──────────────────────────────────────────────
    recommendations = diagnosis_data.get("recommendations", [])
    if recommendations:
        elements.append(Paragraph(
            f"Recomendaciones ({len(recommendations)})", styles["heading"],
        ))

        for rec in recommendations:
            # Convertir dict si es necesario
            if hasattr(rec, 'model_dump'):
                rec = rec.model_dump()
            elif not isinstance(rec, dict):
                continue  # Saltar si no es dict o Pydantic model

            priority = int(rec.get("prioridad", 0))
            action = _sanitize_text_for_reportlab(str(rec.get("accion", "")))
            impact = _sanitize_text_for_reportlab(str(rec.get("impacto", "")))
            timeline = _sanitize_text_for_reportlab(str(rec.get("plazo", "")))

            elements.append(Paragraph(
                f"#{priority} — {action}", styles["rec_title"],
            ))
            elements.append(Paragraph(
                f"Impacto: {impact} | Plazo: {timeline}", styles["rec_detail"],
            ))
            elements.append(Spacer(1, 2 * mm))

    # ── Calidad de datos ─────────────────────────────────────────────
    quality = diagnosis_data.get("data_quality_report", {}) or {}
    if quality:
        # Convertir quality a dict si es un objeto Pydantic
        if hasattr(quality, 'model_dump'):
            quality = quality.model_dump()
        if not isinstance(quality, dict):
            quality = {}

        if quality:  # Verificar nuevamente después de conversión
            elements.append(Paragraph("Calidad de Datos", styles["heading"]))
            orig = quality.get("filas_originales", "?")
            valid = quality.get("filas_validas", "?")
            removed = quality.get("filas_eliminadas", 0)
            elements.append(Paragraph(
                f"Filas originales: {orig} | Filas validas: {valid} | Eliminadas: {removed}",
                styles["body"],
            ))
            problems = quality.get("problemas", [])
            if problems:
                for p in problems:
                    p_safe = _sanitize_text_for_reportlab(str(p))
                    elements.append(Paragraph(f"• {p_safe}", styles["body"]))

    # ── Footer ───────────────────────────────────────────────────────
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    elements.append(Paragraph(
        f"Generado por OpsAgent v0.2.0 — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle("Footer", fontSize=8, textColor=colors.gray, alignment=1),
    ))

    doc.build(elements)
    return buffer.getvalue()


# ── Helpers ──────────────────────────────────────────────────────────────


def _format_kpi(value) -> str:
    """Formatear valor de KPI para mostrar en tabla."""
    if isinstance(value, float):
        if abs(value) < 1:
            return f"{value * 100:.1f}%"
        return f"{value:,.2f}"
    return str(value)
