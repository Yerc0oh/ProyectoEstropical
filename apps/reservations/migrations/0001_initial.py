# Sprint 3 - tablas: parametro_sistema, promocion, reserva, pasajero, documento_viaje,
# confirmacion_proveedor (ver docs/estropical_schema.sql)

import django.db.models.deletion
import django.db.models.expressions
import django.utils.timezone
from django.db import migrations, models

import apps.reservations.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        ("destinations", "0001_initial"),
        ("packages", "0001_initial"),
        ("suppliers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ParametroSistema",
            fields=[
                ("clave", models.CharField(max_length=60, primary_key=True, serialize=False)),
                ("valor", models.CharField(max_length=200)),
                ("descripcion", models.CharField(blank=True, max_length=200)),
            ],
            options={
                "verbose_name": "parámetro del sistema",
                "verbose_name_plural": "parámetros del sistema",
                "db_table": "parametro_sistema",
                "ordering": ["clave"],
            },
        ),
        migrations.CreateModel(
            name="Promocion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=30, unique=True)),
                ("descripcion", models.CharField(blank=True, max_length=200)),
                ("tipo_descuento", models.CharField(
                    choices=[("porcentaje", "Porcentaje"), ("monto_fijo", "Monto fijo (Bs)")], max_length=10)),
                ("valor", models.DecimalField(decimal_places=2, max_digits=10)),
                ("monto_minimo", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("vigente_desde", models.DateField()),
                ("vigente_hasta", models.DateField()),
                ("usos_maximos", models.IntegerField(blank=True, help_text="Vacío = ilimitado", null=True)),
                ("activo", models.BooleanField(default=True)),
                ("paquete", models.ForeignKey(
                    blank=True, help_text="Vacío = aplica a todos", null=True,
                    on_delete=django.db.models.deletion.PROTECT, related_name="promociones",
                    to="packages.paquete")),
            ],
            options={
                "verbose_name": "promoción",
                "verbose_name_plural": "promociones",
                "db_table": "promocion",
                "ordering": ["-vigente_hasta"],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(("valor__gt", 0)), name="ck_promocion_valor"),
                    models.CheckConstraint(condition=models.Q(("vigente_hasta__gte", models.F("vigente_desde"))),
                                           name="ck_promocion_vigencia"),
                    models.CheckConstraint(
                        condition=models.Q(models.Q(("tipo_descuento", "porcentaje"), _negated=True),
                                           ("valor__lte", 100), _connector="OR"),
                        name="ck_promocion_porcentaje"),
                    models.CheckConstraint(
                        condition=models.Q(("usos_maximos__isnull", True), ("usos_maximos__gt", 0), _connector="OR"),
                        name="ck_promocion_usos"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Reserva",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=12, unique=True)),
                ("cantidad_pasajeros", models.SmallIntegerField()),
                ("precio_unitario", models.DecimalField(decimal_places=2, max_digits=12)),
                ("descuento", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("subtotal", models.GeneratedField(
                    db_persist=True,
                    expression=django.db.models.expressions.CombinedExpression(
                        models.F("precio_unitario"), "*", models.F("cantidad_pasajeros")),
                    output_field=models.DecimalField(decimal_places=2, max_digits=12))),
                ("total", models.GeneratedField(
                    db_persist=True,
                    expression=django.db.models.expressions.CombinedExpression(
                        django.db.models.expressions.CombinedExpression(
                            models.F("precio_unitario"), "*", models.F("cantidad_pasajeros")),
                        "-", models.F("descuento")),
                    output_field=models.DecimalField(decimal_places=2, max_digits=12))),
                ("estado", models.CharField(
                    choices=[("pendiente", "Pendiente"), ("confirmada", "Confirmada"), ("cancelada", "Cancelada"),
                             ("completada", "Completada"), ("expirada", "Expirada")],
                    default="pendiente", max_length=10)),
                ("fecha_reserva", models.DateTimeField(default=django.utils.timezone.now)),
                ("fecha_expiracion", models.DateTimeField(blank=True, null=True)),
                ("fecha_confirmacion", models.DateTimeField(blank=True, null=True)),
                ("fecha_cancelacion", models.DateTimeField(blank=True, null=True)),
                ("motivo_cancelacion", models.CharField(blank=True, max_length=250)),
                ("observaciones", models.CharField(blank=True, max_length=300)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                              related_name="reservas", to="accounts.perfil")),
                ("confirmada_por", models.ForeignKey(blank=True, null=True,
                                                     on_delete=django.db.models.deletion.PROTECT,
                                                     related_name="reservas_confirmadas", to="accounts.perfil")),
                ("creada_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                 related_name="reservas_creadas", to="accounts.perfil")),
                ("paquete", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                              related_name="reservas", to="packages.paquete")),
                ("promocion", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                                related_name="reservas", to="reservations.promocion")),
            ],
            options={
                "db_table": "reserva",
                "ordering": ["-fecha_reserva"],
                "indexes": [models.Index(fields=["estado"], name="ix_reserva_estado")],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(("cantidad_pasajeros__gt", 0)),
                                           name="ck_reserva_pasajeros"),
                    models.CheckConstraint(condition=models.Q(("precio_unitario__gt", 0)), name="ck_reserva_precio"),
                    models.CheckConstraint(condition=models.Q(("descuento__gte", 0)),
                                           name="ck_reserva_descuento_positivo"),
                    models.CheckConstraint(
                        condition=models.Q(("descuento__lte", django.db.models.expressions.CombinedExpression(
                            models.F("precio_unitario"), "*", models.F("cantidad_pasajeros")))),
                        name="ck_reserva_descuento_maximo"),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("estado", "cancelada"), ("fecha_cancelacion__isnull", False)),
                            models.Q(models.Q(("estado", "cancelada"), _negated=True),
                                     ("fecha_cancelacion__isnull", True)),
                            _connector="OR"),
                        name="ck_reserva_cancelacion"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Pasajero",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombres", models.CharField(max_length=80)),
                ("apellidos", models.CharField(max_length=80)),
                ("tipo_documento", models.CharField(
                    choices=[("CI", "Cédula de identidad"), ("PASAPORTE", "Pasaporte"),
                             ("CE", "Carnet de extranjería")],
                    default="CI", max_length=10)),
                ("nro_documento", models.CharField(max_length=20, verbose_name="número de documento")),
                ("fecha_nacimiento", models.DateField()),
                ("nacionalidad", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                                   to="destinations.pais")),
                ("reserva", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name="pasajeros", to="reservations.reserva")),
            ],
            options={
                "db_table": "pasajero",
                "ordering": ["id"],
                "constraints": [
                    models.UniqueConstraint(fields=("reserva", "tipo_documento", "nro_documento"),
                                            name="uq_pasajero_documento"),
                ],
            },
        ),
        migrations.CreateModel(
            name="DocumentoViaje",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(
                    choices=[("pasaporte", "Pasaporte"), ("visa", "Visa"), ("ci", "Cédula de identidad"),
                             ("vacunacion", "Certificado de vacunación"), ("otro", "Otro")],
                    max_length=25)),
                ("numero", models.CharField(blank=True, max_length=40, verbose_name="número")),
                ("fecha_vencimiento", models.DateField(blank=True, null=True)),
                ("archivo", models.FileField(max_length=255, upload_to=apps.reservations.models._ruta_documento)),
                ("fecha_carga", models.DateTimeField(auto_now_add=True)),
                ("pasajero", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                               related_name="documentos", to="reservations.pasajero")),
            ],
            options={
                "db_table": "documento_viaje",
                "ordering": ["fecha_carga"],
            },
        ),
        migrations.CreateModel(
            name="ConfirmacionProveedor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("concepto", models.CharField(max_length=200)),
                ("estado", models.CharField(
                    choices=[("pendiente", "Pendiente"), ("confirmada", "Confirmada"), ("rechazada", "Rechazada")],
                    default="pendiente", max_length=10)),
                ("codigo_confirmacion", models.CharField(blank=True, max_length=50,
                                                         verbose_name="código de confirmación")),
                ("fecha_solicitud", models.DateTimeField(default=django.utils.timezone.now)),
                ("fecha_respuesta", models.DateTimeField(blank=True, null=True)),
                ("observacion", models.CharField(blank=True, max_length=250)),
                ("gestionado_por", models.ForeignKey(blank=True, null=True,
                                                     on_delete=django.db.models.deletion.PROTECT,
                                                     related_name="confirmaciones_gestionadas",
                                                     to="accounts.perfil")),
                ("proveedor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                related_name="confirmaciones", to="suppliers.proveedor")),
                ("reserva", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                              related_name="confirmaciones_proveedor", to="reservations.reserva")),
            ],
            options={
                "verbose_name": "confirmación de proveedor",
                "verbose_name_plural": "confirmaciones de proveedores",
                "db_table": "confirmacion_proveedor",
                "ordering": ["-fecha_solicitud"],
                "constraints": [
                    models.UniqueConstraint(fields=("reserva", "proveedor", "concepto"),
                                            name="uq_confirmacion_proveedor"),
                ],
            },
        ),
    ]
