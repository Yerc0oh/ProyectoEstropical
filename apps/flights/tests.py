import datetime as dt

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from apps.core.access import ROL_ADMIN, ROL_CLIENTE
from apps.core.disponibilidad import CapacidadPorDebajoDeOcupado, guardar_con_capacidad
from apps.destinations.models import Categoria, Destino, Pais
from apps.suppliers.models import Proveedor

from .models import Vuelo


class GestionVuelosBase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "admin@test.com", "admin@test.com", "Clave-segura-123")
        self.admin.groups.add(Group.objects.get(name=ROL_ADMIN))
        self.client.force_login(self.admin)

        pais = Pais.objects.get(codigo_iso="BO")
        categoria = Categoria.objects.first()
        self.origen = Destino.objects.create(
            pais=pais, categoria=categoria, nombre="La Paz", codigo_iata="LPB")
        self.destino = Destino.objects.create(
            pais=pais, categoria=categoria, nombre="Santa Cruz", codigo_iata="VVI")
        self.proveedor = Proveedor.objects.create(
            razon_social="Aerolínea Andina", nit="700", tipo=Proveedor.Tipo.AEROLINEA)

        salida = dt.datetime(2027, 3, 1, 8, 0, tzinfo=dt.timezone.utc)
        self.vuelo = Vuelo.objects.create(
            proveedor=self.proveedor, numero_vuelo="AA100", origen=self.origen,
            destino=self.destino, fecha_salida=salida,
            fecha_llegada=salida + dt.timedelta(hours=2),
            asientos_total=10, asientos_disponibles=8,
            precio_referencial="500.00")

    def _datos(self, **cambios):
        datos = {
            "proveedor": self.proveedor.pk,
            "numero_vuelo": "AA100",
            "origen": self.origen.pk,
            "destino": self.destino.pk,
            "fecha_salida": "2027-03-01T08:00",
            "fecha_llegada": "2027-03-01T10:00",
            "asientos_total": 10,
            "precio_referencial": "500.00",
            "estado": "programado",
        }
        datos.update(cambios)
        return datos

    def _url_crear(self):
        return reverse("flights:gestion_crear")

    def _url_editar(self, vuelo=None):
        return reverse("flights:gestion_editar", args=[(vuelo or self.vuelo).pk])

    def _url_lista(self):
        return reverse("flights:gestion_lista")


