# Sprint 4 - tablas: cierre_caja, cuota, pago, reembolso, factura, pago_proveedor
# (ver docs/estropical_schema.sql). SaldoReserva es la vista v_saldo_reserva (managed=False,
# se crea con SQL en 0002).

import django.db.models.deletion
import django.db.models.expressions
import django.utils.timezone
from django.db import migrations, models

METODOS = [("qr", "Código QR"), ("tarjeta", "Tarjeta"), ("efectivo", "Efectivo"), ("transferencia", "Transferencia")]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        ("reservations", "0001_initial"),
        ("suppliers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CierreCaja",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateField(unique=True)),
                ("total_ingresos", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("total_egresos", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("saldo", models.GeneratedField(
                    db_persist=True,
                    expression=django.db.models.expressions.CombinedExpression(
                        models.F("total_ingresos"), "-", models.F("total_egresos")),
                    output_field=models.DecimalField(decimal_places=2, max_digits=12))),
                ("fecha_cierre", models.DateTimeField(default=django.utils.timezone.now)),
                ("observaciones", models.CharField(blank=True, max_length=250)),
                ("realizado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                    related_name="cierres_caja", to="accounts.perfil")),
            ],
            options={
                "verbose_name": "cierre de caja",
                "verbose_name_plural": "cierres de caja",
                "db_table": "cierre_caja",
                "ordering": ["-fecha"],
            },
        ),
        migrations.CreateModel(
            name="Cuota",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero", models.SmallIntegerField()),
                ("monto", models.DecimalField(decimal_places=2, max_digits=12)),
                ("fecha_vencimiento", models.DateField()),
                ("estado", models.CharField(
                    choices=[("pendiente", "Pendiente"), ("pagada", "Pagada"), ("anulada", "Anulada")],
                    default="pendiente", max_length=10)),
                ("reserva", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                              related_name="cuotas", to="reservations.reserva")),
            ],
            options={
                "db_table": "cuota",
                "ordering": ["reserva", "numero"],
                "constraints": [
                    models.UniqueConstraint(fields=("reserva", "numero"), name="uq_cuota_reserva_numero"),
                    models.CheckConstraint(condition=models.Q(("numero__gt", 0)), name="ck_cuota_numero"),
                    models.CheckConstraint(condition=models.Q(("monto__gt", 0)), name="ck_cuota_monto"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Pago",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("metodo", models.CharField(choices=METODOS, max_length=15)),
                ("canal", models.CharField(choices=[("en_linea", "En línea"), ("ventanilla", "Ventanilla")],
                                           max_length=10)),
                ("monto", models.DecimalField(decimal_places=2, max_digits=12)),
                ("estado", models.CharField(
                    choices=[("pendiente", "Pendiente"), ("completado", "Completado"), ("fallido", "Fallido"),
                             ("reembolsado", "Reembolsado")],
                    default="pendiente", max_length=12)),
                ("fecha_pago", models.DateTimeField(default=django.utils.timezone.now)),
                ("referencia_transaccion", models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ("nro_comprobante", models.CharField(blank=True, max_length=20, null=True, unique=True)),
                ("conciliado", models.BooleanField(default=False)),
                ("fecha_conciliacion", models.DateField(blank=True, null=True)),
                ("cierre_caja", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                                  related_name="pagos", to="payments.cierrecaja")),
                ("conciliado_por", models.ForeignKey(blank=True, null=True,
                                                     on_delete=django.db.models.deletion.PROTECT,
                                                     related_name="pagos_conciliados", to="accounts.perfil")),
                ("cuota", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                            related_name="pagos", to="payments.cuota")),
                ("registrado_por", models.ForeignKey(blank=True, null=True,
                                                     on_delete=django.db.models.deletion.PROTECT,
                                                     related_name="pagos_registrados", to="accounts.perfil")),
                ("reserva", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                              related_name="pagos", to="reservations.reserva")),
            ],
            options={
                "db_table": "pago",
                "ordering": ["-fecha_pago"],
                "indexes": [models.Index(fields=["fecha_pago"], name="ix_pago_fecha")],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(("monto__gt", 0)), name="ck_pago_monto"),
                    models.CheckConstraint(
                        condition=models.Q(models.Q(("canal", "ventanilla"), _negated=True),
                                           ("registrado_por__isnull", False), _connector="OR"),
                        name="ck_pago_ventanilla_cajero"),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("conciliado", True), ("fecha_conciliacion__isnull", False)),
                            models.Q(("conciliado", False), ("fecha_conciliacion__isnull", True)),
                            _connector="OR"),
                        name="ck_pago_conciliacion"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Reembolso",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("penalidad", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("monto_reembolso", models.DecimalField(decimal_places=2, max_digits=12)),
                ("estado", models.CharField(
                    choices=[("pendiente", "Pendiente"), ("procesado", "Procesado"), ("rechazado", "Rechazado")],
                    default="pendiente", max_length=10)),
                ("metodo", models.CharField(blank=True, choices=METODOS, max_length=15)),
                ("referencia", models.CharField(blank=True, max_length=100)),
                ("fecha_solicitud", models.DateTimeField(default=django.utils.timezone.now)),
                ("fecha_procesado", models.DateTimeField(blank=True, null=True)),
                ("cierre_caja", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                                  related_name="reembolsos", to="payments.cierrecaja")),
                ("pago", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                           related_name="reembolsos", to="payments.pago")),
                ("procesado_por", models.ForeignKey(blank=True, null=True,
                                                    on_delete=django.db.models.deletion.PROTECT,
                                                    related_name="reembolsos_procesados", to="accounts.perfil")),
                ("reserva", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                              related_name="reembolsos", to="reservations.reserva")),
            ],
            options={
                "db_table": "reembolso",
                "ordering": ["-fecha_solicitud"],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(("penalidad__gte", 0)), name="ck_reembolso_penalidad"),
                    models.CheckConstraint(condition=models.Q(("monto_reembolso__gte", 0)),
                                           name="ck_reembolso_monto"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Factura",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nro_factura", models.BigIntegerField(unique=True)),
                ("nit_cliente", models.CharField(max_length=20, verbose_name="NIT / CI")),
                ("razon_social", models.CharField(max_length=150)),
                ("concepto", models.CharField(max_length=250)),
                ("monto", models.DecimalField(decimal_places=2, max_digits=12)),
                ("estado", models.CharField(choices=[("emitida", "Emitida"), ("anulada", "Anulada")],
                                            default="emitida", max_length=10)),
                ("archivo_pdf", models.CharField(blank=True, max_length=255)),
                ("fecha_emision", models.DateTimeField(default=django.utils.timezone.now)),
                ("fecha_anulacion", models.DateTimeField(blank=True, null=True)),
                ("motivo_anulacion", models.CharField(blank=True, max_length=250)),
                ("anulada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                                  related_name="facturas_anuladas", to="accounts.perfil")),
                ("emitida_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                  related_name="facturas_emitidas", to="accounts.perfil")),
                ("reserva", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                              related_name="facturas", to="reservations.reserva")),
            ],
            options={
                "db_table": "factura",
                "ordering": ["-nro_factura"],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(("monto__gt", 0)), name="ck_factura_monto"),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("estado", "anulada"), ("fecha_anulacion__isnull", False)),
                            models.Q(models.Q(("estado", "anulada"), _negated=True),
                                     ("fecha_anulacion__isnull", True)),
                            _connector="OR"),
                        name="ck_factura_anulacion"),
                ],
            },
        ),
        migrations.CreateModel(
            name="PagoProveedor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("monto", models.DecimalField(decimal_places=2, max_digits=12)),
                ("metodo", models.CharField(
                    choices=[("transferencia", "Transferencia"), ("efectivo", "Efectivo"), ("cheque", "Cheque")],
                    max_length=15)),
                ("estado", models.CharField(choices=[("pendiente", "Pendiente"), ("pagado", "Pagado")],
                                            default="pendiente", max_length=10)),
                ("fecha_pago", models.DateTimeField(default=django.utils.timezone.now)),
                ("referencia", models.CharField(blank=True, max_length=100)),
                ("observacion", models.CharField(blank=True, max_length=250)),
                ("cierre_caja", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                                  related_name="pagos_proveedor", to="payments.cierrecaja")),
                ("confirmacion", models.ForeignKey(blank=True, help_text="Servicio confirmado que se paga (opcional)",
                                                   null=True, on_delete=django.db.models.deletion.PROTECT,
                                                   related_name="pagos", to="reservations.confirmacionproveedor")),
                ("proveedor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                related_name="pagos", to="suppliers.proveedor")),
                ("registrado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                     related_name="pagos_proveedor", to="accounts.perfil")),
            ],
            options={
                "verbose_name": "pago a proveedor",
                "verbose_name_plural": "pagos a proveedores",
                "db_table": "pago_proveedor",
                "ordering": ["-fecha_pago"],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(("monto__gt", 0)), name="ck_pago_proveedor_monto"),
                ],
            },
        ),
        migrations.CreateModel(
            name="SaldoReserva",
            fields=[
                ("reserva", models.OneToOneField(db_column="reserva_id", on_delete=django.db.models.deletion.DO_NOTHING,
                                                 primary_key=True, related_name="saldo", serialize=False,
                                                 to="reservations.reserva")),
                ("codigo", models.CharField(max_length=12)),
                ("estado", models.CharField(max_length=10)),
                ("total", models.DecimalField(decimal_places=2, max_digits=12)),
                ("pagado", models.DecimalField(decimal_places=2, max_digits=12)),
                ("reembolsado", models.DecimalField(decimal_places=2, max_digits=12)),
                ("saldo_pendiente", models.DecimalField(decimal_places=2, max_digits=12)),
                ("cuotas_vencidas", models.IntegerField()),
                ("cliente", models.ForeignKey(db_column="cliente_id", on_delete=django.db.models.deletion.DO_NOTHING,
                                              related_name="+", to="accounts.perfil")),
            ],
            options={
                "db_table": "v_saldo_reserva",
                "managed": False,
            },
        ),
    ]
