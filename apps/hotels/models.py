from django.db import models
from django.db.models import F, Q


class Hotel(models.Model):
    proveedor = models.ForeignKey("suppliers.Proveedor", on_delete=models.PROTECT, related_name="hoteles")
    destino = models.ForeignKey("destinations.Destino", on_delete=models.PROTECT, related_name="hoteles")
    nombre = models.CharField(max_length=120)
    estrellas = models.SmallIntegerField()
    direccion = models.CharField(max_length=200, blank=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "hotel"
        ordering = ["nombre"]
        constraints = [models.CheckConstraint(condition=Q(estrellas__gte=1, estrellas__lte=5),
                                              name="ck_hotel_estrellas")]

    def __str__(self):
        return self.nombre


class TipoHabitacion(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="tipos_habitacion")
    nombre = models.CharField(max_length=60)  # Simple, Doble, Suite...
    capacidad = models.SmallIntegerField()
    habitaciones_total = models.IntegerField()
    habitaciones_disponibles = models.IntegerField()
    descripcion = models.CharField(max_length=250, blank=True)

    class Meta:
        db_table = "tipo_habitacion"
        verbose_name_plural = "tipos de habitación"
        constraints = [
            models.UniqueConstraint(fields=["hotel", "nombre"], name="uq_tipo_habitacion_hotel"),
            models.CheckConstraint(condition=Q(habitaciones_disponibles__gte=0,
                                               habitaciones_disponibles__lte=F("habitaciones_total")),
                                   name="ck_habitaciones_disponibles"),
        ]

    def __str__(self):
        return f"{self.hotel} - {self.nombre}"

    @property
    def habitaciones_ocupadas(self):
        """Habitaciones ya comprometidas (CU-16): total - disponibles."""
        return self.habitaciones_total - self.habitaciones_disponibles


class TarifaHabitacion(models.Model):
    tipo_habitacion = models.ForeignKey(TipoHabitacion, on_delete=models.CASCADE, related_name="tarifas")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    precio_noche = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "tarifa_habitacion"
        constraints = [
            models.UniqueConstraint(fields=["tipo_habitacion", "fecha_inicio"], name="uq_tarifa_inicio"),
            models.CheckConstraint(condition=Q(fecha_fin__gte=F("fecha_inicio")), name="ck_tarifa_fechas"),
        ]
