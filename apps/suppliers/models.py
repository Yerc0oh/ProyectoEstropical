from django.conf import settings
from django.db import models

from .validators import ruta_documento_proveedor, validar_archivo_documento


class Proveedor(models.Model):
    class Tipo(models.TextChoices):
        AEROLINEA = "aerolinea", "Aerolínea"
        HOTEL = "hotel", "Hotel"
        OPERADOR = "operador", "Operador turístico"
        TRANSPORTE = "transporte", "Transporte"
        OTRO = "otro", "Otro"

    class Validacion(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        VALIDADO = "validado", "Validado"
        RECHAZADO = "rechazado", "Rechazado"

    razon_social = models.CharField(max_length=150)
    nit = models.CharField(max_length=20, unique=True)
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    nombre_contacto = models.CharField(max_length=100, blank=True)
    correo = models.EmailField(max_length=120, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    estado_validacion = models.CharField(max_length=10, choices=Validacion.choices,
                                         default=Validacion.PENDIENTE)
    activo = models.BooleanField(default=True)
    # Propietario de la cuenta web que puede cargar y consultar sus documentos.
    # Es nulo para proveedores históricos creados antes de CU-13.
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="proveedor",
                                   verbose_name="usuario del proveedor")

    class Meta:
        db_table = "proveedor"
        verbose_name_plural = "proveedores"
        ordering = ["razon_social"]

    def __str__(self):
        return self.razon_social


class ProveedorDocumento(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"

    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name="documentos")
    tipo_documento = models.CharField(max_length=50)  # NIT, licencia, contrato...
    archivo = models.FileField(upload_to=ruta_documento_proveedor,
                               validators=[validar_archivo_documento])
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    observacion = models.CharField(max_length=250, blank=True)
    revisado_por = models.ForeignKey("accounts.Perfil", on_delete=models.PROTECT, null=True,
                                     blank=True, db_column="revisado_por_id")
    fecha_carga = models.DateTimeField(auto_now_add=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "proveedor_documento"

    def __str__(self):
        return f"{self.tipo_documento} - {self.proveedor}"

# CU-17 (Confirmar servicios reservados): el modelo ConfirmacionProveedor depende de Reserva,
# por eso vive en apps/reservations/models.py (tabla confirmacion_proveedor del schema.sql).
