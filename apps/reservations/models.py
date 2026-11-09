"""Sprint 3 - Reservas e itinerarios (CU-17 a CU-25).

Tablas del docs/estropical_schema.sql: reserva, pasajero, documento_viaje,
confirmacion_proveedor. Además se crean aquí dos tablas que el schema ubica en el
Sprint 6 pero que las reservas necesitan desde ya:
  * promocion          -> cupones de descuento al reservar (CU-18). La gestión
                          completa (CU-50) queda para el Sprint 6; mientras tanto se
                          administran desde Django admin.
  * parametro_sistema  -> % de penalidad, horas de expiración, cuotas máximas.
"""
import os
import uuid

from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.accounts.models import Perfil


# ---------------------------------------------------------------- Configuración
class ParametroSistema(models.Model):
    clave = models.CharField(max_length=60, primary_key=True)
    valor = models.CharField(max_length=200)
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "parametro_sistema"
        verbose_name = "parámetro del sistema"
        verbose_name_plural = "parámetros del sistema"
        ordering = ["clave"]

    def __str__(self):
        return f"{self.clave} = {self.valor}"

    @classmethod
    def obtener(cls, clave, por_defecto, tipo=int):
        """ParametroSistema.obtener("cuotas_maximas", 6) -> 6 (convertido con `tipo`)."""
        fila = cls.objects.filter(clave=clave).first()
        try:
            return tipo(fila.valor) if fila else por_defecto
        except (TypeError, ValueError):
            return por_defecto


# ---------------------------------------------------------------- Cupones
class Promocion(models.Model):
    class TipoDescuento(models.TextChoices):
        PORCENTAJE = "porcentaje", "Porcentaje"
        MONTO_FIJO = "monto_fijo", "Monto fijo (Bs)"

    codigo = models.CharField(max_length=30, unique=True)
    descripcion = models.CharField(max_length=200, blank=True)
    tipo_descuento = models.CharField(max_length=10, choices=TipoDescuento.choices)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    monto_minimo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField()
    usos_maximos = models.IntegerField(null=True, blank=True, help_text="Vacío = ilimitado")
    paquete = models.ForeignKey("packages.Paquete", on_delete=models.PROTECT, null=True, blank=True,
                                related_name="promociones", help_text="Vacío = aplica a todos")
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "promocion"
        verbose_name = "promoción"
        verbose_name_plural = "promociones"
        ordering = ["-vigente_hasta"]
        constraints = [
            models.CheckConstraint(condition=Q(valor__gt=0), name="ck_promocion_valor"),
            models.CheckConstraint(condition=Q(vigente_hasta__gte=F("vigente_desde")),
                                   name="ck_promocion_vigencia"),
            models.CheckConstraint(condition=~Q(tipo_descuento="porcentaje") | Q(valor__lte=100),
                                   name="ck_promocion_porcentaje"),
            models.CheckConstraint(condition=Q(usos_maximos__isnull=True) | Q(usos_maximos__gt=0),
                                   name="ck_promocion_usos"),
        ]

    def __str__(self):
        return self.codigo


# ---------------------------------------------------------------- Reservas
class Reserva(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADA = "confirmada", "Confirmada"
        CANCELADA = "cancelada", "Cancelada"
        COMPLETADA = "completada", "Completada"
        EXPIRADA = "expirada", "Expirada"

    ACTIVAS = [Estado.PENDIENTE, Estado.CONFIRMADA]   # ocupan cupos (ver trigger trg_reserva_cupos)

    codigo = models.CharField(max_length=12, unique=True)
    cliente = models.ForeignKey(Perfil, on_delete=models.PROTECT, related_name="reservas")
    creada_por = models.ForeignKey(Perfil, on_delete=models.PROTECT, related_name="reservas_creadas")
    paquete = models.ForeignKey("packages.Paquete", on_delete=models.PROTECT, related_name="reservas")
    promocion = models.ForeignKey(Promocion, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="reservas")
    cantidad_pasajeros = models.SmallIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)  # copia del precio al reservar
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Columnas calculadas por PostgreSQL (GENERATED ALWAYS AS ... STORED), como en el schema.
    subtotal = models.GeneratedField(
        expression=F("precio_unitario") * F("cantidad_pasajeros"),
        output_field=models.DecimalField(max_digits=12, decimal_places=2), db_persist=True)
    total = models.GeneratedField(
        expression=F("precio_unitario") * F("cantidad_pasajeros") - F("descuento"),
        output_field=models.DecimalField(max_digits=12, decimal_places=2), db_persist=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    fecha_reserva = models.DateTimeField(default=timezone.now)
    fecha_expiracion = models.DateTimeField(null=True, blank=True)   # límite para pagar
    confirmada_por = models.ForeignKey(Perfil, on_delete=models.PROTECT, null=True, blank=True,
                                       related_name="reservas_confirmadas")
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)
    motivo_cancelacion = models.CharField(max_length=250, blank=True)
    observaciones = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "reserva"
        ordering = ["-fecha_reserva"]
        constraints = [
            models.CheckConstraint(condition=Q(cantidad_pasajeros__gt=0), name="ck_reserva_pasajeros"),
            models.CheckConstraint(condition=Q(precio_unitario__gt=0), name="ck_reserva_precio"),
            models.CheckConstraint(condition=Q(descuento__gte=0), name="ck_reserva_descuento_positivo"),
            models.CheckConstraint(
                condition=Q(descuento__lte=F("precio_unitario") * F("cantidad_pasajeros")),
                name="ck_reserva_descuento_maximo"),
            models.CheckConstraint(
                condition=Q(estado="cancelada", fecha_cancelacion__isnull=False)
                | (~Q(estado="cancelada") & Q(fecha_cancelacion__isnull=True)),
                name="ck_reserva_cancelacion"),
        ]
        indexes = [models.Index(fields=["estado"], name="ix_reserva_estado")]

    def __str__(self):
        return self.codigo

    @staticmethod
    def nuevo_codigo():
        """ET- + 8 caracteres: ET-7F3A9C21 (11 de 12 posibles)."""
        while True:
            codigo = "ET-" + uuid.uuid4().hex[:8].upper()
            if not Reserva.objects.filter(codigo=codigo).exists():
                return codigo

    @property
    def esta_activa(self):
        return self.estado in self.ACTIVAS

    @property
    def ya_salio(self):
        return self.paquete.fecha_salida <= timezone.localdate()

    @property
    def puede_modificarse(self):
        return self.esta_activa and not self.ya_salio

    @property
    def puede_cancelarse(self):
        return self.esta_activa and not self.ya_salio

    @property
    def puede_confirmarse(self):
        return self.estado == self.Estado.PENDIENTE


