"""Sprint 4 - Pagos, facturación y caja (CU-26 a CU-37).

Tablas del docs/estropical_schema.sql: cierre_caja, cuota, pago, reembolso, factura,
pago_proveedor, más la vista v_saldo_reserva (modelo de solo lectura SaldoReserva).

El sistema NO procesa pagos reales ni guarda datos de tarjetas (alcance del proyecto y
RNF-05): los pagos en línea pasan por una pasarela simulada (services.pasarela_simulada).
"""
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.accounts.models import Perfil
from apps.reservations.models import ConfirmacionProveedor, Reserva


class Metodo(models.TextChoices):
    QR = "qr", "Código QR"
    TARJETA = "tarjeta", "Tarjeta"
    EFECTIVO = "efectivo", "Efectivo"
    TRANSFERENCIA = "transferencia", "Transferencia"


class CierreCaja(models.Model):                                           # CU-37
    fecha = models.DateField(unique=True)
    total_ingresos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_egresos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo = models.GeneratedField(
        expression=F("total_ingresos") - F("total_egresos"),
        output_field=models.DecimalField(max_digits=12, decimal_places=2), db_persist=True)
    realizado_por = models.ForeignKey(Perfil, on_delete=models.PROTECT, related_name="cierres_caja")
    fecha_cierre = models.DateTimeField(default=timezone.now)
    observaciones = models.CharField(max_length=250, blank=True)

    class Meta:
        db_table = "cierre_caja"
        verbose_name = "cierre de caja"
        verbose_name_plural = "cierres de caja"
        ordering = ["-fecha"]

    def __str__(self):
        return f"Cierre {self.fecha:%d/%m/%Y}"


class Cuota(models.Model):                                                # CU-27
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PAGADA = "pagada", "Pagada"
        ANULADA = "anulada", "Anulada"

    reserva = models.ForeignKey(Reserva, on_delete=models.PROTECT, related_name="cuotas")
    numero = models.SmallIntegerField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)

    class Meta:
        db_table = "cuota"
        ordering = ["reserva", "numero"]
        constraints = [
            models.UniqueConstraint(fields=["reserva", "numero"], name="uq_cuota_reserva_numero"),
            models.CheckConstraint(condition=Q(numero__gt=0), name="ck_cuota_numero"),
            models.CheckConstraint(condition=Q(monto__gt=0), name="ck_cuota_monto"),
        ]

    def __str__(self):
        return f"Cuota {self.numero} de {self.reserva}"

    @property
    def vencida(self):
        """'Vencida' no se guarda: es pendiente con fecha pasada (igual que en v_saldo_reserva)."""
        return self.estado == self.Estado.PENDIENTE and self.fecha_vencimiento < timezone.localdate()


class Pago(models.Model):                                                 # CU-26, CU-28, CU-34
    class Canal(models.TextChoices):
        EN_LINEA = "en_linea", "En línea"
        VENTANILLA = "ventanilla", "Ventanilla"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        COMPLETADO = "completado", "Completado"
        FALLIDO = "fallido", "Fallido"
        REEMBOLSADO = "reembolsado", "Reembolsado"

    reserva = models.ForeignKey(Reserva, on_delete=models.PROTECT, related_name="pagos")
    cuota = models.ForeignKey(Cuota, on_delete=models.PROTECT, null=True, blank=True, related_name="pagos")
    metodo = models.CharField(max_length=15, choices=Metodo.choices)
    canal = models.CharField(max_length=10, choices=Canal.choices)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    fecha_pago = models.DateTimeField(default=timezone.now)
    # null (no '') cuando no hay valor, para no chocar con UNIQUE
    referencia_transaccion = models.CharField(max_length=100, unique=True, null=True, blank=True)
    nro_comprobante = models.CharField(max_length=20, unique=True, null=True, blank=True)
    registrado_por = models.ForeignKey(Perfil, on_delete=models.PROTECT, null=True, blank=True,
                                       related_name="pagos_registrados")
    conciliado = models.BooleanField(default=False)
    fecha_conciliacion = models.DateField(null=True, blank=True)
    conciliado_por = models.ForeignKey(Perfil, on_delete=models.PROTECT, null=True, blank=True,
                                       related_name="pagos_conciliados")
    cierre_caja = models.ForeignKey(CierreCaja, on_delete=models.PROTECT, null=True, blank=True,
                                    related_name="pagos")

    class Meta:
        db_table = "pago"
        ordering = ["-fecha_pago"]
        constraints = [
            models.CheckConstraint(condition=Q(monto__gt=0), name="ck_pago_monto"),
            models.CheckConstraint(condition=~Q(canal="ventanilla") | Q(registrado_por__isnull=False),
                                   name="ck_pago_ventanilla_cajero"),
            models.CheckConstraint(
                condition=Q(conciliado=True, fecha_conciliacion__isnull=False)
                | Q(conciliado=False, fecha_conciliacion__isnull=True),
                name="ck_pago_conciliacion"),
        ]
        indexes = [models.Index(fields=["fecha_pago"], name="ix_pago_fecha")]

    def __str__(self):
        return self.nro_comprobante or f"Pago {self.pk}"


