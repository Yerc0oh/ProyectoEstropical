import datetime as dt

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from apps.core.access import ROL_ADMIN, ROL_CLIENTE
from apps.core.disponibilidad import CapacidadPorDebajoDeOcupado, guardar_con_capacidad
from apps.destinations.models import Categoria, Destino, Pais
from apps.packages.models import Paquete, PaqueteHotel
from apps.suppliers.models import Proveedor

from .models import Hotel, TarifaHabitacion, TipoHabitacion


class GestionHabitacionesBase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "admin@test.com", "admin@test.com", "Clave-segura-123")
        self.admin.groups.add(Group.objects.get(name=ROL_ADMIN))
        self.client.force_login(self.admin)

        pais = Pais.objects.get(codigo_iso="BO")
        categoria = Categoria.objects.first()
        self.destino = Destino.objects.create(
            pais=pais, categoria=categoria, nombre="La Paz", codigo_iata="LPB")
        self.destino2 = Destino.objects.create(
            pais=pais, categoria=categoria, nombre="Uyuni", codigo_iata="UYU")
        proveedor = Proveedor.objects.create(
            razon_social="Hotelera SRL", nit="300", tipo=Proveedor.Tipo.HOTEL)
        self.hotel = Hotel.objects.create(
            proveedor=proveedor, destino=self.destino, nombre="Hotel Central", estrellas=4)
        self.hotel2 = Hotel.objects.create(
            proveedor=proveedor, destino=self.destino2, nombre="Hotel Salar", estrellas=3)
        self.tipo = TipoHabitacion.objects.create(
            hotel=self.hotel, nombre="Doble", capacidad=2,
            habitaciones_total=5, habitaciones_disponibles=5)

    def _datos_tipo(self, **cambios):
        datos = {
            "nombre": "Suite", "capacidad": 3, "habitaciones_total": 4,
            "habitaciones_disponibles": 4, "descripcion": "Vista al lago",
        }
        datos.update(cambios)
        return datos

    def _datos_tarifa(self, inicio="2027-01-01", fin="2027-03-31", precio="450.00"):
        return {"fecha_inicio": inicio, "fecha_fin": fin, "precio_noche": precio}

    def _url_lista_tipos(self, hotel=None):
        return reverse("hotels:gestion_habitaciones", args=[(hotel or self.hotel).pk])

    def _url_crear_tipo(self, hotel=None):
        return reverse("hotels:gestion_habitacion_crear", args=[(hotel or self.hotel).pk])

    def _url_editar_tipo(self, tipo, hotel=None):
        return reverse("hotels:gestion_habitacion_editar",
                       args=[(hotel or self.hotel).pk, tipo.pk])

    def _url_eliminar_tipo(self, tipo, hotel=None):
        return reverse("hotels:gestion_habitacion_eliminar",
                       args=[(hotel or self.hotel).pk, tipo.pk])

    def _url_lista_tarifas(self, tipo=None, hotel=None):
        tipo = tipo or self.tipo
        return reverse("hotels:gestion_tarifas",
                       args=[(hotel or self.hotel).pk, tipo.pk])

    def _url_crear_tarifa(self, tipo=None, hotel=None):
        tipo = tipo or self.tipo
        return reverse("hotels:gestion_tarifa_crear",
                       args=[(hotel or self.hotel).pk, tipo.pk])

    def _url_editar_tarifa(self, tarifa, tipo=None, hotel=None):
        tipo = tipo or self.tipo
        return reverse("hotels:gestion_tarifa_editar",
                       args=[(hotel or self.hotel).pk, tipo.pk, tarifa.pk])

    def _url_eliminar_tarifa(self, tarifa, tipo=None, hotel=None):
        tipo = tipo or self.tipo
        return reverse("hotels:gestion_tarifa_eliminar",
                       args=[(hotel or self.hotel).pk, tipo.pk, tarifa.pk])


