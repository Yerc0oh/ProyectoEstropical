"""Pruebas del Sprint 4 (necesitan PostgreSQL: fn_cerrar_caja, fn_penalidad_cancelacion, v_saldo_reserva)."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.reservations.tests import Escenario

from . import services
from .models import CierreCaja, Cuota, Factura, Pago, PagoProveedor, SaldoReserva

TARJETA_OK = "4111111111111111"


class PagosTests(Escenario):
    def test_pago_en_linea_aprobado_y_rechazado(self):                  # CU-26
        reserva = self.reservar(2)
        pago, _ = services.pagar_en_linea(reserva, "tarjeta", "4000000000000002")
        self.assertEqual(pago.estado, Pago.Estado.FALLIDO)
        self.assertIsNone(pago.nro_comprobante)
        pago, _ = services.pagar_en_linea(reserva, "tarjeta", TARJETA_OK)
        self.assertEqual(pago.estado, Pago.Estado.COMPLETADO)
        self.assertEqual(pago.monto, Decimal("2000"))
        self.assertTrue(pago.nro_comprobante.startswith("CP-"))
        self.assertEqual(services.saldo_pendiente(reserva), 0)
        with self.assertRaises(ValidationError):                    # ya no hay saldo
            services.pagar_en_linea(reserva, "qr")

    def test_pago_desde_la_web_y_comprobante(self):
        reserva = self.reservar(1)
        self.client.force_login(self.cliente_u)
        r = self.client.post(reverse("payments:pagar", args=[reserva.pk]), {"metodo": "qr"})
        pago = Pago.objects.get()
        self.assertRedirects(r, reverse("payments:pago_resultado", args=[pago.pk]))
        r = self.client.get(reverse("payments:comprobante_pdf", args=[pago.pk]))
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.client.force_login(self.otro_u)                        # otro cliente: no lo ve
        self.assertEqual(self.client.get(reverse("payments:comprobante_pdf", args=[pago.pk])).status_code, 404)

    def test_plan_de_cuotas(self):                                     # CU-27
        reserva = self.reservar(1)             # Bs 1000, sale en 40 días
        with self.assertRaises(ValidationError):
            services.crear_plan_cuotas(reserva, 3)     # la 3ra vencería después de salida - 7 días
        cuotas = services.crear_plan_cuotas(reserva, 2)
        self.assertEqual(sum(c.monto for c in cuotas), Decimal("1000"))
        pago, _ = services.pagar_en_linea(reserva, "qr")
        self.assertEqual(pago.monto, Decimal("500.00"))
        self.assertEqual(pago.cuota.estado, Cuota.Estado.PAGADA)
        with self.assertRaises(ValidationError):       # en ventanilla debe pagarse el monto exacto de la cuota
            services.registrar_pago_ventanilla(reserva, "efectivo", Decimal("100"), "", self.admin)

    def test_ventanilla_valida_monto_y_referencia(self):                # CU-28
        reserva = self.reservar(1)
        with self.assertRaises(ValidationError):
            services.registrar_pago_ventanilla(reserva, "efectivo", Decimal("5000"), "", self.admin)
        with self.assertRaises(ValidationError):
            services.registrar_pago_ventanilla(reserva, "transferencia", Decimal("100"), "", self.admin)
        pago = services.registrar_pago_ventanilla(reserva, "transferencia", Decimal("100"), "DEP-1", self.admin)
        self.assertEqual(pago.canal, "ventanilla")
        self.assertEqual(pago.registrado_por, self.admin)

    def test_vista_saldo_reserva(self):                                # CU-29 / CU-35
        reserva = self.reservar(2)
        services.registrar_pago_ventanilla(reserva, "efectivo", Decimal("500"), "", self.admin)
        saldo = SaldoReserva.objects.get(pk=reserva.pk)
        self.assertEqual((saldo.total, saldo.pagado, saldo.saldo_pendiente),
                         (Decimal("2000"), Decimal("500"), Decimal("1500")))
        self.client.force_login(self.admin_u)
        self.assertContains(self.client.get(reverse("payments:cuentas_por_cobrar")), reserva.codigo)


class FacturasTests(Escenario):
    def test_emitir_y_anular_factura(self):                            # CU-30, CU-32
        reserva = self.reservar(1)
        with self.assertRaises(ValidationError):
            services.emitir_factura(reserva, "1234567", "Ana", self.admin)  # nada pagado aún
        services.registrar_pago_ventanilla(reserva, "efectivo", Decimal("400"), "", self.admin)
        with self.assertRaises(ValidationError):
            services.emitir_factura(reserva, "12A45", "Ana", self.admin)    # NIT inválido
        f1 = services.emitir_factura(reserva, "1234567", "Ana López", self.admin)
        self.assertEqual((f1.nro_factura, f1.monto), (1, Decimal("400")))
        self.assertEqual(services.monto_facturable(reserva), 0)
        services.anular_factura(f1, "Error en razón social", self.admin)
        self.assertEqual(services.monto_facturable(reserva), Decimal("400"))
        f2 = services.emitir_factura(reserva, "1234567", "Ana Lopez", self.admin)
        self.assertEqual(f2.nro_factura, 2)

    def test_cliente_descarga_solo_sus_facturas(self):                 # CU-31
        reserva = self.reservar(1)
        services.registrar_pago_ventanilla(reserva, "efectivo", Decimal("400"), "", self.admin)
        factura = services.emitir_factura(reserva, "0", "", self.admin)
        self.assertEqual(factura.razon_social, "S/N")
        self.client.force_login(self.cliente_u)
        r = self.client.get(reverse("payments:factura_pdf", args=[factura.pk]))
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.client.force_login(self.otro_u)
        self.assertEqual(self.client.get(reverse("payments:factura_pdf", args=[factura.pk])).status_code, 404)


class CajaTests(Escenario):
    def test_conciliar_extracto(self):                                 # CU-34
        reserva = self.reservar(1)
        pago = services.registrar_pago_ventanilla(reserva, "transferencia", Decimal("300"), "DEP-77", self.admin)
        csv = SimpleUploadedFile("extracto.csv", b"referencia,monto\nDEP-77,300.00\nNO-EXISTE,10\n")
        resultados = services.conciliar_extracto(csv, self.admin)
        self.assertEqual([r["resultado"] for r in resultados], ["conciliado", "no_encontrado"])
        pago.refresh_from_db()
        self.assertTrue(pago.conciliado)

    def test_cierre_de_caja(self):                                     # CU-37 y CU-36
        reserva = self.reservar(1)
        services.registrar_pago_ventanilla(reserva, "efectivo", Decimal("1000"), "", self.admin)
        pp = PagoProveedor.objects.create(proveedor=self.aerolinea, monto=Decimal("600"), metodo="transferencia",
                                          registrado_por=self.admin)
        services.marcar_pago_proveedor_pagado(pp, "TR-1")
        hoy = timezone.localdate()
        previo = services.movimientos_de_caja(hoy)
        self.assertEqual((previo["ingresos"], previo["egresos"]), (Decimal("1000"), Decimal("600")))
        cierre = services.cerrar_caja(hoy, self.admin, "Prueba")
        self.assertEqual((cierre.total_ingresos, cierre.total_egresos, cierre.saldo),
                         (Decimal("1000"), Decimal("600"), Decimal("400")))
        self.assertEqual(Pago.objects.filter(cierre_caja=cierre).count(), 1)
        with self.assertRaises(ValidationError):
            services.cerrar_caja(hoy, self.admin)
        self.assertEqual(CierreCaja.objects.count(), 1)

    def test_reembolso_procesado(self):                                # CU-33
        from apps.reservations.services import cancelar_reserva
        reserva = self.reservar(1)
        services.registrar_pago_ventanilla(reserva, "efectivo", Decimal("1000"), "", self.admin)
        cancelar_reserva(reserva, self.cliente, "No viajo")
        reembolso = reserva.reembolsos.get()
        self.assertEqual(reembolso.monto_reembolso, Decimal("900.00"))   # 10% de penalidad
        with self.assertRaises(ValidationError):
            services.procesar_reembolso(reembolso, True, "transferencia", "", self.admin)   # falta referencia
        services.procesar_reembolso(reembolso, True, "efectivo", "", self.admin)
        reembolso.refresh_from_db()
        self.assertEqual(reembolso.estado, "procesado")

    def test_paginas_de_caja_solo_admin(self):
        nombres = ["ventanilla", "gestion_pagos", "gestion_facturas", "reembolsos", "conciliacion",
                   "cuentas_por_cobrar", "pagos_proveedor", "pago_proveedor_crear", "caja"]
        self.client.force_login(self.cliente_u)
        for n in nombres:
            self.assertEqual(self.client.get(reverse(f"payments:{n}")).status_code, 403, n)
        self.client.force_login(self.admin_u)
        for n in nombres:
            self.assertEqual(self.client.get(reverse(f"payments:{n}")).status_code, 200, n)
        self.assertEqual(Factura.objects.count(), 0)
