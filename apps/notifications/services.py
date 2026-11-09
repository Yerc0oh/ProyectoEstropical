
from .models import Notificacion


def crear_notificacion(
    usuario,
    titulo,
    mensaje,
    tipo="sistema",
    url=""
):
    """
    Crea una notificación para un usuario de Estropical.
    """
    if usuario is None:
        return None

    return Notificacion.objects.create(
        usuario=usuario,
        titulo=titulo,
        mensaje=mensaje,
        tipo=tipo,
        url=url
    )


def notificar_reserva(reserva):
    """
    Notifica al cliente cuando registra una reserva.
    """
    return crear_notificacion(
        usuario=reserva.cliente.usuario,
        titulo="Reserva registrada",
        mensaje=(
            f"Tu reserva {reserva.codigo} "
            f"ha sido registrada correctamente. "
            f"Estado actual: "
            f"{reserva.get_estado_display()}."
        ),
        tipo="reserva"
    )


def notificar_cambio_reserva(reserva):
    """
    Notifica cuando cambia el estado de una reserva.
    """
    return crear_notificacion(
        usuario=reserva.cliente.usuario,
        titulo="Actualización de reserva",
        mensaje=(
            f"Tu reserva {reserva.codigo} "
            f"cambió al estado: "
            f"{reserva.get_estado_display()}."
        ),
        tipo="reserva"
    )


def notificar_pago(pago):
    """
    Notifica al cliente sobre un pago completado.
    """
    return crear_notificacion(
        usuario=pago.reserva.cliente.usuario,
        titulo="Pago completado",
        mensaje=(
            f"Se registró un pago de {pago.monto} Bs "
            f"para tu reserva "
            f"{pago.reserva.codigo}. "
            f"Estado: {pago.get_estado_display()}."
        ),
        tipo="pago"
    )
