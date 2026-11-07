from django.db import models
from django.db.models import Q


class Pais(models.Model):
    codigo_iso = models.CharField(max_length=2, unique=True)
    nombre = models.CharField(max_length=80, unique=True)

    class Meta:
        db_table = "pais"
        verbose_name_plural = "países"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "categoria"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Destino(models.Model):
    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, related_name="destinos")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="destinos")
    nombre = models.CharField(max_length=100)
    codigo_iata = models.CharField("código IATA", max_length=3, unique=True, null=True, blank=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)  # "eliminar" = desactivar

    class Meta:
        db_table = "destino"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["pais", "nombre"], name="uq_destino_pais_nombre"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.pais.nombre})"

    @property
    def es_internacional(self):
        # TODO: parametrizar el país local si la agencia opera en otro.
        return self.pais.codigo_iso != "BO"

    @property
    def portada(self):
        return self.fotos.filter(es_portada=True).first() or self.fotos.first()


class DestinoFoto(models.Model):
    destino = models.ForeignKey(Destino, on_delete=models.CASCADE, related_name="fotos")
    archivo = models.ImageField(upload_to="destinos/")
    descripcion = models.CharField(max_length=200, blank=True)
    orden = models.SmallIntegerField(default=0)
    es_portada = models.BooleanField(default=False)

    class Meta:
        db_table = "destino_foto"
        ordering = ["orden", "id"]
        constraints = [
            models.UniqueConstraint(fields=["destino"], condition=Q(es_portada=True),
                                    name="uq_destino_foto_portada"),
        ]

    def __str__(self):
        return f"Foto de {self.destino.nombre}"