class Reembolso(models.Model):                                            # CU-21, CU-33
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PROCESADO = "procesado", "Procesado"
        RECHAZADO = "rechazado", "Rechazado"

    reserva = models.ForeignKey(Reserva, on_delete=models.PROTECT, related_name="reembolsos")
    pago = models.ForeignKey(Pago, on_delete=models.PROTECT, related_name="reembolsos")
    penalidad = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_reembolso = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    metodo = models.CharField(max_length=15, choices=Metodo.choices, blank=True)
    referencia = models.CharField(max_length=100, blank=True)
    fecha_solicitud = models.DateTimeField(default=timezone.now)
    fecha_procesado = models.DateTimeField(null=True, blank=True)
    procesado_por = models.ForeignKey(Perfil, on_delete=models.PROTECT, null=True, blank=True,
                                      related_name="reembolsos_procesados")
    cierre_caja = models.ForeignKey(CierreCaja, on_delete=models.PROTECT, null=True, blank=True,
                                    related_name="reembolsos")

    class Meta:
        db_table = "reembolso"
        ordering = ["-fecha_solicitud"]
        constraints = [
            models.CheckConstraint(condition=Q(penalidad__gte=0), name="ck_reembolso_penalidad"),
            models.CheckConstraint(condition=Q(monto_reembolso__gte=0), name="ck_reembolso_monto"),
        ]

    def __str__(self):
        return f"Reembolso {self.pk} de {self.reserva}"


class Factura(models.Model):                                              # CU-30, CU-31, CU-32
    class Estado(models.TextChoices):
        EMITIDA = "emitida", "Emitida"
        ANULADA = "anulada", "Anulada"

    nro_factura = models.BigIntegerField(unique=True)
    reserva = models.ForeignKey(Reserva, on_delete=models.PROTECT, related_name="facturas")
    nit_cliente = models.CharField("NIT / CI", max_length=20)     # copia de los datos al emitir
    razon_social = models.CharField(max_length=150)
    concepto = models.CharField(max_length=250)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.EMITIDA)
    archivo_pdf = models.CharField(max_length=255, blank=True)  # el PDF se genera al descargar
    fecha_emision = models.DateTimeField(default=timezone.now)
    emitida_por = models.ForeignKey(Perfil, on_delete=models.PROTECT, related_name="facturas_emitidas")
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    anulada_por = models.ForeignKey(Perfil, on_delete=models.PROTECT, null=True, blank=True,
                                    related_name="facturas_anuladas")
    motivo_anulacion = models.CharField(max_length=250, blank=True)

    class Meta:
        db_table = "factura"
        ordering = ["-nro_factura"]
        constraints = [
            models.CheckConstraint(condition=Q(monto__gt=0), name="ck_factura_monto"),
            models.CheckConstraint(
                condition=Q(estado="anulada", fecha_anulacion__isnull=False)
                | (~Q(estado="anulada") & Q(fecha_anulacion__isnull=True)),
                name="ck_factura_anulacion"),
        ]

    def __str__(self):
        return f"Factura N° {self.nro_factura}"


class PagoProveedor(models.Model):                                        # CU-36
    class MetodoProveedor(models.TextChoices):
        TRANSFERENCIA = "transferencia", "Transferencia"
        EFECTIVO = "efectivo", "Efectivo"
        CHEQUE = "cheque", "Cheque"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PAGADO = "pagado", "Pagado"

    proveedor = models.ForeignKey("suppliers.Proveedor", on_delete=models.PROTECT, related_name="pagos")
    confirmacion = models.ForeignKey(ConfirmacionProveedor, on_delete=models.PROTECT, null=True, blank=True,
                                     related_name="pagos", help_text="Servicio confirmado que se paga (opcional)")
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    metodo = models.CharField(max_length=15, choices=MetodoProveedor.choices)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    fecha_pago = models.DateTimeField(default=timezone.now)
    referencia = models.CharField(max_length=100, blank=True)
    registrado_por = models.ForeignKey(Perfil, on_delete=models.PROTECT, related_name="pagos_proveedor")
    cierre_caja = models.ForeignKey(CierreCaja, on_delete=models.PROTECT, null=True, blank=True,
                                    related_name="pagos_proveedor")
    observacion = models.CharField(max_length=250, blank=True)

    class Meta:
        db_table = "pago_proveedor"
        verbose_name = "pago a proveedor"
        verbose_name_plural = "pagos a proveedores"
        ordering = ["-fecha_pago"]
        constraints = [models.CheckConstraint(condition=Q(monto__gt=0), name="ck_pago_proveedor_monto")]

    def __str__(self):
        return f"{self.proveedor} - Bs {self.monto}"


class SaldoReserva(models.Model):                                         # CU-29, CU-35
    """Vista v_saldo_reserva (solo lectura). Cuentas por cobrar = saldo_pendiente > 0."""
    reserva = models.OneToOneField(Reserva, on_delete=models.DO_NOTHING, primary_key=True,
                                   related_name="saldo", db_column="reserva_id")
    codigo = models.CharField(max_length=12)
    cliente = models.ForeignKey(Perfil, on_delete=models.DO_NOTHING, related_name="+", db_column="cliente_id")
    estado = models.CharField(max_length=10)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    pagado = models.DecimalField(max_digits=12, decimal_places=2)
    reembolsado = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_pendiente = models.DecimalField(max_digits=12, decimal_places=2)
    cuotas_vencidas = models.IntegerField()

    class Meta:
        managed = False
        db_table = "v_saldo_reserva"
