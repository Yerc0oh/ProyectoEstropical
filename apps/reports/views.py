
from io import BytesIO

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from apps.core.access import admin_required

from .services import obtener_fechas, obtener_reporte


def datos_reporte(request):
    try:
        desde, hasta = obtener_fechas(request)
        reporte = obtener_reporte(desde, hasta)
        return reporte, None
    except ValueError as error:
        return None, str(error)


def formato_monto(valor):
    return f"{valor:,.2f}"


def formato_fecha(valor):
    if not valor:
        return "-"

    if timezone.is_aware(valor):
        valor = timezone.localtime(valor)

    return valor.strftime("%d/%m/%Y %H:%M")


@admin_required
def dashboard(request):
    reporte, error = datos_reporte(request)

    if error:
        return render(
            request,
            "reports/dashboard.html",
            {"error": error},
            status=400,
        )

    return render(
        request,
        "reports/dashboard.html",
        reporte,
    )


@admin_required
def exportar_excel(request):
    reporte, error = datos_reporte(request)

    if error:
        return HttpResponse(error, status=400)

    libro = Workbook()
    resumen = libro.active
    resumen.title = "Resumen"

    resumen.append(["ESTROPICAL - REPORTE ADMINISTRATIVO"])
    resumen.append([
        "Generado",
        formato_fecha(reporte["fecha_generacion"]),
    ])
    resumen.append([
        "Desde",
        str(reporte["desde"] or "Sin límite"),
    ])
    resumen.append([
        "Hasta",
        str(reporte["hasta"] or "Sin límite"),
    ])
    resumen.append([])

    indicadores = [
        ("Total reservas", reporte["total_reservas"]),
        ("Reservas pendientes", reporte["reservas_pendientes"]),
        ("Reservas confirmadas", reporte["reservas_confirmadas"]),
        ("Reservas canceladas", reporte["reservas_canceladas"]),
        ("Total pagos", reporte["total_pagos"]),
        ("Pagos completados", reporte["pagos_completados"]),
        ("Ingresos registrados (Bs)", reporte["total_ingresos"]),
        ("Reembolsos procesados (Bs)", reporte["total_reembolsos"]),
        ("Flujo neto simplificado (Bs)", reporte["flujo_neto"]),
    ]

    for etiqueta, valor in indicadores:
        resumen.append([etiqueta, valor])

    hoja_reservas = libro.create_sheet("Reservas")
    hoja_reservas.append([
        "Código",
        "Paquete",
        "Estado",
        "Pasajeros",
        "Total (Bs)",
        "Fecha",
    ])

    for reserva in reporte["reservas"].iterator():
        hoja_reservas.append([
            reserva.codigo,
            str(reserva.paquete),
            reserva.get_estado_display(),
            reserva.cantidad_pasajeros,
            float(reserva.total or 0),
            formato_fecha(reserva.fecha_reserva),
        ])

    hoja_pagos = libro.create_sheet("Pagos")
    hoja_pagos.append([
        "Reserva",
        "Método",
        "Estado",
        "Monto (Bs)",
        "Fecha",
    ])

    for pago in reporte["pagos"].iterator():
        hoja_pagos.append([
            pago.reserva.codigo,
            pago.get_metodo_display(),
            pago.get_estado_display(),
            float(pago.monto or 0),
            formato_fecha(pago.fecha_pago),
        ])

    hoja_reembolsos = libro.create_sheet("Reembolsos")
    hoja_reembolsos.append([
        "Reserva",
        "Estado",
        "Monto reembolsado (Bs)",
        "Fecha de procesamiento",
    ])

    for reembolso in reporte["reembolsos"].iterator():
        hoja_reembolsos.append([
            reembolso.reserva.codigo,
            reembolso.get_estado_display(),
            float(reembolso.monto_reembolso or 0),
            formato_fecha(reembolso.fecha_procesado),
        ])

    for hoja in libro.worksheets:
        hoja.freeze_panes = "A2"

        for celda in hoja[1]:
            celda.font = Font(
                bold=True,
                color="FFFFFF",
            )
            celda.fill = PatternFill(
                "solid",
                fgColor="17365D",
            )
            celda.alignment = Alignment(
                horizontal="center"
            )

        for columna in hoja.columns:
            letra = get_column_letter(columna[0].column)
            ancho = max(
                len(str(celda.value or ""))
                for celda in columna
            )
            hoja.column_dimensions[letra].width = min(
                max(ancho + 3, 15),
                48,
            )

    salida = BytesIO()
    libro.save(salida)
    salida.seek(0)

    respuesta = HttpResponse(
        salida.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )
    respuesta["Content-Disposition"] = (
        'attachment; filename="estropical_reporte.xlsx"'
    )

    return respuesta


