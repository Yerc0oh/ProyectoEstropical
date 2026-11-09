
"""Opciones del catálogo de Estropical para el chatbot."""
import json
import re
import unicodedata
from decimal import Decimal

from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.packages.models import Paquete
from apps.flights.models import Vuelo
from apps.hotels.models import Hotel


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(
        c for c in texto if not unicodedata.combining(c)
    ).lower()


def precio(valor):
    if valor is None:
        return None
    return str(valor.quantize(Decimal("0.01")))


def opciones_catalogo(pregunta):
    texto = normalizar(pregunta)
    tokens = set(re.findall(r"[a-z]{3,}", texto))

    stop = {
        "quiero", "viajar", "viaje", "para", "desde", "hasta",
        "donde", "tengo", "busco", "buscar", "necesito",
        "persona", "personas", "pasajeros", "economico",
        "economica", "barato", "barata", "precio", "precios",
        "cuanto", "cuesta", "opciones", "disponible",
        "disponibles", "mostrar", "recomienda", "recomendar",
        "puedes", "tienes", "con", "una", "unos", "dos",
        "tres", "cuatro", "cinco", "seis", "siete",
        "ocho", "nueve", "diez", "los", "las", "del",
        "por", "que", "hay", "mejor", "buen", "buenos",
        "entre", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre",
        "noviembre", "diciembre", "enero", "febrero",
        "hotel", "hoteles", "vuelo", "vuelos",
        "paquete", "paquetes", "ida", "vuelta",
        "solo", "tambien", "dias", "noche", "noches",
    }

    claves = tokens - stop
    hoy = timezone.localdate()
    resultados = []

    tipos = set()

    if any(x in texto for x in (
        "hotel", "alojamiento", "habitacion"
    )):
        tipos.add("hotel")

    if any(x in texto for x in (
        "vuelo", "volar", "avion", "pasaje"
    )):
        tipos.add("vuelo")

    if any(x in texto for x in (
        "paquete", "tour", "excursion"
    )):
        tipos.add("paquete")

    if not tipos:
        tipos = {"paquete", "vuelo", "hotel"}

    def coincide(*partes):
        if not claves:
            return True

        contenido = normalizar(
            " ".join(str(p or "") for p in partes)
        )
        return any(clave in contenido for clave in claves)

    if "paquete" in tipos:
        paquetes = (
            Paquete.objects.filter(
                estado="publicado",
                cupos_disponibles__gt=0,
                fecha_salida__gte=hoy,
                venta_desde__lte=hoy,
                venta_hasta__gte=hoy,
            )
            .select_related("destino")
            .order_by("fecha_salida")[:120]
        )

        for p in paquetes:
            if coincide(
                p.nombre, p.destino.nombre, p.descripcion
            ):
                resultados.append({
                    "tipo": "paquete",
                    "titulo": p.nombre,
                    "detalle": (
                        f"{p.destino.nombre} · "
                        f"Salida {p.fecha_salida:%d/%m/%Y} · "
                        f"{p.cupos_disponibles} cupos"
                    ),
                    "precio": precio(p.precio_persona),
                    "unidad": "por persona",
                    "url": reverse(
                        "packages:detalle", args=[p.pk]
                    ),
                })

    if "vuelo" in tipos:
        vuelos = (
            Vuelo.objects.filter(
                estado__in=["programado", "retrasado"],
                fecha_salida__gte=timezone.now(),
                asientos_disponibles__gt=0,
            )
            .select_related("origen", "destino")
            .order_by("fecha_salida")[:150]
        )

        for v in vuelos:
            if coincide(
                v.origen.nombre,
                v.destino.nombre,
                v.numero_vuelo,
            ):
                salida = timezone.localtime(v.fecha_salida)

                resultados.append({
                    "tipo": "vuelo",
                    "titulo": (
                        f"{v.origen.nombre} → "
                        f"{v.destino.nombre}"
                    ),
                    "detalle": (
                        f"{v.numero_vuelo} · "
                        f"{salida:%d/%m/%Y %H:%M} · "
                        f"{v.asientos_disponibles} asientos"
                    ),
                    "precio": precio(
                        v.precio_referencial
                    ),
                    "unidad": "referencial por persona",
                    "url": reverse(
                        "flights:detalle", args=[v.pk]
                    ),
                })

    if "hotel" in tipos:
        hoteles = (
            Hotel.objects.filter(activo=True)
            .select_related("destino")
            .order_by("nombre")[:150]
        )

        for h in hoteles:
            if coincide(
                h.nombre,
                h.destino.nombre,
                h.descripcion,
            ):
                resultados.append({
                    "tipo": "hotel",
                    "titulo": h.nombre,
                    "detalle": (
                        f"{h.destino.nombre} · "
                        f"{h.estrellas} estrellas · "
                        "Consultar fechas y tarifas"
                    ),
                    "precio": None,
                    "unidad": "",
                    "url": reverse(
                        "hotels:detalle", args=[h.pk]
                    ),
                })

    return resultados[:8]


@require_POST
def consultar_catalogo(request):
    try:
        payload = json.loads(request.body or "{}")
        pregunta = payload.get("pregunta", "")

        if (
            not isinstance(pregunta, str)
            or len(pregunta) > 1000
        ):
            return JsonResponse(
                {"error": "Consulta no válida."},
                status=400,
            )

        return JsonResponse({
            "opciones": opciones_catalogo(pregunta)
        })

    except (ValueError, TypeError):
        return JsonResponse(
            {"error": "JSON no válido."},
            status=400,
        )
