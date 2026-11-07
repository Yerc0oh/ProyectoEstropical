from apps.core.views_base import (AdminCreateView, AdminListView,
                                  AdminSoftDeleteView, AdminUpdateView)

from .forms import VueloForm
from .models import Vuelo


class VueloLista(AdminListView):
    model = Vuelo
    titulo = "Gestionar vuelos"
    columnas = [("Vuelo", "numero_vuelo"), ("Origen", "origen"), ("Destino", "destino"),
                ("Salida", "fecha_salida"), ("Asientos libres", "asientos_disponibles"),
                ("Estado", "get_estado_display")]
    url_crear = "flights:gestion_crear"
    url_editar = "flights:gestion_editar"
    url_eliminar = "flights:gestion_eliminar"


class VueloCrear(AdminCreateView):
    model = Vuelo
    form_class = VueloForm
    titulo = "Nuevo vuelo"
    url_listado = "flights:gestion_lista"


class VueloEditar(AdminUpdateView):
    model = Vuelo
    form_class = VueloForm
    titulo = "Editar vuelo"
    url_listado = "flights:gestion_lista"


class VueloEliminar(AdminSoftDeleteView):
    """'Eliminar' un vuelo = marcarlo como cancelado."""
    model = Vuelo
    url_listado = "flights:gestion_lista"
    campo = "estado"
    valor = "cancelado"
