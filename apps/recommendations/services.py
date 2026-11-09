
from django.utils import timezone

from apps.packages.models import Paquete


def recomendar_paquetes(preferencia, limite=20):
    """
    Busca paquetes disponibles que coincidan
    con una preferencia de viaje.
    """

    hoy = timezone.localdate()

    paquetes = (
        Paquete.objects
        .filter(
            estado="publicado",
            cupos_disponibles__gt=0,
            fecha_salida__gte=hoy,
            venta_desde__lte=hoy,
            venta_hasta__gte=hoy,
        )
        .select_related("destino", "destino__pais")
    )

    destinos_ids = list(
        preferencia.destinos.values_list("id", flat=True)
    )

    if destinos_ids:
        paquetes = paquetes.filter(
            destino_id__in=destinos_ids
        )

    personas = preferencia.cantidad_personas or 1

    paquetes = paquetes.filter(
        cupos_disponibles__gte=personas
    )

    resultados = []

    for paquete in paquetes.order_by("precio_persona", "id"):
        duracion = (
            paquete.fecha_retorno - paquete.fecha_salida
        ).days + 1

        precio_total = paquete.precio_persona * personas

        if (
            preferencia.presupuesto_minimo is not None
            and precio_total < preferencia.presupuesto_minimo
        ):
            continue

        if (
            preferencia.presupuesto_maximo is not None
            and precio_total > preferencia.presupuesto_maximo
        ):
            continue

        if (
            preferencia.duracion_minima is not None
            and duracion < preferencia.duracion_minima
        ):
            continue

        if (
            preferencia.duracion_maxima is not None
            and duracion > preferencia.duracion_maxima
        ):
            continue

        resultados.append({
            "paquete": paquete,
            "duracion": duracion,
            "precio_total": precio_total,
            "personas": personas,
            "motivo": (
                "Este paquete coincide con el destino, "
                "presupuesto y duración de tu viaje."
            ),
        })

        if len(resultados) >= limite:
            break

    return resultados
