
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class PreferenciaViaje(models.Model):

    class TipoViaje(models.TextChoices):
        AVENTURA = "aventura", "Aventura"
        CULTURAL = "cultural", "Cultural"
        RELAX = "relax", "Descanso"
        FAMILIAR = "familiar", "Familiar"
        ROMANTICO = "romantico", "Romántico"
        NEGOCIOS = "negocios", "Negocios"
        OTRO = "otro", "Otro"

    cliente = models.ForeignKey(
        "accounts.Perfil",
        on_delete=models.CASCADE,
        related_name="preferencias_viaje"
    )

    nombre = models.CharField(max_length=100)
    tipo_viaje = models.CharField(
        max_length=20,
        choices=TipoViaje.choices
    )

    destinos = models.ManyToManyField(
        "destinations.Destino",
        related_name="preferencias_viaje",
        blank=True
    )

    presupuesto_minimo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    presupuesto_maximo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    duracion_minima = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)]
    )

    duracion_maxima = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)]
    )

    cantidad_personas = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )

    observaciones = models.TextField(
        blank=True,
        max_length=1000
    )

    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "preferencia_viaje"
        ordering = ["-fecha_actualizacion"]
        constraints = [
            models.CheckConstraint(
                condition=Q(presupuesto_minimo__gte=0),
                name="ck_preferencia_presupuesto_min"
            ),
            models.CheckConstraint(
                condition=Q(
                    presupuesto_maximo__gte=F("presupuesto_minimo")
                ),
                name="ck_preferencia_presupuesto_orden"
            ),
            models.CheckConstraint(
                condition=Q(duracion_minima__gte=1),
                name="ck_preferencia_duracion_min"
            ),
            models.CheckConstraint(
                condition=Q(
                    duracion_maxima__gte=F("duracion_minima")
                ),
                name="ck_preferencia_duracion_orden"
            ),
            models.CheckConstraint(
                condition=Q(cantidad_personas__gte=1),
                name="ck_preferencia_personas"
            ),
            models.UniqueConstraint(
                fields=["cliente", "nombre"],
                name="uq_preferencia_cliente_nombre"
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.presupuesto_minimo is not None
            and self.presupuesto_maximo is not None
            and self.presupuesto_minimo > self.presupuesto_maximo
        ):
            raise ValidationError({
                "presupuesto_maximo":
                    "El presupuesto máximo no puede ser menor al mínimo."
            })

        if (
            self.duracion_minima is not None
            and self.duracion_maxima is not None
            and self.duracion_minima > self.duracion_maxima
        ):
            raise ValidationError({
                "duracion_maxima":
                    "La duración máxima no puede ser menor a la mínima."
            })

    def __str__(self):
        return f"{self.nombre} - {self.cliente.nombre_completo}"
