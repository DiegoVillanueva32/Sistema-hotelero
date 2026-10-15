from xml.sax.saxutils import escape

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def exportar_reporte(titulo, encabezados, filas, formato, ruta):
    """Exporta una tabla de reporte a XLSX o PDF."""
    formato = formato.lower()
    if formato == "xlsx":
        libro = Workbook()
        hoja = libro.active
        hoja.title = "Reporte"
        hoja.append([titulo])
        hoja.append(encabezados)
        for fila in filas:
            hoja.append(list(fila))
        hoja.freeze_panes = "A3"
        hoja.auto_filter.ref = hoja.dimensions
        for columna in hoja.columns:
            ancho = max(len(str(celda.value or "")) for celda in columna)
            hoja.column_dimensions[columna[0].column_letter].width = min(ancho + 2, 42)
        libro.save(ruta)
        return

    if formato != "pdf":
        raise ValueError("Formato de exportación no soportado.")

    estilos = getSampleStyleSheet()
    estilo_celda = ParagraphStyle(
        "CeldaReporte", parent=estilos["BodyText"], fontSize=7, leading=8)
    estilo_encabezado = ParagraphStyle(
        "EncabezadoReporte", parent=estilo_celda, textColor=colors.HexColor("#1e3a8a"))
    contenido = [Paragraph(escape(titulo), estilos["Title"]), Spacer(1, 12)]
    datos_tabla = [[Paragraph(escape(str(valor)), estilo_encabezado)
                    for valor in encabezados]]
    datos_tabla.extend([
        [Paragraph(escape(str(valor)), estilo_celda) for valor in fila]
        for fila in filas
    ])
    ancho_pagina = landscape(letter)[0] - 56
    tabla = Table(datos_tabla, colWidths=[ancho_pagina / len(encabezados)] * len(encabezados),
                  repeatRows=1, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    contenido.append(tabla)
    documento = SimpleDocTemplate(
        str(ruta), pagesize=landscape(letter),
        leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
    documento.build(contenido)