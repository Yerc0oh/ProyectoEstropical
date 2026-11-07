from django.db import models
from django.db.models import F, Q


class Servicio(models.Model):
    """Catálogo de servicios incluibles: traslado, desayuno, guía..."""
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "servicio"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Paquete(models.Model):
    """Un paquete = UNA salida con fechas concretas (otra fecha = otro paquete)."""

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        PUBLICADO = "publicado", "Publicado"
        ARCHIVADO = "archivado", "Archivado"

    destino = models.ForeignKey("destinations.Destino", on_delete=models.PROTECT, related_name="paquetes")
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    condiciones = models.TextField(blank=True)
    fecha_salida = models.DateField()
    fecha_retorno = models.DateField()
    precio_persona = models.DecimalField("precio por persona (Bs)", max_digits=12, decimal_places=2)
    cupos_total = models.IntegerField()
    cupos_disponibles = models.IntegerField()
    venta_desde = models.DateField()
    venta_hasta = models.DateField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.BORRADOR)

    hoteles = models.ManyToManyField("hotels.TipoHabitacion", through="PaqueteHotel", blank=True)
    vuelos = models.ManyToManyField("flights.Vuelo", through="PaqueteVuelo", blank=True)
    servicios = models.ManyToManyField(Servicio, through="PaqueteServicio", blank=True)

    class Meta:
        db_table = "paquete"
        ordering = ["fecha_salida"]
        constraints = [
            models.CheckConstraint(condition=Q(fecha_retorno__gte=F("fecha_salida")), name="ck_paquete_fechas"),
            models.CheckConstraint(condition=Q(venta_hasta__gte=F("venta_desde"),
                                               venta_hasta__lte=F("fecha_salida")), name="ck_paquete_venta"),
            models.CheckConstraint(condition=Q(cupos_disponibles__gte=0,
                                               cupos_disponibles__lte=F("cupos_total")),
                                   name="ck_paquete_cupos"),
            models.CheckConstraint(condition=Q(precio_persona__gt=0), name="ck_paquete_precio"),
        ]

    def __str__(self):
        return self.nombre

    @property
    def duracion_dias(self):
        return (self.fecha_retorno - self.fecha_salida).days + 1

    def save(self, *args, **kwargs):
        if self._state.adding and self.cupos_disponibles is None:
            self.cupos_disponibles = self.cupos_total
        super().save(*args, **kwargs)


class PaqueteHotel(models.Model):
    paquete = models.ForeignKey(Paquete, on_delete=models.CASCADE)
    tipo_habitacion = models.ForeignKey("hotels.TipoHabitacion", on_delete=models.PROTECT)
    noches = models.SmallIntegerField()

    class Meta:
        db_table = "paquete_hotel"
        constraints = [models.UniqueConstraint(fields=["paquete", "tipo_habitacion"], name="uq_paquete_hotel")]


class PaqueteVuelo(models.Model):
    class Tramo(models.TextChoices):
        IDA = "ida", "Ida"
        VUELTA = "vuelta", "Vuelta"
        INTERNO = "interno", "Interno"

    paquete = models.ForeignKey(Paquete, on_delete=models.CASCADE)
    vuelo = models.ForeignKey("flights.Vuelo", on_delete=models.PROTECT)
    tramo = models.CharField(max_length=10, choices=Tramo.choices, default=Tramo.IDA)

    class Meta:
        db_table = "paquete_vuelo"
        constraints = [models.UniqueConstraint(fields=["paquete", "vuelo"], name="uq_paquete_vuelo")]


class PaqueteServicio(models.Model):
    paquete = models.ForeignKey(Paquete, on_delete=models.CASCADE)
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT)
    detalle = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "paquete_servicio"
        constraints = [models.UniqueConstraint(fields=["paquete", "servicio"], name="uq_paquete_servicio")]


class PaqueteActividad(models.Model):
    """Cronograma base del itinerario (CU-25, Sprint 3 genera el PDF)."""
    paquete = models.ForeignKey(Paquete, on_delete=models.CASCADE, related_name="actividades")
    dia = models.SmallIntegerField()
    orden = models.SmallIntegerField(default=1)
    hora_inicio = models.TimeField(null=True, blank=True)
    titulo = models.CharField(max_length=120)
    descripcion = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "paquete_actividad"
        ordering = ["dia", "orden"]
        verbose_name_plural = "actividades del paquete"
        constraints = [models.UniqueConstraint(fields=["paquete", "dia", "orden"], name="uq_paquete_actividad")]
