"""Asignación automática de alojamiento para reservas de paquetes.

No altera el trigger de cupos/asientos. Se llama DENTRO de la transacción de
creación o modificación de reservas. Solo reservas pendientes/confirmadas
consumen inventario; las canceladas/expiradas conservan historial sin ocupar.
"""
from collections import defaultdict
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.hotels.models import TipoHabitacion
from apps.packages.models import PaqueteHotel
from .models import AsignacionHabitacion, Reserva

ACTIVAS = (Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA)


def _fechas(paquete, componente):
    entrada = paquete.fecha_salida + timedelta(days=componente.dia_inicio - 1)
    salida = entrada + timedelta(days=componente.noches)
    if componente.dia_inicio < 1 or componente.noches < 1 or salida > paquete.fecha_retorno:
        raise ValidationError(
            f"El alojamiento {componente.tipo_habitacion} está fuera de las fechas del paquete."
        )
    return entrada, salida


@transaction.atomic
def sincronizar_alojamiento(reserva):
    """Recalcula todas las asignaciones para la reserva de forma transaccional.

    Bloquea inventarios en orden estable para serializar reservas simultáneas.
    Agrupa alternativas del mismo hotel y estancia; diferentes hoteles/fechas
    se consideran etapas diferentes, cada una alojando a todos los pasajeros.
    """
    reserva = Reserva.objects.select_for_update().select_related("paquete").get(pk=reserva.pk)
    if reserva.estado not in ACTIVAS:
        return
    componentes = list(PaqueteHotel.objects.filter(paquete_id=reserva.paquete_id)
                       .select_related("tipo_habitacion", "tipo_habitacion__hotel")
                       .order_by("tipo_habitacion_id"))
    if not componentes:
        # Paquetes sin hoteles siguen reservables: no se inventa alojamiento.
        AsignacionHabitacion.objects.filter(reserva=reserva).delete()
        return
    ids = sorted({c.tipo_habitacion_id for c in componentes})
    tipos = {t.pk: t for t in TipoHabitacion.objects.select_for_update()
             .filter(pk__in=ids).order_by("pk")}
    grupos = defaultdict(list)
    for c in componentes:
        entrada, salida = _fechas(reserva.paquete, c)
        grupos[(tipos[c.tipo_habitacion_id].hotel_id, entrada, salida)].append(c.tipo_habitacion_id)
    # Diferentes etapas no pueden solaparse. Alternativas del mismo hotel y
    # fechas exactas ya se agruparon como una sola etapa.
    etapas = sorted(grupos)
    for i, (hotel_a, inicio_a, fin_a) in enumerate(etapas):
        for hotel_b, inicio_b, fin_b in etapas[i + 1:]:
            if inicio_a < fin_b and inicio_b < fin_a:
                raise ValidationError(
                    "El paquete tiene alojamientos de etapas diferentes con fechas "
                    "solapadas. Corrige los días de inicio y las noches."
                )
    plan = []
    for (_, entrada, salida), opciones in sorted(grupos.items()):
        faltan = reserva.cantidad_pasajeros
        # Mayor capacidad primero; en caso de empate, menor id.
        opciones.sort(key=lambda tid: (-tipos[tid].capacidad, tid))
        for tipo_id in opciones:
            tipo = tipos[tipo_id]
            if tipo.capacidad < 1:
                raise ValidationError(f"Capacidad inválida en {tipo}.")
            # Cada noche tiene un máximo independiente; se usa el pico de ocupación.
            ocupaciones = (AsignacionHabitacion.objects
                           .filter(tipo_habitacion_id=tipo_id,
                                   fecha_entrada__lt=salida, fecha_salida__gt=entrada,
                                   reserva__estado__in=ACTIVAS)
                           .exclude(reserva_id=reserva.pk)
                           .values("fecha_entrada", "fecha_salida", "cantidad_habitaciones"))
            max_ocupadas = 0
            dia = entrada
            filas = list(ocupaciones)
            while dia < salida:
                ocupadas = sum(x["cantidad_habitaciones"] for x in filas
                                if x["fecha_entrada"] <= dia < x["fecha_salida"])
                max_ocupadas = max(max_ocupadas, ocupadas)
                dia += timedelta(days=1)
            # 'disponibles' puede reflejar bloqueos manuales ajenos a este módulo.
            # Evitamos sobreasignar el total, pero NO restamos este campo por fecha.
            libres = max(0, tipo.habitaciones_total - max_ocupadas)
            usar = min(libres, (faltan + tipo.capacidad - 1) // tipo.capacidad)
            if usar:
                plan.append((tipo_id, entrada, salida, usar))
                faltan = max(0, faltan - usar * tipo.capacidad)
            if faltan == 0:
                break
        if faltan:
            raise ValidationError(
                f"No hay habitaciones suficientes para {reserva.cantidad_pasajeros} "
                f"pasajeros del {entrada:%d/%m/%Y} al {salida:%d/%m/%Y}."
            )
    AsignacionHabitacion.objects.filter(reserva=reserva).delete()
    AsignacionHabitacion.objects.bulk_create([
        AsignacionHabitacion(reserva=reserva, tipo_habitacion_id=tid,
                            fecha_entrada=entrada, fecha_salida=salida,
                            cantidad_habitaciones=cantidad)
        for tid, entrada, salida, cantidad in plan
    ])
