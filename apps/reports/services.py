
from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from apps.reservations.models import Reserva
from apps.payments.models import Pago, Reembolso


CERO = Decimal("0.00")


def obtener_fechas(request):
    """
    Lee y valida las fechas de los filtros.
    Formato esperado: AAAA-MM-DD.
    """
    desde_texto = request.GET.get("desde", "").strip()
    hasta_texto = request.GET.get("hasta", "").strip()

    try:
        desde = date.fromisoformat(desde_texto) if desde_texto else None
        hasta = date.fromisoformat(hasta_texto) if hasta_texto else None
    except ValueError:
        raise ValueError("Las fechas ingresadas no son válidas.")

    if desde and hasta and desde > hasta:
        raise ValueError(
            "La fecha inicial no puede ser posterior a la final."
        )

    return desde, hasta


def filtrar_por_fechas(queryset, campo, desde, hasta):
    if desde:
        queryset = queryset.filter(
            **{f"{campo}__date__gte": desde}
        )

    if hasta:
        queryset = queryset.filter(
            **{f"{campo}__date__lte": hasta}
        )

    return queryset


def obtener_reporte(desde=None, hasta=None):
    """
    Obtiene información administrativa desde PostgreSQL.

    Cada registro se filtra según su propia fecha:
    - Reservas: fecha_reserva
    - Pagos: fecha_pago
    - Reembolsos: fecha_procesado
    """

    reservas = Reserva.objects.select_related(
        "cliente",
        "paquete",
    ).order_by("-fecha_reserva")

    pagos = Pago.objects.select_related(
        "reserva",
    ).order_by("-fecha_pago")

    reembolsos = Reembolso.objects.select_related(
        "reserva",
        "pago",
    ).order_by("-fecha_procesado")

    reservas = filtrar_por_fechas(
        reservas, "fecha_reserva", desde, hasta
    )

    pagos = filtrar_por_fechas(
        pagos, "fecha_pago", desde, hasta
    )

    # Solo los reembolsos procesados se consideran
    # para calcular las devoluciones realizadas.
    reembolsos_procesados = reembolsos.filter(
        estado="procesado"
    )

    reembolsos_procesados = filtrar_por_fechas(
        reembolsos_procesados,
        "fecha_procesado",
        desde,
        hasta,
    )

    # Pagos completados en el periodo.
    pagos_completados = pagos.filter(
        estado="completado"
    )

    total_ingresos = (
        pagos_completados.aggregate(
            total=Sum("monto")
        )["total"] or CERO
    )

    total_reembolsos = (
        reembolsos_procesados.aggregate(
            total=Sum("monto_reembolso")
        )["total"] or CERO
    )

    # Indicador simplificado de flujo neto.
    # No equivale a utilidad ni a contabilidad completa.
    flujo_neto = total_ingresos - total_reembolsos

    estados_reservas = list(
        reservas.values("estado")
        .annotate(cantidad=Count("id"))
        .order_by("estado")
    )

    estados_pagos = list(
        pagos.values("estado")
        .annotate(cantidad=Count("id"))
        .order_by("estado")
    )

    return {
        "desde": desde,
        "hasta": hasta,
        "fecha_generacion": timezone.localtime(),

        "total_reservas": reservas.count(),
        "reservas_pendientes": reservas.filter(
            estado="pendiente"
        ).count(),
        "reservas_confirmadas": reservas.filter(
            estado="confirmada"
        ).count(),
        "reservas_canceladas": reservas.filter(
            estado="cancelada"
        ).count(),

        "total_pagos": pagos.count(),
        "pagos_completados": pagos_completados.count(),
        "total_ingresos": total_ingresos,
        "total_reembolsos": total_reembolsos,
        "flujo_neto": flujo_neto,

        "estados_reservas": estados_reservas,
        "estados_pagos": estados_pagos,

        "reservas": reservas,
        "pagos": pagos,
        "reembolsos": reembolsos_procesados,
    }
