
from django.db import models
from django.conf import settings


class Notificacion(models.Model):

    TIPOS = [
        ("reserva", "Reserva"),
        ("pago", "Pago"),
        ("promocion", "Promoción"),
        ("sistema", "Sistema"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificaciones"
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        default="sistema"
    )

    titulo = models.CharField(max_length=150)

    mensaje = models.TextField()

    url = models.CharField(
        max_length=255,
        blank=True
    )

    leida = models.BooleanField(default=False)

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"

    def __str__(self):
        return f"{self.usuario} - {self.titulo}"