class TipoHabitacionGestionTests(GestionHabitacionesBase):
    def test_lista_muestra_solo_las_habitaciones_del_hotel(self):
        TipoHabitacion.objects.create(
            hotel=self.hotel2, nombre="Familiar", capacidad=4,
            habitaciones_total=2, habitaciones_disponibles=2)
        r = self.client.get(self._url_lista_tipos())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Doble")
        self.assertNotContains(r, "Familiar")
        self.assertContains(r, self.hotel.nombre)

    def test_admin_crea_tipo_de_habitacion(self):
        r = self.client.post(self._url_crear_tipo(), self._datos_tipo())
        self.assertEqual(r.status_code, 302)
        tipo = TipoHabitacion.objects.get(hotel=self.hotel, nombre="Suite")
        self.assertEqual(tipo.capacidad, 3)
        self.assertEqual(tipo.habitaciones_disponibles, 4)

    def test_crear_asigna_el_hotel_de_la_url(self):
        self.client.post(self._url_crear_tipo(hotel=self.hotel2), self._datos_tipo())
        self.assertTrue(TipoHabitacion.objects.filter(
            hotel=self.hotel2, nombre="Suite").exists())

    def test_admin_edita_tipo_de_habitacion(self):
        r = self.client.post(
            self._url_editar_tipo(self.tipo),
            self._datos_tipo(nombre="Doble superior", capacidad=4))
        self.assertEqual(r.status_code, 302)
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.nombre, "Doble superior")
        self.assertEqual(self.tipo.capacidad, 4)

    def test_editar_tipo_de_otro_hotel_devuelve_404(self):
        r = self.client.get(self._url_editar_tipo(self.tipo, hotel=self.hotel2))
        self.assertEqual(r.status_code, 404)

    def test_eliminar_tipo_sin_uso_lo_borra_y_cascada_sus_tarifas(self):
        tarifa = TarifaHabitacion.objects.create(
            tipo_habitacion=self.tipo, fecha_inicio=dt.date(2027, 1, 1),
            fecha_fin=dt.date(2027, 1, 31), precio_noche="300.00")
        r = self.client.post(self._url_eliminar_tipo(self.tipo))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(TipoHabitacion.objects.filter(pk=self.tipo.pk).exists())
        self.assertFalse(TarifaHabitacion.objects.filter(pk=tarifa.pk).exists())

    def test_eliminar_tipo_usado_por_un_paquete_es_bloqueado(self):
        paquete = Paquete.objects.create(
            destino=self.destino, nombre="Paquete", fecha_salida=dt.date(2027, 2, 1),
            fecha_retorno=dt.date(2027, 2, 4), precio_persona="1000.00",
            cupos_total=5, cupos_disponibles=5, venta_desde=dt.date(2027, 1, 1),
            venta_hasta=dt.date(2027, 1, 20))
        PaqueteHotel.objects.create(
            paquete=paquete, tipo_habitacion=self.tipo, noches=3)
        r = self.client.post(self._url_eliminar_tipo(self.tipo), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "No se puede eliminar este tipo de habitación")
        self.assertTrue(TipoHabitacion.objects.filter(pk=self.tipo.pk).exists())

    def test_capacidad_invalida_es_rechazada(self):
        r = self.client.post(self._url_crear_tipo(), self._datos_tipo(capacidad=0))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "La capacidad debe ser al menos 1")
        self.assertFalse(TipoHabitacion.objects.filter(nombre="Suite").exists())

    def test_total_de_habitaciones_invalido_es_rechazado(self):
        r = self.client.post(
            self._url_crear_tipo(), self._datos_tipo(habitaciones_total=0))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Debe existir al menos 1 habitación")

    def test_la_disponibilidad_no_se_edita_directamente(self):
        # El formulario no expone habitaciones_disponibles: un valor enviado
        # por POST se ignora y la disponibilidad se recalcula al guardar.
        r = self.client.post(
            self._url_crear_tipo(),
            self._datos_tipo(habitaciones_total=2, habitaciones_disponibles=99))
        self.assertEqual(r.status_code, 302)
        tipo = TipoHabitacion.objects.get(hotel=self.hotel, nombre="Suite")
        self.assertEqual(tipo.habitaciones_total, 2)
        self.assertEqual(tipo.habitaciones_disponibles, 2)

    def test_nombre_duplicado_en_el_hotel_es_rechazado(self):
        r = self.client.post(self._url_crear_tipo(), self._datos_tipo(nombre="Doble"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(
            r, "Ya existe un tipo de habitación con ese nombre en este hotel")
        self.assertEqual(
            TipoHabitacion.objects.filter(hotel=self.hotel, nombre__iexact="Doble").count(), 1)

    def test_nombre_duplicado_ignora_mayusculas(self):
        r = self.client.post(self._url_crear_tipo(), self._datos_tipo(nombre="DOBLE"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(
            r, "Ya existe un tipo de habitación con ese nombre en este hotel")

    def test_mismo_nombre_permitido_en_otro_hotel(self):
        r = self.client.post(self._url_crear_tipo(hotel=self.hotel2),
                             self._datos_tipo(nombre="Doble"))
        self.assertEqual(r.status_code, 302)

    def test_cliente_no_accede_a_la_gestion_de_habitaciones(self):
        cliente = User.objects.create_user(
            "cliente@test.com", "cliente@test.com", "Clave-segura-123")
        cliente.groups.add(Group.objects.get(name=ROL_CLIENTE))
        self.client.force_login(cliente)
        self.assertEqual(self.client.get(self._url_lista_tipos()).status_code, 403)
        self.assertEqual(self.client.get(self._url_crear_tipo()).status_code, 403)


class DisponibilidadHabitacionesTests(GestionHabitacionesBase):
    def test_aumentar_el_total_incrementa_las_disponibles(self):
        # 5 habitaciones, 5 disponibles => 0 ocupadas. Se ocupan 3.
        TipoHabitacion.objects.filter(pk=self.tipo.pk).update(
            habitaciones_disponibles=2)
        r = self.client.post(
            self._url_editar_tipo(self.tipo),
            self._datos_tipo(nombre="Doble", capacidad=2, habitaciones_total=8))
        self.assertEqual(r.status_code, 302)
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.habitaciones_total, 8)
        self.assertEqual(self.tipo.habitaciones_ocupadas, 3)
        self.assertEqual(self.tipo.habitaciones_disponibles, 5)

    def test_reducir_el_total_conserva_las_habitaciones_ocupadas(self):
        TipoHabitacion.objects.filter(pk=self.tipo.pk).update(
            habitaciones_disponibles=2)  # 3 ocupadas
        r = self.client.post(
            self._url_editar_tipo(self.tipo),
            self._datos_tipo(nombre="Doble", capacidad=2, habitaciones_total=4))
        self.assertEqual(r.status_code, 302)
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.habitaciones_total, 4)
        self.assertEqual(self.tipo.habitaciones_ocupadas, 3)
        self.assertEqual(self.tipo.habitaciones_disponibles, 1)

    def test_rechaza_total_menor_que_las_habitaciones_ocupadas(self):
        TipoHabitacion.objects.filter(pk=self.tipo.pk).update(
            habitaciones_disponibles=2)  # 3 ocupadas
        r = self.client.post(
            self._url_editar_tipo(self.tipo),
            self._datos_tipo(nombre="Doble", capacidad=2, habitaciones_total=2))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "No puedes reducir el total por debajo de 3")
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.habitaciones_total, 5)
        self.assertEqual(self.tipo.habitaciones_disponibles, 2)

    def test_rechaza_total_negativo(self):
        r = self.client.post(
            self._url_editar_tipo(self.tipo),
            self._datos_tipo(nombre="Doble", capacidad=2, habitaciones_total=-1))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Debe existir al menos 1 habitación")
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.habitaciones_total, 5)

    def test_lista_muestra_total_ocupadas_y_disponibles(self):
        TipoHabitacion.objects.filter(pk=self.tipo.pk).update(
            habitaciones_disponibles=2)
        r = self.client.get(self._url_lista_tipos())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Ocupadas")
        self.assertContains(r, "Disponibles")
        self.assertContains(r, ">3<")
        self.assertContains(r, ">2<")

    def test_pantalla_de_edicion_muestra_el_resumen_de_disponibilidad(self):
        r = self.client.get(self._url_editar_tipo(self.tipo))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Capacidad total actual")

    def test_actualizacion_concurrente_conserva_las_habitaciones_ocupadas(self):
        obsoleto = TipoHabitacion.objects.get(pk=self.tipo.pk)  # 5/5
        TipoHabitacion.objects.filter(pk=self.tipo.pk).update(
            habitaciones_disponibles=1)  # otra operación ocupó 4
        obsoleto.habitaciones_total = 10
        guardar_con_capacidad(
            obsoleto, "habitaciones_total", "habitaciones_disponibles")
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.habitaciones_total, 10)
        self.assertEqual(self.tipo.habitaciones_ocupadas, 4)
        self.assertEqual(self.tipo.habitaciones_disponibles, 6)

    def test_servicio_rechaza_bajo_ocupado_tras_una_ocupacion_concurrente(self):
        obsoleto = TipoHabitacion.objects.get(pk=self.tipo.pk)  # 0 ocupadas
        TipoHabitacion.objects.filter(pk=self.tipo.pk).update(
            habitaciones_disponibles=1)  # 4 ocupadas
        obsoleto.habitaciones_total = 2
        with self.assertRaises(CapacidadPorDebajoDeOcupado):
            guardar_con_capacidad(
                obsoleto, "habitaciones_total", "habitaciones_disponibles")
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.habitaciones_total, 5)
        self.assertEqual(self.tipo.habitaciones_disponibles, 1)


