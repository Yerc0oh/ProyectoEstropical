from django.conf import settings
from django.db import models


class Perfil(models.Model):
    """Datos de persona (clientes y empleados). Correo, contraseña, rol (grupo) y bloqueo
    de cuenta viven en el usuario de Django; aquí solo datos propios del negocio."""

    class TipoDocumento(models.TextChoices):
        CI = "CI", "Cédula de identidad"
        PASAPORTE = "PASAPORTE", "Pasaporte"
        CE = "CE", "Carnet de extranjería"

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name="perfil", db_column="usuario_id")
    nombres = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80)
    tipo_documento = models.CharField(max_length=10, choices=TipoDocumento.choices,
                                      default=TipoDocumento.CI)
    nro_documento = models.CharField("número de documento", max_length=20)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    nacionalidad = models.ForeignKey("destinations.Pais", on_delete=models.PROTECT,
                                     null=True, blank=True, db_column="nacionalidad_id")
    nit = models.CharField(max_length=20, blank=True)
    razon_social = models.CharField(max_length=150, blank=True)
    # Cambio de correo pendiente de verificación. El correo real del usuario
    # (User.email / User.username) no se modifica hasta confirmar el enlace.
    correo_pendiente = models.EmailField(null=True, blank=True)
    # Nonce que invalida los enlaces anteriores en cada nueva solicitud.
    correo_pendiente_nonce = models.CharField(max_length=64, blank=True, default="")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "perfil"
        constraints = [
            models.UniqueConstraint(fields=["tipo_documento", "nro_documento"],
                                    name="uq_perfil_documento"),
        ]

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()