class DisponibilidadVuelosTests(GestionVuelosBase):
    def test_crear_vuelo_deja_todos_los_asientos_disponibles(self):
        r = self.client.post(self._url_crear(), self._datos(
            numero_vuelo="AA200", asientos_total=45))
        self.assertEqual(r.status_code, 302)
        vuelo = Vuelo.objects.get(numero_vuelo="AA200")
        self.assertEqual(vuelo.asientos_total, 45)
        self.assertEqual(vuelo.asientos_disponibles, 45)
        self.assertEqual(vuelo.asientos_ocupados, 0)

    def test_aumentar_total_incrementa_disponibles_conservando_ocupados(self):
        # 10 asientos, 8 disponibles => 2 ocupados.
        r = self.client.post(self._url_editar(), self._datos(asientos_total=15))
        self.assertEqual(r.status_code, 302)
        self.vuelo.refresh_from_db()
        self.assertEqual(self.vuelo.asientos_total, 15)
        self.assertEqual(self.vuelo.asientos_ocupados, 2)
        self.assertEqual(self.vuelo.asientos_disponibles, 13)
        self.assertLessEqual(self.vuelo.asientos_disponibles, self.vuelo.asientos_total)

    def test_reducir_total_conserva_la_cantidad_ocupada(self):
        r = self.client.post(self._url_editar(), self._datos(asientos_total=8))
        self.assertEqual(r.status_code, 302)
        self.vuelo.refresh_from_db()
        self.assertEqual(self.vuelo.asientos_total, 8)
        self.assertEqual(self.vuelo.asientos_ocupados, 2)
        self.assertEqual(self.vuelo.asientos_disponibles, 6)

    def test_rechaza_total_menor_que_los_asientos_ocupados(self):
        r = self.client.post(self._url_editar(), self._datos(asientos_total=1))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "No puedes reducir el total por debajo de 2")
        self.vuelo.refresh_from_db()
        self.assertEqual(self.vuelo.asientos_total, 10)
        self.assertEqual(self.vuelo.asientos_disponibles, 8)

    def test_rechaza_total_negativo(self):
        r = self.client.post(self._url_editar(), self._datos(asientos_total=-5))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "El total no puede ser negativo")
        self.vuelo.refresh_from_db()
        self.assertEqual(self.vuelo.asientos_total, 10)
        self.assertEqual(self.vuelo.asientos_disponibles, 8)

    def test_editar_no_permite_fijar_disponibilidad_manualmente(self):
        # El formulario no expone asientos_disponibles: un valor enviado por
        # POST se ignora y la disponibilidad se recalcula.
        r = self.client.post(self._url_editar(), self._datos(
            asientos_total=12, asientos_disponibles=12))
        self.assertEqual(r.status_code, 302)
        self.vuelo.refresh_from_db()
        self.assertEqual(self.vuelo.asientos_disponibles, 10)
        self.assertEqual(self.vuelo.asientos_ocupados, 2)

    def test_lista_muestra_total_ocupados_y_disponibles(self):
        r = self.client.get(self._url_lista())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Asientos totales")
        self.assertContains(r, "Ocupados")
        self.assertContains(r, "Disponibles")

    def test_pantalla_de_edicion_muestra_el_resumen_de_disponibilidad(self):
        r = self.client.get(self._url_editar())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Capacidad total actual")
        self.assertContains(r, "10")   # total
        self.assertContains(r, "8")    # disponible

    def test_actualizacion_concurrente_no_pierde_los_asientos_ocupados(self):
        """Simula dos administradores/ventas simultáneas sobre el mismo vuelo.

        La instancia que se guarda tiene una disponibilidad obsoleta (8). Otra
        operación ya comprometió 3 asientos más (disponible 5). El servicio
        debe recalcular con el valor vigente: 20 - 5 = 15, no 20 - 2 = 18.
        """
        obsoleto = Vuelo.objects.get(pk=self.vuelo.pk)   # disponible 8, ocupado 2
        Vuelo.objects.filter(pk=self.vuelo.pk).update(asientos_disponibles=5)

        obsoleto.asientos_total = 20
        guardar_con_capacidad(
            obsoleto, "asientos_total", "asientos_disponibles")

        self.vuelo.refresh_from_db()
        self.assertEqual(self.vuelo.asientos_total, 20)
        self.assertEqual(self.vuelo.asientos_ocupados, 5)
        self.assertEqual(self.vuelo.asientos_disponibles, 15)

    def test_servicio_rechaza_bajo_ocupado_tras_una_venta_concurrente(self):
        obsoleto = Vuelo.objects.get(pk=self.vuelo.pk)   # ocupado 2
        Vuelo.objects.filter(pk=self.vuelo.pk).update(asientos_disponibles=5)  # ocupado 5
        obsoleto.asientos_total = 3
        with self.assertRaises(CapacidadPorDebajoDeOcupado):
            guardar_con_capacidad(
                obsoleto, "asientos_total", "asientos_disponibles")
        self.vuelo.refresh_from_db()
        self.assertEqual(self.vuelo.asientos_total, 10)
        self.assertEqual(self.vuelo.asientos_disponibles, 5)


class AccesoVuelosTests(GestionVuelosBase):
    def test_cliente_no_accede_a_la_gestion_de_vuelos(self):
        cliente = User.objects.create_user(
            "cliente@test.com", "cliente@test.com", "Clave-segura-123")
        cliente.groups.add(Group.objects.get(name=ROL_CLIENTE))
        self.client.force_login(cliente)
        self.assertEqual(self.client.get(self._url_lista()).status_code, 403)
        self.assertEqual(self.client.get(self._url_editar()).status_code, 403)

    def test_anonimo_es_redirigido_al_login(self):
        self.client.logout()
        r = self.client.get(self._url_lista())
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:login"), r["Location"])