class TarifaHabitacionGestionTests(GestionHabitacionesBase):
    def test_lista_muestra_hotel_y_tipo_de_habitacion(self):
        TarifaHabitacion.objects.create(
            tipo_habitacion=self.tipo, fecha_inicio=dt.date(2027, 1, 1),
            fecha_fin=dt.date(2027, 1, 31), precio_noche="300.00")
        r = self.client.get(self._url_lista_tarifas())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.hotel.nombre)
        self.assertContains(r, self.tipo.nombre)
        self.assertContains(r, "300,00")

    def test_admin_crea_tarifa(self):
        r = self.client.post(self._url_crear_tarifa(), self._datos_tarifa())
        self.assertEqual(r.status_code, 302)
        tarifa = TarifaHabitacion.objects.get(tipo_habitacion=self.tipo)
        self.assertEqual(tarifa.fecha_inicio, dt.date(2027, 1, 1))
        self.assertEqual(tarifa.fecha_fin, dt.date(2027, 3, 31))
        self.assertEqual(str(tarifa.precio_noche), "450.00")

    def test_admin_edita_tarifa(self):
        tarifa = TarifaHabitacion.objects.create(
            tipo_habitacion=self.tipo, fecha_inicio=dt.date(2027, 1, 1),
            fecha_fin=dt.date(2027, 1, 31), precio_noche="300.00")
        r = self.client.post(
            self._url_editar_tarifa(tarifa), self._datos_tarifa(precio="550.00"))
        self.assertEqual(r.status_code, 302)
        tarifa.refresh_from_db()
        self.assertEqual(str(tarifa.precio_noche), "550.00")

    def test_admin_elimina_tarifa(self):
        tarifa = TarifaHabitacion.objects.create(
            tipo_habitacion=self.tipo, fecha_inicio=dt.date(2027, 1, 1),
            fecha_fin=dt.date(2027, 1, 31), precio_noche="300.00")
        r = self.client.post(self._url_eliminar_tarifa(tarifa))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(TarifaHabitacion.objects.filter(pk=tarifa.pk).exists())

    def test_tarifa_de_otro_tipo_devuelve_404(self):
        otro = TipoHabitacion.objects.create(
            hotel=self.hotel, nombre="Simple", capacidad=1,
            habitaciones_total=3, habitaciones_disponibles=3)
        tarifa = TarifaHabitacion.objects.create(
            tipo_habitacion=self.tipo, fecha_inicio=dt.date(2027, 1, 1),
            fecha_fin=dt.date(2027, 1, 31), precio_noche="300.00")
        r = self.client.get(self._url_editar_tarifa(tarifa, tipo=otro))
        self.assertEqual(r.status_code, 404)

    def test_tarifa_de_tipo_de_otro_hotel_devuelve_404(self):
        otro_hotel = Hotel.objects.create(
            proveedor=self.hotel.proveedor, destino=self.destino2,
            nombre="Hotel Otro", estrellas=2)
        otro_tipo = TipoHabitacion.objects.create(
            hotel=otro_hotel, nombre="Doble", capacidad=2,
            habitaciones_total=2, habitaciones_disponibles=2)
        tarifa = TarifaHabitacion.objects.create(
            tipo_habitacion=self.tipo, fecha_inicio=dt.date(2027, 1, 1),
            fecha_fin=dt.date(2027, 1, 31), precio_noche="300.00")
        r = self.client.get(reverse("hotels:gestion_tarifa_editar",
                                    args=[self.hotel.pk, otro_tipo.pk, tarifa.pk]))
        self.assertEqual(r.status_code, 404)

    def test_precio_debe_ser_mayor_que_cero(self):
        r = self.client.post(
            self._url_crear_tarifa(), self._datos_tarifa(precio="0.00"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "El precio por noche debe ser mayor que cero")
        self.assertFalse(TarifaHabitacion.objects.exists())

    def test_fecha_fin_no_puede_ser_anterior_al_inicio(self):
        r = self.client.post(
            self._url_crear_tarifa(),
            self._datos_tarifa(inicio="2027-03-31", fin="2027-01-01"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(
            r, "La fecha de fin no puede ser anterior a la de inicio")
        self.assertFalse(TarifaHabitacion.objects.exists())

    def test_rangos_solapados_son_rechazados(self):
        TarifaHabitacion.objects.create(
            tipo_habitacion=self.tipo, fecha_inicio=dt.date(2027, 1, 1),
            fecha_fin=dt.date(2027, 1, 10), precio_noche="300.00")
        r = self.client.post(
            self._url_crear_tarifa(),
            self._datos_tarifa(inicio="2027-01-05", fin="2027-01-20"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "se solapa")
        self.assertEqual(TarifaHabitacion.objects.count(), 1)

    def test_rangos_adyacentes_son_permitidos(self):
        TarifaHabitacion.objects.create(
            tipo_habitacion=self.tipo, fecha_inicio=dt.date(2027, 1, 1),
            fecha_fin=dt.date(2027, 1, 10), precio_noche="300.00")
        r = self.client.post(
            self._url_crear_tarifa(),
            self._datos_tarifa(inicio="2027-01-11", fin="2027-01-20"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(TarifaHabitacion.objects.count(), 2)

    def test_solapamiento_con_otro_tipo_de_habitacion_es_permitido(self):
        otro = TipoHabitacion.objects.create(
            hotel=self.hotel, nombre="Simple", capacidad=1,
            habitaciones_total=3, habitaciones_disponibles=3)
        TarifaHabitacion.objects.create(
            tipo_habitacion=self.tipo, fecha_inicio=dt.date(2027, 1, 1),
            fecha_fin=dt.date(2027, 1, 10), precio_noche="300.00")
        r = self.client.post(
            self._url_crear_tarifa(tipo=otro),
            self._datos_tarifa(inicio="2027-01-05", fin="2027-01-20"))
        self.assertEqual(r.status_code, 302)

    def test_cliente_no_accede_a_la_gestion_de_tarifas(self):
        cliente = User.objects.create_user(
            "cliente@test.com", "cliente@test.com", "Clave-segura-123")
        cliente.groups.add(Group.objects.get(name=ROL_CLIENTE))
        self.client.force_login(cliente)
        self.assertEqual(self.client.get(self._url_lista_tarifas()).status_code, 403)
        self.assertEqual(self.client.get(self._url_crear_tarifa()).status_code, 403)


class IntegracionConPaquetesTests(GestionHabitacionesBase):
    def test_tipo_asignado_desde_cu12_sigue_disponible_y_protegido(self):
        hoy = dt.date.today()
        datos = {
            "destino": self.destino.pk, "nombre": "Salar 4D", "descripcion": "x",
            "condiciones": "y", "fecha_salida": hoy + dt.timedelta(days=30),
            "fecha_retorno": hoy + dt.timedelta(days=33),
            "precio_persona": "1500.00", "cupos_total": 10, "venta_desde": hoy,
            "venta_hasta": hoy + dt.timedelta(days=20), "estado": "publicado",
        }
        for prefix, formularios in (
                ("hoteles", [{"tipo_habitacion": self.tipo.pk, "noches": 3}]),
                ("vuelos", []), ("servicios", []), ("actividades", [])):
            datos[f"{prefix}-TOTAL_FORMS"] = str(len(formularios))
            datos[f"{prefix}-INITIAL_FORMS"] = "0"
            datos[f"{prefix}-MIN_NUM_FORMS"] = "0"
            datos[f"{prefix}-MAX_NUM_FORMS"] = "1000"
            for i, campos in enumerate(formularios):
                for nombre, valor in campos.items():
                    datos[f"{prefix}-{i}-{nombre}"] = valor
        r = self.client.post(reverse("packages:gestion_crear"), datos)
        self.assertEqual(r.status_code, 302)
        paquete = Paquete.objects.get(nombre="Salar 4D")
        self.assertEqual(paquete.paquetehotel_set.get().tipo_habitacion, self.tipo)

        # El tipo se puede seguir editando desde hoteles.
        r = self.client.post(
            self._url_editar_tipo(self.tipo),
            self._datos_tipo(nombre="Doble reformada", capacidad=3))
        self.assertEqual(r.status_code, 302)
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.nombre, "Doble reformada")

        # Pero no se puede borrar mientras el paquete lo use.
        r = self.client.post(self._url_eliminar_tipo(self.tipo), follow=True)
        self.assertContains(r, "No se puede eliminar este tipo de habitación")
        self.assertTrue(PaqueteHotel.objects.filter(
            paquete=paquete, tipo_habitacion=self.tipo).exists())
