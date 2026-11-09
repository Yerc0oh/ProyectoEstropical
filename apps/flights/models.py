from django.db import models
from django.db.models import F, Q


class Vuelo(models.Model):
    class Estado(models.TextChoices):
        PROGRAMADO = "programado", "Programado"
        RETRASADO = "retrasado", "Retrasado"
        CANCELADO = "cancelado", "Cancelado"
        COMPLETADO = "completado", "Completado"

    proveedor = models.ForeignKey("suppliers.Proveedor", on_delete=models.PROTECT, related_name="vuelos")
    numero_vuelo = models.CharField(max_length=10)
    origen = models.ForeignKey("destinations.Destino", on_delete=models.PROTECT,
                               related_name="vuelos_salida")
    destino = models.ForeignKey("destinations.Destino", on_delete=models.PROTECT,
                                related_name="vuelos_llegada")
    fecha_salida = models.DateTimeField()
    fecha_llegada = models.DateTimeField()
    asientos_total = models.IntegerField()
    asientos_disponibles = models.IntegerField()
    precio_referencial = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PROGRAMADO)

    class Meta:
        db_table = "vuelo"
        ordering = ["fecha_salida"]
        constraints = [
            models.UniqueConstraint(fields=["numero_vuelo", "fecha_salida"], name="uq_vuelo_numero_fecha"),
            models.CheckConstraint(condition=~Q(origen=F("destino")), name="ck_vuelo_origen_destino"),
            models.CheckConstraint(condition=Q(fecha_llegada__gt=F("fecha_salida")), name="ck_vuelo_fechas"),
            models.CheckConstraint(condition=Q(asientos_disponibles__gte=0,
                                               asientos_disponibles__lte=F("asientos_total")),
                                   name="ck_vuelo_asientos"),
        ]

    def __str__(self):
        return f"{self.numero_vuelo} {self.origen.nombre} → {self.destino.nombre}"

    @property
    def asientos_ocupados(self):
        """Asientos ya comprometidos (CU-16). Se derivan de total - disponibles."""
        return self.asientos_total - self.asientos_disponibles
