
from django.conf import settings
from django.db import models
from django.utils import timezone


class Ticket(models.Model):

    CATEGORIAS = [
        ("consulta", "Consulta general"),
        ("reserva", "Problema con reserva"),
        ("pago", "Consulta sobre pago"),
        ("reclamo", "Reclamo"),
        ("otro", "Otro"),
    ]

    PRIORIDADES = [
        ("baja", "Baja"),
        ("media", "Media"),
        ("alta", "Alta"),
    ]

    ESTADOS = [
        ("abierto", "Abierto"),
        ("en_proceso", "En proceso"),
        ("resuelto", "Resuelto"),
        ("cerrado", "Cerrado"),
    ]

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tickets_soporte",
    )

    asunto = models.CharField(max_length=180)

    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIAS,
        default="consulta",
    )

    descripcion = models.TextField()

    prioridad = models.CharField(
        max_length=10,
        choices=PRIORIDADES,
        default="media",
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="abierto",
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "Ticket de soporte"
        verbose_name_plural = "Tickets de soporte"

    def __str__(self):
        return f"Ticket #{self.pk} - {self.asunto}"

    def save(self, *args, **kwargs):
        if self.estado == "cerrado" and not self.fecha_cierre:
            self.fecha_cierre = timezone.now()
        elif self.estado != "cerrado":
            self.fecha_cierre = None

        super().save(*args, **kwargs)


class RespuestaTicket(models.Model):

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="respuestas",
    )

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="respuestas_soporte",
    )

    mensaje = models.TextField()

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["fecha_creacion"]
        verbose_name = "Respuesta de ticket"
        verbose_name_plural = "Respuestas de tickets"

    def __str__(self):
        return f"Respuesta #{self.pk} - Ticket #{self.ticket_id}"
