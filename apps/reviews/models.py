
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Resena(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("aprobada", "Aprobada"),
        ("rechazada", "Rechazada"),
    ]

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resenas"
    )

    paquete = models.ForeignKey(
        "packages.Paquete",
        on_delete=models.CASCADE,
        related_name="resenas"
    )

    calificacion = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )

    comentario = models.TextField(max_length=1500)

    estado = models.CharField(
        max_length=12,
        choices=ESTADOS,
        default="pendiente"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "paquete"],
                name="resena_unica_cliente_paquete"
            )
        ]

    def __str__(self):
        return f"{self.cliente} - {self.paquete} ({self.calificacion}/5)"
