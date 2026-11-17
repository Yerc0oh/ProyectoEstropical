"""Pruebas del Sprint 3 (necesitan PostgreSQL: usan el trigger y las funciones del schema)."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Perfil
from apps.core.access import ROL_ADMIN, ROL_CLIENTE
from apps.destinations.models import Categoria, Destino, Pais
from apps.flights.models import Vuelo
from apps.packages.models import Paquete, PaqueteActividad, PaqueteVuelo
from apps.suppliers.models import Proveedor

from . import services
from .models import ConfirmacionProveedor, Promocion, Reserva


def crear_usuario(email, rol, doc):
    u = User.objects.create_user(username=email, email=email, password="Clave-segura-123", first_name="Ana")
    u.groups.add(Group.objects.get(name=rol))
    perfil = Perfil.objects.create(usuario=u, nombres="Ana", apellidos=email.split("@")[0], nro_documento=doc)
    return u, perfil


def pasajero(n):
    return {"nombres": f"Pasajero{n}", "apellidos": "Prueba", "tipo_documento": "CI",
            "nro_documento": f"900{n}", "fecha_nacimiento": timezone.localdate() - timedelta(days=9000)}


class Escenario(TestCase):
    """Paquete publicado de Bs 1000 por persona, 10 cupos, con un vuelo de 3 asientos, que sale en 40 días."""

    def setUp(self):
        hoy = timezone.localdate()
        bolivia, peru = Pais.objects.get(codigo_iso="BO"), Pais.objects.get(codigo_iso="PE")
        cat = Categoria.objects.first()
        self.lpz = Destino.objects.create(pais=bolivia, categoria=cat, nombre="La Paz", codigo_iata="LPB")
        self.cuz = Destino.objects.create(pais=peru, categoria=cat, nombre="Cusco", codigo_iata="CUZ")
        self.aerolinea = Proveedor.objects.create(razon_social="Aerolínea Test", nit="1001", tipo="aerolinea")
        salida = timezone.now() + timedelta(days=40)
        self.vuelo = Vuelo.objects.create(proveedor=self.aerolinea, numero_vuelo="OB100", origen=self.lpz,
                                          destino=self.cuz, fecha_salida=salida, fecha_llegada=salida + timedelta(hours=1),
                                          asientos_total=3, asientos_disponibles=3, precio_referencial=500)
        self.paquete = Paquete.objects.create(
            destino=self.cuz, nombre="Cusco mágico", fecha_salida=hoy + timedelta(days=40),
            fecha_retorno=hoy + timedelta(days=44), precio_persona=Decimal("1000"), cupos_total=10,
            venta_desde=hoy - timedelta(days=1), venta_hasta=hoy + timedelta(days=30), estado="publicado")
        PaqueteVuelo.objects.create(paquete=self.paquete, vuelo=self.vuelo, tramo="ida")
        PaqueteActividad.objects.create(paquete=self.paquete, dia=2, orden=1, titulo="Machu Picchu")
        self.cliente_u, self.cliente = crear_usuario("cliente@test.com", ROL_CLIENTE, "111")
        self.otro_u, self.otro = crear_usuario("otro@test.com", ROL_CLIENTE, "222")
        self.admin_u, self.admin = crear_usuario("admin@test.com", ROL_ADMIN, "333")

    def reservar(self, n=2, cupon=""):
        return services.crear_reserva(self.paquete, self.cliente, self.cliente, [pasajero(i) for i in range(n)], cupon)

    def refrescar(self):
        self.paquete.refresh_from_db()
        self.vuelo.refresh_from_db()


class AccesoReservasTests(Escenario):
    SOLO_ADMIN = ["reservations:gestion_lista", "reservations:clientes", "reservations:confirmaciones",
                  "reservations:cronograma_paquetes", "reservations:cliente_nuevo"]

    def test_anonimo_redirigido(self):
        for nombre in self.SOLO_ADMIN + ["reservations:mis_reservas"]:
            r = self.client.get(reverse(nombre))
            self.assertEqual(r.status_code, 302, nombre)

    def test_cliente_no_entra_a_gestion(self):
        self.client.force_login(self.cliente_u)
        for nombre in self.SOLO_ADMIN:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 403, nombre)
        self.assertEqual(self.client.get(reverse("reservations:mis_reservas")).status_code, 200)

    def test_admin_entra_a_gestion(self):
        self.client.force_login(self.admin_u)
        for nombre in self.SOLO_ADMIN:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)

    def test_cliente_no_ve_reserva_ajena(self):
        reserva = self.reservar(1)
        self.client.force_login(self.otro_u)
        for nombre in ["detalle", "itinerario", "itinerario_pdf", "modificar", "cancelar"]:
            self.assertEqual(self.client.get(reverse(f"reservations:{nombre}", args=[reserva.pk])).status_code, 404, nombre)


class ReservarTests(Escenario):
    def test_reservar_desde_la_web_descuenta_cupos(self):            # CU-18 + trigger
        self.client.force_login(self.cliente_u)
        url = reverse("reservations:reservar", args=[self.paquete.pk])
        self.assertEqual(self.client.get(url + "?pasajeros=2").status_code, 200)
        datos = {"pas-TOTAL_FORMS": "2", "pas-INITIAL_FORMS": "2", "pas-MIN_NUM_FORMS": "1",
                 "pas-MAX_NUM_FORMS": "10", "cupon": "", "observaciones": ""}
        for i in range(2):
            p = pasajero(i)
            datos.update({f"pas-{i}-{k}": v for k, v in p.items()})
            datos[f"pas-{i}-fecha_nacimiento"] = p["fecha_nacimiento"].isoformat()
        r = self.client.post(url, datos)
        reserva = Reserva.objects.get()
        self.assertRedirects(r, reverse("reservations:detalle", args=[reserva.pk]))
        self.assertEqual(reserva.total, Decimal("2000"))
        self.assertEqual(reserva.estado, "pendiente")
        self.refrescar()
        self.assertEqual(self.paquete.cupos_disponibles, 8)
        self.assertEqual(self.vuelo.asientos_disponibles, 1)

    def test_no_permite_sobreventa(self):                               # RF-12
        with self.assertRaises(ValidationError):
            self.reservar(4)          # el vuelo solo tiene 3 asientos
        self.refrescar()
        self.assertEqual(self.paquete.cupos_disponibles, 10)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_cupon_porcentaje_y_minimo(self):
        hoy = timezone.localdate()
        Promocion.objects.create(codigo="VERANO10", tipo_descuento="porcentaje", valor=10, monto_minimo=1500,
                                 vigente_desde=hoy, vigente_hasta=hoy + timedelta(days=5))
        with self.assertRaises(ValidationError):
            self.reservar(1, "VERANO10")          # Bs 1000 < mínimo 1500
        reserva = self.reservar(2, "verano10")
        reserva.refresh_from_db()
        self.assertEqual(reserva.descuento, Decimal("200.00"))
        self.assertEqual(reserva.total, Decimal("1800.00"))

    def test_cupon_vencido_o_inexistente(self):
        hoy = timezone.localdate()
        Promocion.objects.create(codigo="VIEJO", tipo_descuento="monto_fijo", valor=50,
                                 vigente_desde=hoy - timedelta(days=10), vigente_hasta=hoy - timedelta(days=1))
        for codigo in ["VIEJO", "NOEXISTE"]:
            with self.assertRaises(ValidationError):
                self.reservar(1, codigo)

    def test_admin_reserva_para_cliente(self):
        reserva = services.crear_reserva(self.paquete, self.cliente, self.admin, [pasajero(1)])
        self.assertEqual(reserva.cliente, self.cliente)
        self.assertEqual(reserva.creada_por, self.admin)

    def test_modificar_cantidad_ajusta_cupos_y_precio(self):           # CU-20
        reserva = self.reservar(2)
        reserva.pasajeros.first().delete()
        reserva = services.actualizar_cantidad(reserva)
        reserva.refresh_from_db()
        self.refrescar()
        self.assertEqual(reserva.cantidad_pasajeros, 1)
        self.assertEqual(reserva.total, Decimal("1000"))
        self.assertEqual(self.paquete.cupos_disponibles, 9)

    def test_expira_sin_pago_y_libera_cupos(self):
        reserva = self.reservar(2)
        Reserva.objects.filter(pk=reserva.pk).update(fecha_expiracion=timezone.now() - timedelta(minutes=1))
        self.assertEqual(services.expirar_reservas_vencidas(), 1)
        reserva.refresh_from_db()
        self.refrescar()
        self.assertEqual(reserva.estado, "expirada")
        self.assertEqual(self.paquete.cupos_disponibles, 10)


class CancelarConfirmarTests(Escenario):
    def pagar(self, reserva, monto):
        from apps.payments.services import registrar_pago_ventanilla
        return registrar_pago_ventanilla(reserva, "efectivo", Decimal(monto), "", self.admin)

    def test_cancelar_calcula_penalidad_y_reembolso(self):              # CU-21
        reserva = self.reservar(2)                 # total 2000, faltan 40 días -> 10%
        self.pagar(reserva, 500)
        calculo = services.cancelar_reserva(reserva, self.cliente, "Cambio de planes")
        self.assertEqual(calculo["porcentaje"], Decimal("10"))
        self.assertEqual(calculo["penalidad"], Decimal("200.00"))
        self.assertEqual(calculo["reembolsable"], Decimal("300.00"))
        reserva.refresh_from_db()
        self.refrescar()
        self.assertEqual(reserva.estado, "cancelada")
        self.assertEqual(self.paquete.cupos_disponibles, 10)
        reembolso = reserva.reembolsos.get()
        self.assertEqual((reembolso.monto_reembolso, reembolso.penalidad), (Decimal("300.00"), Decimal("200.00")))
        with self.assertRaises(ValidationError):
            services.cancelar_reserva(reserva, self.cliente, "otra vez")

    def test_confirmar_exige_pago_y_genera_solicitudes(self):           # CU-22 y CU-17
        reserva = self.reservar(1)
        with self.assertRaises(ValidationError):
            services.confirmar_reserva(reserva, self.admin)
        self.pagar(reserva, 300)
        services.confirmar_reserva(reserva, self.admin)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, "confirmada")
        conf = ConfirmacionProveedor.objects.get(reserva=reserva)
        self.assertEqual(conf.proveedor, self.aerolinea)
        with self.assertRaises(ValidationError):           # sin código no se puede confirmar
            services.responder_confirmacion(conf, "confirmada", "", "", self.admin)
        services.responder_confirmacion(conf, "confirmada", "PNR123", "", self.admin)
        conf.refresh_from_db()
        self.assertEqual(conf.estado, "confirmada")

    def test_cliente_no_puede_confirmar(self):
        reserva = self.reservar(1)
        self.client.force_login(self.cliente_u)
        r = self.client.post(reverse("reservations:confirmar", args=[reserva.pk]))
        self.assertEqual(r.status_code, 403)


class ItinerarioYClientesTests(Escenario):
    def test_itinerario_pdf(self):                                       # CU-25
        reserva = self.reservar(1)
        self.client.force_login(self.cliente_u)
        r = self.client.get(reverse("reservations:itinerario_pdf", args=[reserva.pk]))
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
        r = self.client.get(reverse("reservations:itinerario", args=[reserva.pk]))
        self.assertContains(r, "Machu Picchu")

    def test_admin_registra_cliente(self):                               # CU-23
        self.client.force_login(self.admin_u)
        r = self.client.post(reverse("reservations:cliente_nuevo"), {
            "email": "Nuevo@Test.com", "nombres": "Luis", "apellidos": "Mamani", "tipo_documento": "CI",
            "nro_documento": "7654321"})
        perfil = Perfil.objects.get(nro_documento="7654321")
        self.assertRedirects(r, reverse("reservations:cliente_detalle", args=[perfil.pk]))
        self.assertTrue(perfil.usuario.groups.filter(name=ROL_CLIENTE).exists())
        self.assertEqual(perfil.usuario.username, "nuevo@test.com")



class VueloYHotelSoloTests(Escenario):
    """CU-18 ampliado: reservar un vuelo solo o un hotel solo, y pagarlo/cancelarlo igual que un paquete."""

    def setUp(self):
        super().setUp()
        from apps.hotels.models import Hotel, TarifaHabitacion, TipoHabitacion
        hotelero = Proveedor.objects.create(razon_social="Hoteles Test", nit="2002", tipo="hotel")
        self.hotel = Hotel.objects.create(proveedor=hotelero, destino=self.cuz, nombre="Hotel Inti", estrellas=3)
        self.doble = TipoHabitacion.objects.create(hotel=self.hotel, nombre="Doble", capacidad=2,
                                                   habitaciones_total=1, habitaciones_disponibles=1)
        hoy = timezone.localdate()
        TarifaHabitacion.objects.create(tipo_habitacion=self.doble, fecha_inicio=hoy,
                                        fecha_fin=hoy + timedelta(days=90), precio_noche=Decimal("300"))
        self.entrada = hoy + timedelta(days=20)

    def test_reservar_vuelo_solo_descuenta_asientos(self):
        reserva = services.crear_reserva_vuelo(self.vuelo, self.cliente, self.cliente, [pasajero(1), pasajero(2)])
        self.refrescar()
        self.assertEqual(reserva.tipo, Reserva.Tipo.VUELO)
        self.assertIsNone(reserva.paquete)
        self.assertEqual(reserva.total, Decimal("1000"))          # 2 × Bs 500
        self.assertEqual(self.vuelo.asientos_disponibles, 1)      # el trigger descontó 2
        self.assertEqual(self.paquete.cupos_disponibles, 10)      # el paquete no se toca
        with self.assertRaises(ValidationError):                  # solo queda 1 asiento
            services.crear_reserva_vuelo(self.vuelo, self.otro, self.otro, [pasajero(3), pasajero(4)])
        services.cancelar_reserva(reserva, self.cliente, "Prueba")
        self.refrescar()
        self.assertEqual(self.vuelo.asientos_disponibles, 3)      # al cancelar se devuelven

    def test_reservar_hotel_solo_calcula_noches_y_habitaciones(self):
        salida = self.entrada + timedelta(days=3)
        reserva = services.crear_reserva_hotel(self.doble, self.entrada, salida, self.cliente, self.cliente,
                                               [pasajero(1), pasajero(2)])
        self.assertEqual(reserva.tipo, Reserva.Tipo.HOTEL)
        self.assertEqual(reserva.total, Decimal("900"))           # 3 noches × Bs 300 × 1 habitación
        self.assertEqual(reserva.fecha_viaje, self.entrada)
        self.assertEqual(reserva.asignaciones_hotel.count(), 1)
        with self.assertRaises(ValidationError):                  # el hotel solo tiene 1 habitación doble
            services.crear_reserva_hotel(self.doble, self.entrada, salida, self.otro, self.otro, [pasajero(3)])
        with self.assertRaises(ValidationError):                  # fechas sin tarifa
            services.crear_reserva_hotel(self.doble, self.entrada + timedelta(days=100),
                                         self.entrada + timedelta(days=101), self.otro, self.otro, [pasajero(3)])

    def test_vuelo_solo_se_paga_factura_y_cancela_con_penalidad(self):
        from apps.payments import services as pagos
        reserva = services.crear_reserva_vuelo(self.vuelo, self.cliente, self.cliente, [pasajero(1)])
        pagos.pagar_en_linea(reserva, "qr")
        services.confirmar_reserva(reserva, self.admin)
        self.assertEqual(reserva.confirmaciones_proveedor.count(), 1)   # solicitud a la aerolínea
        factura = pagos.emitir_factura(reserva, "1234567", "Cliente Test", self.admin)
        self.assertIn("Vuelo OB100", factura.concepto)
        datos = services.calcular_cancelacion(reserva)
        self.assertEqual(datos["porcentaje"], Decimal("10"))       # sale en 40 días → 10 %

    def test_paginas_de_reserva_de_vuelo_y_hotel(self):
        self.client.force_login(self.cliente_u)
        r = self.client.get(reverse("reservations:reservar_vuelo", args=[self.vuelo.pk]))
        self.assertEqual(r.status_code, 200)
        datos = {"pas-TOTAL_FORMS": "1", "pas-INITIAL_FORMS": "0", "pas-0-nombres": "Ana", "pas-0-apellidos": "Q",
                 "pas-0-tipo_documento": "CI", "pas-0-nro_documento": "555",
                 "pas-0-fecha_nacimiento": "1990-01-01", "cupon": "", "observaciones": ""}
        r = self.client.post(reverse("reservations:reservar_vuelo", args=[self.vuelo.pk]), datos)
        reserva = Reserva.objects.get(tipo="vuelo")
        self.assertRedirects(r, reverse("reservations:detalle", args=[reserva.pk]))
        datos.update({"fecha_entrada": self.entrada.isoformat(),
                      "fecha_salida": (self.entrada + timedelta(days=2)).isoformat()})
        r = self.client.post(reverse("reservations:reservar_hotel", args=[self.doble.pk]), datos)
        reserva = Reserva.objects.get(tipo="hotel")
        self.assertRedirects(r, reverse("reservations:detalle", args=[reserva.pk]))
        self.assertContains(self.client.get(reverse("reservations:detalle", args=[reserva.pk])), "Hotel Inti")