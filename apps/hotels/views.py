from apps.core.views_base import (AdminCreateView, AdminListView,
                                  AdminSoftDeleteView, AdminUpdateView)

from .forms import HotelForm
from .models import Hotel


class HotelLista(AdminListView):
    model = Hotel
    titulo = "Gestionar hoteles"
    columnas = [("Hotel", "nombre"), ("Destino", "destino"), ("Estrellas", "estrellas"),
                ("Proveedor", "proveedor"), ("Activo", "activo")]
    url_crear = "hotels:gestion_crear"
    url_editar = "hotels:gestion_editar"
    url_eliminar = "hotels:gestion_eliminar"


class HotelCrear(AdminCreateView):
    model = Hotel
    form_class = HotelForm
    titulo = "Nuevo hotel"
    url_listado = "hotels:gestion_lista"


class HotelEditar(AdminUpdateView):
    model = Hotel
    form_class = HotelForm
    titulo = "Editar hotel"
    url_listado = "hotels:gestion_lista"


class HotelEliminar(AdminSoftDeleteView):
    model = Hotel
    url_listado = "hotels:gestion_lista"
