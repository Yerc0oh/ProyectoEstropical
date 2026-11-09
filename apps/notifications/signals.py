
import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction

from apps.reservations.models import Reserva
from apps.payments.models import Pago

from .services import (
    notificar_reserva,
    notificar_cambio_reserva,
    notificar_pago,
)


logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Reserva)
def guardar_estado_anterior_reserva(sender, instance, **kwargs):
    instance._estado_anterior = None

    if instance.pk:
        instance._estado_anterior = (
            Reserva.objects.filter(pk=instance.pk)
            .values_list("estado", flat=True)
            .first()
        )


@receiver(post_save, sender=Reserva)
def notificacion_automatica_reserva(
    sender, instance, created, **kwargs
):
    if created:
        transaction.on_commit(
            lambda: notificar_reserva(instance)
        )

    elif (
        instance._estado_anterior is not None
        and instance._estado_anterior != instance.estado
    ):
        transaction.on_commit(
            lambda: notificar_cambio_reserva(instance)
        )


@receiver(pre_save, sender=Pago)
def guardar_estado_anterior_pago(sender, instance, **kwargs):
    instance._estado_anterior = None

    if instance.pk:
        instance._estado_anterior = (
            Pago.objects.filter(pk=instance.pk)
            .values_list("estado", flat=True)
            .first()
        )


@receiver(post_save, sender=Pago)
def notificacion_automatica_pago(
    sender, instance, created, **kwargs
):
    estado_anterior = getattr(
        instance, "_estado_anterior", None
    )

    if (
        instance.estado == "completado"
        and (
            created
            or estado_anterior != "completado"
        )
    ):
        transaction.on_commit(
            lambda: notificar_pago(instance)
        )
