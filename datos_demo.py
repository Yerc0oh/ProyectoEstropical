"""Datos de demostración: destinos, proveedores, vuelos, hoteles y 7 paquetes turísticos.

Uso (con el entorno virtual activo, desde la carpeta del proyecto):
    python manage.py shell -c "exec(open('datos_demo.py', encoding='utf-8').read())"

Se puede ejecutar varias veces: si un paquete ya existe (mismo nombre) no lo duplica.
Las fechas se calculan a partir de hoy, así los paquetes siempre quedan a la venta.
Nombres de empresas, hoteles y NIT son ficticios.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.destinations.models import Categoria, Destino, Pais
from apps.flights.models import Vuelo
from apps.hotels.models import Hotel, TarifaHabitacion, TipoHabitacion
from apps.packages.models import (Paquete, PaqueteActividad, PaqueteHotel, PaqueteServicio,
                                  PaqueteVuelo, Servicio)
from apps.suppliers.models import Proveedor

HOY = timezone.localdate()


def momento(fecha, hora, minuto=0):
    return timezone.make_aware(datetime.combine(fecha, time(hora, minuto)))


def destino(iso, categoria, nombre, iata, descripcion):
    pais = Pais.objects.get(codigo_iso=iso)
    cat, _ = Categoria.objects.get_or_create(nombre=categoria)
    obj = (Destino.objects.filter(codigo_iata=iata).first() if iata else None) \
        or Destino.objects.filter(pais=pais, nombre=nombre).first()
    if obj:
        return obj
    return Destino.objects.create(pais=pais, categoria=cat, nombre=nombre, codigo_iata=iata,
                                  descripcion=descripcion)


def proveedor(razon_social, nit, tipo, contacto, correo, telefono):
    obj, _ = Proveedor.objects.get_or_create(nit=nit, defaults={
        "razon_social": razon_social, "tipo": tipo, "nombre_contacto": contacto, "correo": correo,
        "telefono": telefono, "estado_validacion": "validado"})
    return obj


def vuelo(prov, numero, origen, dest, salida, horas, precio, asientos=60):
    obj, _ = Vuelo.objects.get_or_create(numero_vuelo=numero, fecha_salida=salida, defaults={
        "proveedor": prov, "origen": origen, "destino": dest, "fecha_llegada": salida + timedelta(hours=horas),
        "asientos_total": asientos, "asientos_disponibles": asientos, "precio_referencial": precio})
    return obj


def habitacion(prov, dest, hotel_nombre, estrellas, direccion, tipo, capacidad, total, precio_noche):
    hotel, _ = Hotel.objects.get_or_create(nombre=hotel_nombre, destino=dest, defaults={
        "proveedor": prov, "estrellas": estrellas, "direccion": direccion,
        "descripcion": f"Hotel {estrellas} estrellas en {dest.nombre}."})
    th, creado = TipoHabitacion.objects.get_or_create(hotel=hotel, nombre=tipo, defaults={
        "capacidad": capacidad, "habitaciones_total": total, "habitaciones_disponibles": total})
    if creado:
        TarifaHabitacion.objects.create(tipo_habitacion=th, fecha_inicio=HOY,
                                        fecha_fin=HOY + timedelta(days=365), precio_noche=precio_noche)
    return th


SERVICIOS = {
    "Traslado aeropuerto": "Traslado aeropuerto - hotel - aeropuerto",
    "Desayuno": "Desayuno buffet diario",
    "Guía bilingüe": "Guía en español e inglés",
    "Entradas": "Entradas a los atractivos del itinerario",
    "Seguro de viaje": "Asistencia médica en viaje",
    "Transporte terrestre": "Bus turístico durante el recorrido",
    "Almuerzos": "Almuerzos indicados en el itinerario",
}


def servicio(nombre):
    obj, _ = Servicio.objects.get_or_create(nombre=nombre, defaults={"descripcion": SERVICIOS[nombre]})
    return obj


def paquete(datos, vuelos=(), hoteles=(), servicios=(), actividades=()):
    if Paquete.objects.filter(nombre=datos["nombre"]).exists():
        print(f"  ya existe: {datos['nombre']}")
        return
    salida = HOY + timedelta(days=datos.pop("dias_hasta_salida"))
    duracion = datos.pop("duracion")
    p = Paquete.objects.create(
        fecha_salida=salida, fecha_retorno=salida + timedelta(days=duracion - 1),
        venta_desde=HOY, venta_hasta=salida - timedelta(days=3), estado="publicado", **datos)
    for v, tramo in vuelos:
        PaqueteVuelo.objects.create(paquete=p, vuelo=v, tramo=tramo)
    for th, noches in hoteles:
        PaqueteHotel.objects.create(paquete=p, tipo_habitacion=th, noches=noches)
    for nombre, detalle in servicios:
        PaqueteServicio.objects.create(paquete=p, servicio=servicio(nombre), detalle=detalle)
    for i, (dia, hora, titulo, descripcion) in enumerate(actividades, start=1):
        PaqueteActividad.objects.create(paquete=p, dia=dia, orden=i, titulo=titulo, descripcion=descripcion,
                                        hora_inicio=time(*hora) if hora else None)
    print(f"  creado: {p.nombre} (sale {p.fecha_salida:%d/%m/%Y}, Bs {p.precio_persona})")
    return p


@transaction.atomic
def cargar():
    print("Cargando datos de demostración...")
    # ------------------------------------------------------------ destinos
    lpz = destino("BO", "Ciudad", "La Paz", "LPB", "Sede de gobierno de Bolivia, punto de partida de los viajes.")
    cuz = destino("PE", "Cultural", "Cusco", "CUZ", "Antigua capital inca y puerta de entrada a Machu Picchu.")
    uyu = destino("BO", "Naturaleza", "Uyuni", "UYU", "El salar más grande del mundo.")
    rio = destino("BR", "Playa", "Río de Janeiro", "GIG", "Playas de Copacabana e Ipanema, Cristo Redentor.")
    bue = destino("AR", "Ciudad", "Buenos Aires", "EZE", "Tango, gastronomía y arquitectura europea.")
    spa = destino("CL", "Aventura", "San Pedro de Atacama", "CJC", "Desierto, géiseres y lagunas altiplánicas.")
    mad = destino("ES", "Cultural", "Madrid", "MAD", "Museos, plazas históricas y vida nocturna.")
    cop = destino("BO", "Naturaleza", "Copacabana", None, "Lago Titicaca e Isla del Sol.")

    # ------------------------------------------------------------ proveedores (ficticios)
    aero = proveedor("Aerolínea Andina S.A.", "900100101", "aerolinea", "Carla Rojas", "reservas@andina.test", "22441100")
    aero_int = proveedor("Sudamérica Air Ltda.", "900100102", "aerolinea", "Jorge Paz", "grupos@sudair.test", "22441200")
    hoteles = proveedor("Cadena Hotelera Inti S.R.L.", "900100201", "hotel", "Lucía Mamani", "ventas@inti.test", "22442100")
    proveedor("Operadora Altiplano Tours", "900100301", "operador", "Raúl Quispe", "ops@altiplano.test", "22443100")
    proveedor("Transportes Titicaca", "900100401", "transporte", "Mario Choque", "info@titicaca.test", "22444100")

    # ------------------------------------------------------------ paquetes
    s1 = HOY + timedelta(days=30)
    paquete({"nombre": "Cusco y Machu Picchu", "destino": cuz, "dias_hasta_salida": 30, "duracion": 5,
             "precio_persona": Decimal("4850.00"), "cupos_total": 20,
             "descripcion": "Recorre la capital del imperio inca, el Valle Sagrado y la ciudadela de Machu Picchu.",
             "condiciones": "Incluye vuelos ida y vuelta desde La Paz. Pasaporte o CI vigente. No incluye cenas."},
            vuelos=[(vuelo(aero, "AN201", lpz, cuz, momento(s1, 7, 30), 1.5, 950), "ida"),
                    (vuelo(aero, "AN202", cuz, lpz, momento(s1 + timedelta(days=4), 17), 1.5, 950), "vuelta")],
            hoteles=[(habitacion(hoteles, cuz, "Hotel Inti Wasi Cusco", 4, "Calle Plateros 320", "Doble", 2, 30, 420), 4)],
            servicios=[("Traslado aeropuerto", ""), ("Desayuno", "4 desayunos"), ("Guía bilingüe", ""),
                       ("Entradas", "Machu Picchu, Sacsayhuamán y Valle Sagrado"), ("Seguro de viaje", "")],
            actividades=[(1, (10, 0), "Llegada y aclimatación", "Mate de coca y descanso en el hotel."),
                         (1, (15, 0), "City tour", "Catedral, Qoricancha y Sacsayhuamán."),
                         (2, (8, 0), "Valle Sagrado", "Pisac, almuerzo en Urubamba y Ollantaytambo."),
                         (3, (5, 30), "Machu Picchu", "Tren a Aguas Calientes y visita guiada a la ciudadela."),
                         (4, None, "Día libre", "Mercado de San Pedro y barrio de San Blas."),
                         (5, (14, 0), "Retorno", "Traslado al aeropuerto.")])

    s2 = HOY + timedelta(days=21)
    paquete({"nombre": "Salar de Uyuni 3 días", "destino": uyu, "dias_hasta_salida": 21, "duracion": 3,
             "precio_persona": Decimal("1650.00"), "cupos_total": 15,
             "descripcion": "Tour en 4x4 por el Salar, la Isla Incahuasi y las lagunas de colores.",
             "condiciones": "Llevar ropa abrigada: de noche baja a -10 °C. Altitud mayor a 3.600 m."},
            vuelos=[(vuelo(aero, "AN310", lpz, uyu, momento(s2, 6, 45), 1, 600), "ida"),
                    (vuelo(aero, "AN311", uyu, lpz, momento(s2 + timedelta(days=2), 18), 1, 600), "vuelta")],
            hoteles=[(habitacion(hoteles, uyu, "Hotel de Sal Tayka", 3, "Colchani", "Doble", 2, 15, 380), 2)],
            servicios=[("Transporte terrestre", "Vagoneta 4x4 con chofer"), ("Almuerzos", "3 almuerzos"),
                       ("Desayuno", ""), ("Guía bilingüe", "")],
            actividades=[(1, (9, 0), "Cementerio de trenes", ""),
                         (1, (12, 0), "Salar e Isla Incahuasi", "Almuerzo sobre el salar y fotos de perspectiva."),
                         (2, (7, 0), "Lagunas altiplánicas", "Laguna Colorada y flamencos."),
                         (3, (5, 0), "Géiseres Sol de Mañana", "Aguas termales de Polques y retorno.")])

    s3 = HOY + timedelta(days=45)
    paquete({"nombre": "Río de Janeiro playa y samba", "destino": rio, "dias_hasta_salida": 45, "duracion": 6,
             "precio_persona": Decimal("6990.00"), "cupos_total": 25,
             "descripcion": "Playas de Copacabana e Ipanema, Cristo Redentor y Pan de Azúcar.",
             "condiciones": "Pasaporte o CI vigente (Mercosur). Recomendada vacuna contra fiebre amarilla."},
            vuelos=[(vuelo(aero_int, "SA840", lpz, rio, momento(s3, 9), 4, 2100), "ida"),
                    (vuelo(aero_int, "SA841", rio, lpz, momento(s3 + timedelta(days=5), 13), 4, 2100), "vuelta")],
            hoteles=[(habitacion(hoteles, rio, "Hotel Atlântico Copacabana", 4, "Av. Atlântica 1500", "Doble vista al mar", 2, 40, 690), 5)],
            servicios=[("Traslado aeropuerto", ""), ("Desayuno", ""), ("Seguro de viaje", ""),
                       ("Entradas", "Cristo Redentor y teleférico Pan de Azúcar")],
            actividades=[(1, (15, 0), "Llegada y playa de Copacabana", ""),
                         (2, (8, 30), "Cristo Redentor", "Subida en tren del Corcovado."),
                         (3, (9, 0), "Pan de Azúcar", "Teleférico y mirador."),
                         (4, None, "Día libre en Ipanema", ""),
                         (5, (20, 0), "Noche de samba", "Show en Lapa."),
                         (6, (10, 0), "Retorno", "")])

    s4 = HOY + timedelta(days=60)
    paquete({"nombre": "Buenos Aires clásico", "destino": bue, "dias_hasta_salida": 60, "duracion": 5,
             "precio_persona": Decimal("5400.00"), "cupos_total": 20,
             "descripcion": "Caminito, Recoleta, Puerto Madero y cena show de tango.",
             "condiciones": "CI o pasaporte vigente. Propinas no incluidas."},
            vuelos=[(vuelo(aero_int, "SA500", lpz, bue, momento(s4, 11), 3.5, 1800), "ida"),
                    (vuelo(aero_int, "SA501", bue, lpz, momento(s4 + timedelta(days=4), 16), 3.5, 1800), "vuelta")],
            hoteles=[(habitacion(hoteles, bue, "Hotel Recoleta Plaza", 4, "Av. Callao 1200", "Doble", 2, 25, 560), 4)],
            servicios=[("Traslado aeropuerto", ""), ("Desayuno", ""), ("Guía bilingüe", "City tour"),
                       ("Seguro de viaje", "")],
            actividades=[(1, (16, 0), "Llegada y Puerto Madero", ""),
                         (2, (9, 0), "City tour", "Plaza de Mayo, La Boca y Caminito."),
                         (3, (10, 0), "Recoleta y Palermo", ""),
                         (3, (20, 30), "Cena show de tango", ""),
                         (4, (9, 0), "Tigre y Delta del Paraná", "Paseo en lancha."),
                         (5, (12, 0), "Retorno", "")])

    s5 = HOY + timedelta(days=35)
    paquete({"nombre": "San Pedro de Atacama aventura", "destino": spa, "dias_hasta_salida": 35, "duracion": 4,
             "precio_persona": Decimal("3900.00"), "cupos_total": 12,
             "descripcion": "Valle de la Luna, géiseres del Tatio y lagunas altiplánicas.",
             "condiciones": "Vuelo a Calama y traslado terrestre de 1 h 30 min a San Pedro."},
            vuelos=[(vuelo(aero_int, "SA620", lpz, spa, momento(s5, 8), 2, 1300), "ida"),
                    (vuelo(aero_int, "SA621", spa, lpz, momento(s5 + timedelta(days=3), 19), 2, 1300), "vuelta")],
            hoteles=[(habitacion(hoteles, spa, "Hostal Licancabur", 3, "Caracoles 140", "Triple", 3, 10, 350), 3)],
            servicios=[("Transporte terrestre", "Calama - San Pedro y excursiones"), ("Desayuno", ""),
                       ("Entradas", "Valle de la Luna y Tatio")],
            actividades=[(1, (17, 0), "Valle de la Luna", "Atardecer en el mirador."),
                         (2, (4, 30), "Géiseres del Tatio", ""),
                         (3, (8, 0), "Lagunas altiplánicas", "Miscanti y Miñiques."),
                         (4, (15, 0), "Retorno", "")])

    s6 = HOY + timedelta(days=90)
    paquete({"nombre": "Madrid y Toledo", "destino": mad, "dias_hasta_salida": 90, "duracion": 8,
             "precio_persona": Decimal("14500.00"), "cupos_total": 18,
             "descripcion": "Museo del Prado, Palacio Real, excursión a Toledo y Segovia.",
             "condiciones": "Pasaporte con vigencia mínima de 6 meses. Requiere seguro de viaje Schengen (incluido)."},
            vuelos=[(vuelo(aero_int, "SA900", lpz, mad, momento(s6, 22), 12, 6500, asientos=80), "ida"),
                    (vuelo(aero_int, "SA901", mad, lpz, momento(s6 + timedelta(days=7), 12), 12, 6500, asientos=80), "vuelta")],
            hoteles=[(habitacion(hoteles, mad, "Hotel Gran Vía Centro", 4, "Gran Vía 45", "Doble", 2, 30, 900), 6)],
            servicios=[("Traslado aeropuerto", ""), ("Desayuno", ""), ("Seguro de viaje", "Cobertura Schengen"),
                       ("Guía bilingüe", "Excursiones"), ("Entradas", "Museo del Prado y Palacio Real")],
            actividades=[(2, (14, 0), "Llegada a Madrid", ""),
                         (3, (9, 30), "Madrid de los Austrias", "Plaza Mayor, Puerta del Sol y Palacio Real."),
                         (4, (10, 0), "Museo del Prado y Retiro", ""),
                         (5, (8, 0), "Excursión a Toledo", ""),
                         (6, (8, 0), "Excursión a Segovia", "Acueducto y Alcázar."),
                         (7, None, "Día libre", ""),
                         (8, (10, 0), "Retorno", "")])

    paquete({"nombre": "Copacabana e Isla del Sol", "destino": cop, "dias_hasta_salida": 14, "duracion": 2,
             "precio_persona": Decimal("690.00"), "cupos_total": 30,
             "descripcion": "Escapada de fin de semana al Lago Titicaca en bus turístico.",
             "condiciones": "Salida desde La Paz en bus. Llevar protector solar y abrigo."},
            hoteles=[(habitacion(hoteles, cop, "Hotel Mirador del Lago", 3, "Av. Costanera", "Doble", 2, 20, 280), 1)],
            servicios=[("Transporte terrestre", "Bus La Paz - Copacabana ida y vuelta"), ("Desayuno", ""),
                       ("Almuerzos", "Trucha del lago"), ("Guía bilingüe", "")],
            actividades=[(1, (7, 0), "Salida de La Paz", "Cruce del estrecho de Tiquina."),
                         (1, (12, 0), "Basílica y Cerro Calvario", ""),
                         (2, (8, 0), "Isla del Sol", "Lancha, escalinata inca y Pilkokaina."),
                         (2, (16, 0), "Retorno a La Paz", "")])
    print("Listo.")


cargar()
