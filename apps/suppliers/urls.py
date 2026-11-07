from django.urls import path

from . import views

app_name = "suppliers"

urlpatterns = [  # Todo el módulo es solo para Administrador (CU-13)
    path("gestion/proveedores/", views.ProveedorLista.as_view(), name="gestion_lista"),
    path("gestion/proveedores/nuevo/", views.ProveedorCrear.as_view(), name="gestion_crear"),
    path("gestion/proveedores/<int:pk>/editar/", views.ProveedorEditar.as_view(), name="gestion_editar"),
    path("gestion/proveedores/<int:pk>/eliminar/", views.ProveedorEliminar.as_view(), name="gestion_eliminar"),
]
