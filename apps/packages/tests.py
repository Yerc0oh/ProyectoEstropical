import datetime as dt

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.access import ROL_ADMIN, ROL_CLIENTE
from apps.core.disponibilidad import CapacidadPorDebajoDeOcupado, guardar_con_capacidad
from apps.destinations.models import Categoria, Destino, Pais
from apps.flights.models import Vuelo
from apps.hotels.models import Hotel, TipoHabitacion
from apps.packages.models import (Paquete, PaqueteActividad, PaqueteHotel,
                                  PaqueteServicio, PaqueteVuelo, Servicio)
from apps.suppliers.models import Proveedor


class GestionPaquetesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "a@test.com", "a@test.com", "Clave-segura-123")
        self.admin.groups.add(Group.objects.get(name=ROL_ADMIN))
        self.client.force_login(self.admin)

        self.pais = Pais.objects.get(codigo_iso="BO")
        self.categoria = Categoria.objects.first()
        self.destino = Destino.objects.create(
            pais=self.pais, categoria=self.categoria, nombre="La Paz", codigo_iata="LPB")
        self.destino2 = Destino.objects.create(
            pais=self.pais, categoria=self.categoria, nombre="Uyuni", codigo_iata="UYU")

        proveedor_hotel = Proveedor.objects.create(
            razon_social="Hotelera SRL", nit="100", tipo=Proveedor.Tipo.HOTEL)
        self.hotel = Hotel.objects.create(
            proveedor=proveedor_hotel, destino=self.destino, nombre="Hotel Central",
            estrellas=4)
        self.tipo_habitacion = TipoHabitacion.objects.create(
            hotel=self.hotel, nombre="Doble", capacidad=2,
            habitaciones_total=5, habitaciones_disponibles=5)

        proveedor_vuelo = Proveedor.objects.create(
            razon_social="Aerolínea SRL", nit="200", tipo=Proveedor.Tipo.AEROLINEA)
        salida = timezone.now() + dt.timedelta(days=30)
        self.vuelo = Vuelo.objects.create(
            proveedor=proveedor_vuelo, numero_vuelo="AV101", origen=self.destino2,
            destino=self.destino, fecha_salida=salida,
            fecha_llegada=salida + dt.timedelta(hours=2), asientos_total=100,
            asientos_disponibles=100, precio_referencial="500.00")

        self.servicio = Servicio.objects.create(nombre="Traslado aeropuerto")

    # ------------------------------------------------------------- utilidades
    def _datos_paquete(self, **cambios):
        hoy = dt.date.today()
        datos = {
            "destino": self.destino.pk, "nombre": "Salar 4D", "descripcion": "x",
            "condiciones": "y", "fecha_salida": hoy + dt.timedelta(days=30),
            "fecha_retorno": hoy + dt.timedelta(days=33), "precio_persona": "1500.00",
            "cupos_total": 10, "venta_desde": hoy,
            "venta_hasta": hoy + dt.timedelta(days=20), "estado": "publicado",
        }
        datos.update(cambios)
        return datos

    def _formset(self, prefix, formularios, initial=0):
        datos = {
            f"{prefix}-TOTAL_FORMS": str(len(formularios)),
            f"{prefix}-INITIAL_FORMS": str(initial),
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
        }
        for i, campos in enumerate(formularios):
            for nombre, valor in campos.items():
                datos[f"{prefix}-{i}-{nombre}"] = valor
        return datos

    def _datos_componentes(self, componentes=None, initial=None):
        """Añade los management forms de los cuatro formsets al POST."""
        componentes = componentes or {}
        initial = initial or {}
        datos = {}
        for prefix in ("hoteles", "vuelos", "servicios", "actividades"):
            datos.update(self._formset(
                prefix, componentes.get(prefix, []), initial.get(prefix, 0)))
        return datos

    def _hotel(self, noches=3, **extra):
        return {"tipo_habitacion": self.tipo_habitacion.pk, "noches": noches, **extra}

    def _vuelo(self, tramo="ida", **extra):
        return {"vuelo": self.vuelo.pk, "tramo": tramo, **extra}

    def _servicio(self, detalle="Incluido", **extra):
        return {"servicio": self.servicio.pk, "detalle": detalle, **extra}

    def _actividad(self, dia=1, orden=1, titulo="City tour", **extra):
        return {"dia": dia, "orden": orden, "hora_inicio": "09:00",
                "titulo": titulo, "descripcion": "Recorrido", **extra}

    def _crear_paquete(self, componentes=None):
        datos = self._datos_paquete()
        datos.update(self._datos_componentes(componentes))
        return self.client.post(reverse("packages:gestion_crear"), datos)

    def _crear_con_todos_los_componentes(self):
        r = self._crear_paquete({
            "hoteles": [self._hotel()],
            "vuelos": [self._vuelo()],
            "servicios": [self._servicio()],
            "actividades": [self._actividad()],
        })
        self.assertEqual(r.status_code, 302)
        return Paquete.objects.get(nombre="Salar 4D")

    # --------------------------------------------------------------- creación
    def test_admin_crea_paquete_con_todos_los_componentes(self):
        p = self._crear_con_todos_los_componentes()
        self.assertEqual(PaqueteHotel.objects.filter(paquete=p).count(), 1)
        self.assertEqual(PaqueteVuelo.objects.filter(paquete=p).count(), 1)
        self.assertEqual(PaqueteServicio.objects.filter(paquete=p).count(), 1)
        self.assertEqual(PaqueteActividad.objects.filter(paquete=p).count(), 1)
        self.assertEqual(p.paquetehotel_set.get().noches, 3)
        self.assertEqual(p.paquetevuelo_set.get().tramo, "ida")
        self.assertEqual(p.paqueteservicio_set.get().detalle, "Incluido")
        self.assertEqual(p.actividades.get().titulo, "City tour")

    def test_crear_varios_componentes_del_mismo_tipo(self):
        otra_habitacion = TipoHabitacion.objects.create(
            hotel=self.hotel, nombre="Suite", capacidad=3,
            habitaciones_total=2, habitaciones_disponibles=2)
        r = self._crear_paquete({
            "hoteles": [self._hotel(), self._hotel(
                tipo_habitacion=otra_habitacion.pk, noches=2)],
            "actividades": [self._actividad(), self._actividad(orden=2, titulo="Cena")],
        })
        self.assertEqual(r.status_code, 302)
        p = Paquete.objects.get(nombre="Salar 4D")
        self.assertEqual(p.paquetehotel_set.count(), 2)
        self.assertEqual(p.actividades.count(), 2)

    # ---------------------------------------------------------------- edición
    def test_editar_componentes_existentes(self):
        p = self._crear_con_todos_los_componentes()
        componentes = {
            "hoteles": [self._hotel(noches=5, id=p.paquetehotel_set.get().pk)],
            "vuelos": [self._vuelo(tramo="vuelta", id=p.paquetevuelo_set.get().pk)],
            "servicios": [self._servicio(detalle="Actualizado",
                                         id=p.paqueteservicio_set.get().pk)],
            "actividades": [self._actividad(titulo="City tour nocturno",
                                            id=p.actividades.get().pk)],
        }
        datos = self._datos_paquete()
        datos.update(self._datos_componentes(componentes, initial={
            "hoteles": 1, "vuelos": 1, "servicios": 1, "actividades": 1}))
        r = self.client.post(reverse("packages:gestion_editar", args=[p.pk]), datos)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(p.paquetehotel_set.get().noches, 5)
        self.assertEqual(p.paquetevuelo_set.get().tramo, "vuelta")
        self.assertEqual(p.paqueteservicio_set.get().detalle, "Actualizado")
        self.assertEqual(p.actividades.get().titulo, "City tour nocturno")

    def test_eliminar_componentes_existentes(self):
        p = self._crear_con_todos_los_componentes()
        componentes = {
            "hoteles": [self._hotel(id=p.paquetehotel_set.get().pk, DELETE="on")],
            "vuelos": [self._vuelo(id=p.paquetevuelo_set.get().pk, DELETE="on")],
            "servicios": [self._servicio(id=p.paqueteservicio_set.get().pk, DELETE="on")],
            "actividades": [self._actividad(id=p.actividades.get().pk, DELETE="on")],
        }
        datos = self._datos_paquete()
        datos.update(self._datos_componentes(componentes, initial={
            "hoteles": 1, "vuelos": 1, "servicios": 1, "actividades": 1}))
        r = self.client.post(reverse("packages:gestion_editar", args=[p.pk]), datos)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(PaqueteHotel.objects.filter(paquete=p).count(), 0)
        self.assertEqual(PaqueteVuelo.objects.filter(paquete=p).count(), 0)
        self.assertEqual(PaqueteServicio.objects.filter(paquete=p).count(), 0)
        self.assertEqual(PaqueteActividad.objects.filter(paquete=p).count(), 0)

    # ------------------------------------------------------------ validaciones
    def test_componente_invalido_no_crea_registros_parciales(self):
        r = self._crear_paquete({
            "hoteles": [self._hotel(noches=0)],
            "vuelos": [self._vuelo()],
            "servicios": [self._servicio()],
            "actividades": [self._actividad()],
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Debe indicar al menos 1 noche")
        self.assertFalse(Paquete.objects.filter(nombre="Salar 4D").exists())
        self.assertEqual(PaqueteHotel.objects.count(), 0)
        self.assertEqual(PaqueteVuelo.objects.count(), 0)
        self.assertEqual(PaqueteServicio.objects.count(), 0)
        self.assertEqual(PaqueteActividad.objects.count(), 0)

    def test_actividad_con_dia_invalido_es_rechazada(self):
        r = self._crear_paquete({"actividades": [self._actividad(dia=0)]})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "El día debe ser 1 o mayor")
        self.assertFalse(Paquete.objects.filter(nombre="Salar 4D").exists())

    def test_duplicado_en_el_mismo_formset_es_rechazado(self):
        r = self._crear_paquete({
            "hoteles": [self._hotel(), self._hotel(noches=2)],
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "repetido en el paquete")
        self.assertFalse(Paquete.objects.filter(nombre="Salar 4D").exists())
        self.assertEqual(PaqueteHotel.objects.count(), 0)

    def test_actividad_duplicada_por_dia_y_orden_es_rechazada(self):
        r = self._crear_paquete({
            "actividades": [self._actividad(), self._actividad(titulo="Otra")],
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Ya existe una actividad con ese día y orden")
        self.assertFalse(Paquete.objects.filter(nombre="Salar 4D").exists())

    def test_edicion_invalida_no_modifica_ni_borra_componentes(self):
        p = self._crear_con_todos_los_componentes()
        hotel = p.paquetehotel_set.get()
        datos = self._datos_paquete(nombre="Nombre modificado")
        datos.update(self._datos_componentes({
            "hoteles": [self._hotel(noches="", id=hotel.pk)],
            "vuelos": [self._vuelo(id=p.paquetevuelo_set.get().pk)],
            "servicios": [self._servicio(id=p.paqueteservicio_set.get().pk)],
            "actividades": [self._actividad(id=p.actividades.get().pk)],
        }, initial={"hoteles": 1, "vuelos": 1, "servicios": 1, "actividades": 1}))
        r = self.client.post(reverse("packages:gestion_editar", args=[p.pk]), datos)
        self.assertEqual(r.status_code, 200)
        p.refresh_from_db()
        hotel.refresh_from_db()
        self.assertEqual(p.nombre, "Salar 4D")
        self.assertEqual(hotel.noches, 3)
        self.assertEqual(p.paquetehotel_set.count(), 1)

    # --------------------------------------------------------- interfaz/acceso
    def test_formulario_de_gestion_muestra_los_cuatro_formsets(self):
        r = self.client.get(reverse("packages:gestion_crear"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Componentes del paquete")
        for prefix in ("hoteles", "vuelos", "servicios", "actividades"):
            self.assertContains(r, f"{prefix}-TOTAL_FORMS")
        self.assertContains(r, "Agregar")

    def test_cliente_no_puede_acceder_a_la_gestion_de_paquetes(self):
        cliente = User.objects.create_user(
            "c@test.com", "c@test.com", "Clave-segura-123")
        cliente.groups.add(Group.objects.get(name=ROL_CLIENTE))
        self.client.force_login(cliente)
        self.assertEqual(self.client.get(reverse("packages:gestion_crear")).status_code, 403)
        self.assertEqual(
            self.client.get(reverse("packages:gestion_editar", args=[1])).status_code, 403)


class DisponibilidadPaquetesTests(GestionPaquetesTests):
    def _paquete_con_ocupacion(self):
        p = self._crear_con_todos_los_componentes()   # 10 cupos, 10 disponibles
        Paquete.objects.filter(pk=p.pk).update(cupos_disponibles=7)  # 3 ocupados
        p.refresh_from_db()
        return p

    def _editar(self, paquete, **cambios):
        datos = self._datos_paquete(**cambios)
        datos.update(self._datos_componentes())
        return self.client.post(
            reverse("packages:gestion_editar", args=[paquete.pk]), datos)

    def test_aumentar_cupos_incrementa_disponibles_conservando_ocupados(self):
        p = self._paquete_con_ocupacion()
        r = self._editar(p, cupos_total=15)
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertEqual(p.cupos_total, 15)
        self.assertEqual(p.cupos_ocupados, 3)
        self.assertEqual(p.cupos_disponibles, 12)

    def test_reducir_cupos_conserva_la_cantidad_ocupada(self):
        p = self._paquete_con_ocupacion()
        r = self._editar(p, cupos_total=8)
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertEqual(p.cupos_total, 8)
        self.assertEqual(p.cupos_ocupados, 3)
        self.assertEqual(p.cupos_disponibles, 5)

    def test_rechaza_cupos_totales_menores_que_los_ocupados(self):
        p = self._paquete_con_ocupacion()
        r = self._editar(p, cupos_total=2)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "No puedes reducir el total por debajo de 3")
        p.refresh_from_db()
        self.assertEqual(p.cupos_total, 10)
        self.assertEqual(p.cupos_disponibles, 7)

    def test_rechaza_cupos_negativos(self):
        p = self._paquete_con_ocupacion()
        r = self._editar(p, cupos_total=-1)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "El total no puede ser negativo")
        p.refresh_from_db()
        self.assertEqual(p.cupos_total, 10)
        self.assertEqual(p.cupos_disponibles, 7)

    def test_la_disponibilidad_no_se_edita_manualmente(self):
        p = self._paquete_con_ocupacion()
        r = self._editar(p, cupos_total=12, cupos_disponibles=99)
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertEqual(p.cupos_disponibles, 9)
        self.assertEqual(p.cupos_ocupados, 3)

    def test_actualizar_cupos_no_altera_los_componentes_del_paquete(self):
        p = self._paquete_con_ocupacion()
        hoteles = list(PaqueteHotel.objects.filter(paquete=p))
        vuelos = list(PaqueteVuelo.objects.filter(paquete=p))
        self.assertEqual(len(hoteles), 1)
        self.assertEqual(len(vuelos), 1)

        r = self._editar(p, cupos_total=20)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(list(PaqueteHotel.objects.filter(paquete=p)), hoteles)
        self.assertEqual(list(PaqueteVuelo.objects.filter(paquete=p)), vuelos)
        self.assertEqual(self.tipo_habitacion.habitaciones_disponibles, 5)
        self.assertEqual(self.vuelo.asientos_disponibles, 100)

    def test_pantalla_de_edicion_muestra_el_resumen_de_cupos(self):
        p = self._paquete_con_ocupacion()
        r = self.client.get(reverse("packages:gestion_editar", args=[p.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Cupos totales")

    def test_actualizacion_concurrente_conserva_los_cupos_ocupados(self):
        p = self._paquete_con_ocupacion()
        obsoleto = Paquete.objects.get(pk=p.pk)  # disponible 7, ocupado 3
        Paquete.objects.filter(pk=p.pk).update(cupos_disponibles=4)  # ocupado 6
        obsoleto.cupos_total = 20
        guardar_con_capacidad(obsoleto, "cupos_total", "cupos_disponibles")
        p.refresh_from_db()
        self.assertEqual(p.cupos_total, 20)
        self.assertEqual(p.cupos_ocupados, 6)
        self.assertEqual(p.cupos_disponibles, 14)

    def test_servicio_rechaza_bajo_ocupado_tras_una_venta_concurrente(self):
        p = self._paquete_con_ocupacion()
        obsoleto = Paquete.objects.get(pk=p.pk)  # ocupado 3
        Paquete.objects.filter(pk=p.pk).update(cupos_disponibles=4)  # ocupado 6
        obsoleto.cupos_total = 5
        with self.assertRaises(CapacidadPorDebajoDeOcupado):
            guardar_con_capacidad(obsoleto, "cupos_total", "cupos_disponibles")
        p.refresh_from_db()
        self.assertEqual(p.cupos_total, 10)
        self.assertEqual(p.cupos_disponibles, 4)

    def test_lista_muestra_cupos_totales_ocupados_y_libres(self):
        self._paquete_con_ocupacion()
        r = self.client.get(reverse("packages:gestion_lista"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Cupos totales")
        self.assertContains(r, "Cupos ocupados")
        self.assertContains(r, "Cupos libres")


class GestionYCatalogoTests(TestCase):
    def setUp(self):
        u = User.objects.create_user("a@test.com", "a@test.com", "Clave-segura-123")
        u.groups.add(Group.objects.get(name=ROL_ADMIN))
        self.client.force_login(u)

    def _formset_vacio(self, prefix):
        return {
            f"{prefix}-TOTAL_FORMS": "0", f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "0", f"{prefix}-MAX_NUM_FORMS": "1000"}

    def test_admin_crea_destino_y_paquete_y_visitante_lo_ve(self):
        r = self.client.post(reverse("destinations:gestion_crear"), {
            "pais": Pais.objects.get(codigo_iso="BO").pk, "categoria": Categoria.objects.first().pk,
            "nombre": "Uyuni", "codigo_iata": "UYU", "descripcion": "Salar", "activo": "on"})
        self.assertEqual(r.status_code, 302)
        destino = Destino.objects.get(nombre="Uyuni")
        hoy = dt.date.today()
        datos = {
            "destino": destino.pk, "nombre": "Salar 3D", "descripcion": "x", "condiciones": "y",
            "fecha_salida": hoy + dt.timedelta(days=30), "fecha_retorno": hoy + dt.timedelta(days=33),
            "precio_persona": "1500.00", "cupos_total": 10,
            "venta_desde": hoy, "venta_hasta": hoy + dt.timedelta(days=20), "estado": "publicado"}
        for prefix in ("hoteles", "vuelos", "servicios", "actividades"):
            datos.update(self._formset_vacio(prefix))
        r = self.client.post(reverse("packages:gestion_crear"), datos)
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["form"].errors)
        p = Paquete.objects.get(nombre="Salar 3D")
        self.assertEqual(p.cupos_disponibles, 10)
        self.assertEqual(p.duracion_dias, 4)
        self.client.logout()  # visitante sin cuenta
        self.assertContains(self.client.get(reverse("packages:catalogo")), "Salar 3D")
        self.assertEqual(self.client.get(reverse("packages:detalle", args=[p.pk])).status_code, 200)
        self.assertContains(self.client.get(reverse("packages:comparar") + f"?ids={p.pk}"), "Salar 3D")

    def test_eliminar_es_logico(self):
        p = Pais.objects.first()
        d = Destino.objects.create(pais=p, categoria=Categoria.objects.first(), nombre="X")
        self.client.post(reverse("destinations:gestion_eliminar", args=[d.pk]))
        d.refresh_from_db()
        self.assertFalse(d.activo)


class CatalogoFiltrosTests(TestCase):          # CU-09
    """Los parámetros GET del catálogo público nunca deben provocar errores 500."""

    def setUp(self):
        self.pais = Pais.objects.get(codigo_iso="BO")
        self.categoria = Categoria.objects.first()
        self.lapaz = Destino.objects.create(
            pais=self.pais, categoria=self.categoria, nombre="La Paz", codigo_iata="LPB")
        self.uyuni = Destino.objects.create(
            pais=self.pais, categoria=self.categoria, nombre="Uyuni", codigo_iata="UYU")

        hoy = timezone.localdate()
        self.barato = self._paquete(
            "Económico La Paz", self.lapaz, "500.00", hoy + dt.timedelta(days=10), hoy)
        self.caro = self._paquete(
            "Premium Uyuni", self.uyuni, "1500.00", hoy + dt.timedelta(days=40), hoy)
        # No debe aparecer en el catálogo público.
        self.borrador = self._paquete(
            "Borrador oculto", self.lapaz, "100.00", hoy + dt.timedelta(days=15), hoy,
            estado="borrador")

    def _paquete(self, nombre, destino, precio, salida, hoy, estado="publicado"):
        return Paquete.objects.create(
            destino=destino, nombre=nombre, precio_persona=precio,
            fecha_salida=salida, fecha_retorno=salida + dt.timedelta(days=3),
            cupos_total=10, cupos_disponibles=10,
            venta_desde=hoy - dt.timedelta(days=1),
            venta_hasta=hoy + dt.timedelta(days=5), estado=estado)

    def _get(self, **params):
        r = self.client.get(reverse("packages:catalogo"), params)
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r.status_code, 500)
        return r

    def _assert_sin_paquetes(self, r):
        self.assertNotContains(r, self.barato.nombre)
        self.assertNotContains(r, self.caro.nombre)

    def _assert_catalogo_completo(self, r):
        self.assertContains(r, self.barato.nombre)
        self.assertContains(r, self.caro.nombre)
        self.assertNotContains(r, self.borrador.nombre)

    def _assert_filtro_invalido(self, r):
        self.assertContains(r, "no son válidos")
        self._assert_catalogo_completo(r)

    # ------------------------------------------------------------ sin filtros
    def test_catalogo_sin_filtros_muestra_solo_publicados(self):
        self._assert_catalogo_completo(self._get())

    def test_parametros_vacios_equivalen_a_sin_filtros(self):
        self._assert_catalogo_completo(self._get(
            q="", destino="", precio_min="", precio_max="",
            salida_desde="", salida_hasta=""))

    # ---------------------------------------------------------------- precios
    def test_precio_minimo_valido(self):
        r = self._get(precio_min="1000")
        self.assertContains(r, self.caro.nombre)
        self.assertNotContains(r, self.barato.nombre)
        self.assertNotContains(r, "no son válidos")

    def test_precio_maximo_valido(self):
        r = self._get(precio_max="1000")
        self.assertContains(r, self.barato.nombre)
        self.assertNotContains(r, self.caro.nombre)
        self.assertNotContains(r, "no son válidos")

    def test_rango_de_precios_valido(self):
        r = self._get(precio_min="400", precio_max="1600")
        self.assertContains(r, self.barato.nombre)
        self.assertContains(r, self.caro.nombre)

    def test_precio_negativo_es_rechazado(self):
        self._assert_filtro_invalido(self._get(precio_min="-1"))
        self._assert_filtro_invalido(self._get(precio_max="-100"))

    def test_precio_con_formato_incorrecto_es_rechazado(self):
        self._assert_filtro_invalido(self._get(precio_max="abc"))
        self._assert_filtro_invalido(self._get(precio_min="10,5,3"))

    def test_precio_minimo_mayor_que_el_maximo_es_rechazado(self):
        r = self._get(precio_min="2000", precio_max="1000")
        self._assert_filtro_invalido(r)
        self.assertContains(r, "no puede ser mayor que el precio máximo")

    # ----------------------------------------------------------------- fechas
    def test_fecha_de_salida_valida(self):
        salida = self.caro.fecha_salida.isoformat()
        r = self._get(salida_desde=salida)
        self.assertContains(r, self.caro.nombre)
        self.assertNotContains(r, self.barato.nombre)
        self.assertNotContains(r, "no son válidos")

    def test_rango_de_fechas_valido(self):
        r = self._get(
            salida_desde=self.barato.fecha_salida.isoformat(),
            salida_hasta=self.caro.fecha_salida.isoformat())
        self.assertContains(r, self.barato.nombre)
        self.assertContains(r, self.caro.nombre)
        self.assertNotContains(r, "no son válidos")

    def test_fecha_inexistente_es_rechazada(self):
        self._assert_filtro_invalido(self._get(salida_desde="2027-02-31"))
        self._assert_filtro_invalido(self._get(salida_hasta="2027-13-01"))

    def test_fecha_con_formato_incorrecto_es_rechazada(self):
        self._assert_filtro_invalido(self._get(salida_desde="ayer"))
        self._assert_filtro_invalido(self._get(salida_hasta="31/02/2027"))

    def test_fecha_inicial_posterior_a_la_final_es_rechazada(self):
        r = self._get(salida_desde="2027-06-01", salida_hasta="2027-05-01")
        self._assert_filtro_invalido(r)
        self.assertContains(r, "no puede ser posterior a la final")

    # --------------------------------------------------- combinaciones/destino
    def test_combinacion_de_filtros_validos(self):
        r = self._get(
            q="Uyuni", destino=self.uyuni.pk, precio_min="1000",
            precio_max="2000", salida_desde=self.caro.fecha_salida.isoformat(),
            salida_hasta=self.caro.fecha_salida.isoformat())
        self.assertContains(r, self.caro.nombre)
        self.assertNotContains(r, self.barato.nombre)
        self.assertNotContains(r, "no son válidos")

    def test_combinacion_de_parametros_invalidos(self):
        r = self._get(
            precio_min="-5", precio_max="abc",
            salida_desde="2027-02-31", salida_hasta="nada")
        self._assert_filtro_invalido(r)

    def test_destino_manipulado_es_rechazado(self):
        self._assert_filtro_invalido(self._get(destino="999999"))
        self._assert_filtro_invalido(self._get(destino="abc"))
        self._assert_filtro_invalido(self._get(destino=f"-{self.uyuni.pk}"))

    def test_ningun_parametro_invalido_produce_http_500(self):
        casos = [
            {"precio_min": "-1"}, {"precio_max": "-1"}, {"precio_max": "x"},
            {"precio_min": "10,5,3"}, {"precio_min": "999999999999999999"},
            {"precio_min": "3000", "precio_max": "100"},
            {"salida_desde": "2027-02-30"}, {"salida_hasta": "0000-00-00"},
            {"salida_desde": "2027-12-31", "salida_hasta": "2027-01-01"},
            {"destino": "no-existe"}, {"destino": ""},
            {"precio_min": "", "precio_max": "", "salida_desde": "", "salida_hasta": ""},
            {"q": "x" * 500},
        ]
        for params in casos:
            with self.subTest(params=params):
                self._get(**params)


class ComparadorPaquetesTests(TestCase):       # CU-10
    """El comparador acepta entre uno y tres paquetes, también en el servidor."""

    def setUp(self):
        self.pais = Pais.objects.get(codigo_iso="BO")
        self.categoria = Categoria.objects.first()
        self.destino = Destino.objects.create(
            pais=self.pais, categoria=self.categoria, nombre="La Paz", codigo_iata="LPB")
        hoy = timezone.localdate()
        self.paquetes = [
            self._paquete(f"Paquete {n}", f"{n}000.00", hoy + dt.timedelta(days=10 + n))
            for n in range(1, 5)
        ]
        self.oculto = self._paquete(
            "Paquete oculto", "100.00", hoy + dt.timedelta(days=15), estado="borrador")

    def _paquete(self, nombre, precio, salida, estado="publicado"):
        hoy = timezone.localdate()
        return Paquete.objects.create(
            destino=self.destino, nombre=nombre, precio_persona=precio,
            fecha_salida=salida, fecha_retorno=salida + dt.timedelta(days=3),
            cupos_total=10, cupos_disponibles=10,
            venta_desde=hoy - dt.timedelta(days=1),
            venta_hasta=hoy + dt.timedelta(days=5), estado=estado)

    def _comparar(self, ids):
        r = self.client.get(reverse("packages:comparar"), {"ids": ids})
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r.status_code, 500)
        return r

    def _assert_incluye(self, r, *paquetes):
        for p in paquetes:
            self.assertContains(r, p.nombre)

    def _assert_no_incluye(self, r, *paquetes):
        for p in paquetes:
            self.assertNotContains(r, p.nombre)

    # ------------------------------------------------------------- selecciones
    def test_comparar_un_paquete(self):
        self._assert_incluye(self._comparar([self.paquetes[0].pk]), self.paquetes[0])

    def test_comparar_dos_paquetes(self):
        self._assert_incluye(
            self._comparar([p.pk for p in self.paquetes[:2]]), *self.paquetes[:2])

    def test_comparar_tres_paquetes(self):
        r = self._comparar([p.pk for p in self.paquetes[:3]])
        self._assert_incluye(r, *self.paquetes[:3])
        self.assertNotContains(r, "máximo 3 paquetes")

    def test_cuarto_paquete_es_rechazado_por_el_servidor(self):
        r = self._comparar([p.pk for p in self.paquetes])
        self.assertContains(r, "Puedes comparar como máximo 3 paquetes")
        self._assert_no_incluye(r, *self.paquetes)

    def test_desmarcar_uno_y_elegir_otro(self):
        # La URL final refleja la selección vigente: 2, 3 y 4.
        r = self._comparar([p.pk for p in self.paquetes[1:4]])
        self._assert_incluye(r, *self.paquetes[1:4])
        self._assert_no_incluye(r, self.paquetes[0])

    def test_identificadores_duplicados_no_cuentan_dos_veces(self):
        p1, p2, p3 = self.paquetes[:3]
        r = self._comparar([p1.pk, p1.pk, p2.pk, p2.pk, p3.pk])
        self._assert_incluye(r, p1, p2, p3)
        self.assertNotContains(r, "máximo 3 paquetes")

    # --------------------------------------------------------------- validación
    def test_mas_de_tres_identificadores_por_url_es_rechazado(self):
        r = self._comparar([p.pk for p in self.paquetes] + [self.paquetes[0].pk])
        self.assertContains(r, "máximo 3 paquetes")
        self._assert_no_incluye(r, *self.paquetes)

    def test_identificador_inexistente_se_ignora(self):
        r = self._comparar([self.paquetes[0].pk, 999999])
        self._assert_incluye(r, self.paquetes[0])
        self._assert_no_incluye(r, *self.paquetes[1:])

    def test_identificador_no_numerico_no_produce_http_500(self):
        for valor in ("abc", "-1", "1.5", " "):
            with self.subTest(valor=valor):
                r = self._comparar([valor])
                self.assertContains(r, "identificadores no válidos")
                self._assert_no_incluye(r, *self.paquetes)

    def test_paquete_no_publicado_no_se_compara(self):
        r = self._comparar([self.oculto.pk])
        self._assert_no_incluye(r, self.oculto)
        self.assertContains(r, "Selecciona al menos un paquete")

    def test_sin_seleccion_muestra_ayuda(self):
        r = self._comparar([])
        self.assertContains(r, "Selecciona al menos un paquete")

    # --------------------------------------------------------------- interfaz
    def test_catalogo_muestra_el_limite_y_la_seleccion_multiple(self):
        r = self.client.get(reverse("packages:catalogo"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "máximo 3 paquetes")
        self.assertContains(r, 'id="comparador-form"')
        self.assertContains(r, 'class="form-check-input js-comparar"')
