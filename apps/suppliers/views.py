from apps.core.views_base import (AdminCreateView, AdminListView,
                                  AdminSoftDeleteView, AdminUpdateView)

from .forms import ProveedorForm
from .models import Proveedor


class ProveedorLista(AdminListView):
    model = Proveedor
    titulo = "Gestionar proveedores"
    columnas = [("Razón social", "razon_social"), ("NIT", "nit"), ("Tipo", "get_tipo_display"),
                ("Validación", "get_estado_validacion_display"), ("Activo", "activo")]
    url_crear = "suppliers:gestion_crear"
    url_editar = "suppliers:gestion_editar"
    url_eliminar = "suppliers:gestion_eliminar"


class ProveedorCrear(AdminCreateView):
    model = Proveedor
    form_class = ProveedorForm
    titulo = "Nuevo proveedor"
    url_listado = "suppliers:gestion_lista"


class ProveedorEditar(AdminUpdateView):
    model = Proveedor
    form_class = ProveedorForm
    titulo = "Editar proveedor"
    url_listado = "suppliers:gestion_lista"


class ProveedorEliminar(AdminSoftDeleteView):
    model = Proveedor
    url_listado = "suppliers:gestion_lista"