class Pasajero(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name="pasajeros")
    nombres = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80)
    tipo_documento = models.CharField(max_length=10, choices=Perfil.TipoDocumento.choices,
                                      default=Perfil.TipoDocumento.CI)
    nro_documento = models.CharField("número de documento", max_length=20)
    fecha_nacimiento = models.DateField()
    nacionalidad = models.ForeignKey("destinations.Pais", on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        db_table = "pasajero"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["reserva", "tipo_documento", "nro_documento"],
                                    name="uq_pasajero_documento"),
        ]

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"


def _ruta_documento(instancia, nombre):
    """Nombre aleatorio: los documentos de viaje (pasaportes, visas) no deben poder adivinarse."""
    extension = os.path.splitext(nombre)[1].lower()
    return f"documentos_viaje/{uuid.uuid4().hex}{extension}"


class DocumentoViaje(models.Model):
    class Tipo(models.TextChoices):
        PASAPORTE = "pasaporte", "Pasaporte"
        VISA = "visa", "Visa"
        CI = "ci", "Cédula de identidad"
        VACUNACION = "vacunacion", "Certificado de vacunación"
        OTRO = "otro", "Otro"

    pasajero = models.ForeignKey(Pasajero, on_delete=models.CASCADE, related_name="documentos")
    tipo = models.CharField(max_length=25, choices=Tipo.choices)
    numero = models.CharField("número", max_length=40, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    archivo = models.FileField(upload_to=_ruta_documento, max_length=255)
    fecha_carga = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documento_viaje"
        ordering = ["fecha_carga"]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.pasajero}"

    @property
    def vencido(self):
        return bool(self.fecha_vencimiento and self.fecha_vencimiento < timezone.localdate())


# ---------------------------------------------------------------- CU-17
class ConfirmacionProveedor(models.Model):
    """Solicitud de confirmación de un servicio (vuelo, hotel) al proveedor de una reserva.
    No es lo mismo que confirmar la reserva del cliente (CU-22)."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADA = "confirmada", "Confirmada"
        RECHAZADA = "rechazada", "Rechazada"

    reserva = models.ForeignKey(Reserva, on_delete=models.PROTECT, related_name="confirmaciones_proveedor")
    proveedor = models.ForeignKey("suppliers.Proveedor", on_delete=models.PROTECT,
                                  related_name="confirmaciones")
    concepto = models.CharField(max_length=200)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    codigo_confirmacion = models.CharField("código de confirmación", max_length=50, blank=True)
    gestionado_por = models.ForeignKey(Perfil, on_delete=models.PROTECT, null=True, blank=True,
                                       related_name="confirmaciones_gestionadas")
    fecha_solicitud = models.DateTimeField(default=timezone.now)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    observacion = models.CharField(max_length=250, blank=True)

    class Meta:
        db_table = "confirmacion_proveedor"
        verbose_name = "confirmación de proveedor"
        verbose_name_plural = "confirmaciones de proveedores"
        ordering = ["-fecha_solicitud"]
        constraints = [
            models.UniqueConstraint(fields=["reserva", "proveedor", "concepto"],
                                    name="uq_confirmacion_proveedor"),
        ]

    def __str__(self):
        return f"{self.reserva} - {self.concepto}"
