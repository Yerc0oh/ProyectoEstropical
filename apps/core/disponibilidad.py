"""CU-16: actualización de capacidad conservando lo ya ocupado.

Ninguno de los recursos del Sprint 2 tiene todavía una tabla de reservas, por
lo que la única información fiable de ocupación es la que ya está registrada en
el propio recurso::

    ocupado = capacidad_total - disponibilidad

Al cambiar la capacidad total se conserva ese valor ``ocupado`` y se recalcula
la disponibilidad. Nunca se iguala la disponibilidad al total, porque eso
borraría las unidades ya comprometidas.
"""
from django.db import transaction


class CapacidadInvalida(Exception):
    """El total indicado no es un número entero no negativo."""


class CapacidadPorDebajoDeOcupado(Exception):
    """Se intentó reducir el total por debajo de lo ya ocupado."""

    def __init__(self, ocupado):
        self.ocupado = ocupado
        super().__init__(
            f"No se puede reducir la capacidad por debajo de {ocupado} unidades, "
            "que ya están ocupadas o comprometidas.")


def unidades_ocupadas(instancia, campo_total, campo_disponible):
    """Unidades comprometidas según lo registrado en el propio recurso."""
    return getattr(instancia, campo_total) - getattr(instancia, campo_disponible)


@transaction.atomic
def guardar_con_capacidad(instancia, campo_total, campo_disponible):
    """Guarda ``instancia`` recalculando la disponibilidad bajo bloqueo de fila.

    La fila se vuelve a leer con ``select_for_update`` para calcular la
    ocupación con el valor vigente en la base de datos, no con el que tenía la
    instancia en memoria. En PostgreSQL dos actualizaciones simultáneas no se
    pisan: la segunda espera a que la primera confirme y recalcula sobre el
    resultado. En SQLite el bloqueo es un no-op, pero el recálculo sigue
    usando el valor persistido.
    """
    if instancia.pk is None:
        raise ValueError("guardar_con_capacidad requiere una instancia guardada.")

    actual = (type(instancia)._default_manager.select_for_update()
              .get(pk=instancia.pk))
    ocupado = unidades_ocupadas(actual, campo_total, campo_disponible)
    nuevo_total = getattr(instancia, campo_total)

    if nuevo_total is None or nuevo_total < 0:
        raise CapacidadInvalida("La capacidad total no puede ser negativa.")
    if nuevo_total < ocupado:
        raise CapacidadPorDebajoDeOcupado(ocupado)

    setattr(instancia, campo_disponible, nuevo_total - ocupado)
    instancia.save()
    return instancia