@admin_required
def exportar_pdf(request):
    reporte, error = datos_reporte(request)

    if error:
        return HttpResponse(error, status=400)

    salida = BytesIO()

    documento = SimpleDocTemplate(
        salida,
        pagesize=landscape(A4),
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    estilos = getSampleStyleSheet()
    elementos = []

    elementos.append(
        Paragraph(
            "ESTROPICAL - REPORTE ADMINISTRATIVO",
            estilos["Title"],
        )
    )

    elementos.append(
        Paragraph(
            "Periodo: "
            f"{reporte['desde'] or 'Inicio'} "
            f"al {reporte['hasta'] or 'Actualidad'}",
            estilos["Normal"],
        )
    )

    elementos.append(Spacer(1, 15))

    resumen = [
        ["Indicador", "Resultado"],
        ["Total reservas", str(reporte["total_reservas"])],
        ["Reservas pendientes", str(reporte["reservas_pendientes"])],
        ["Reservas confirmadas", str(reporte["reservas_confirmadas"])],
        ["Reservas canceladas", str(reporte["reservas_canceladas"])],
        ["Pagos completados", str(reporte["pagos_completados"])],
        [
            "Ingresos registrados (Bs)",
            formato_monto(reporte["total_ingresos"]),
        ],
        [
            "Reembolsos procesados (Bs)",
            formato_monto(reporte["total_reembolsos"]),
        ],
        [
            "Flujo neto simplificado (Bs)",
            formato_monto(reporte["flujo_neto"]),
        ],
    ]

    tabla = Table(
        resumen,
        colWidths=[300, 160],
        repeatRows=1,
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 20))

    elementos.append(
        Paragraph(
            "Últimas reservas del periodo",
            estilos["Heading2"],
        )
    )

    filas = [[
        "Código",
        "Paquete",
        "Estado",
        "Pasajeros",
        "Total (Bs)",
    ]]

    for reserva in reporte["reservas"][:25]:
        filas.append([
            Paragraph(str(reserva.codigo), estilos["BodyText"]),
            Paragraph(str(reserva.paquete), estilos["BodyText"]),
            reserva.get_estado_display(),
            str(reserva.cantidad_pasajeros),
            formato_monto(reserva.total or 0),
        ])

    if len(filas) == 1:
        filas.append(["Sin reservas", "-", "-", "-", "-"])

    tabla_reservas = Table(
        filas,
        colWidths=[110, 260, 120, 100, 110],
        repeatRows=1,
        hAlign="LEFT",
    )

    tabla_reservas.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    elementos.append(tabla_reservas)
    elementos.append(Spacer(1, 12))

    elementos.append(
        Paragraph(
            "Nota: los ingresos corresponden a pagos con estado "
            "'completado' y el flujo neto es un indicador "
            "simplificado, no una utilidad contable. "
            "El detalle PDF muestra hasta 25 reservas; "
            "Excel contiene el detalle completo.",
            estilos["Normal"],
        )
    )

    documento.build(elementos)

    respuesta = HttpResponse(
        salida.getvalue(),
        content_type="application/pdf",
    )

    respuesta["Content-Disposition"] = (
        'attachment; filename="estropical_reporte.pdf"'
    )

    return respuesta
