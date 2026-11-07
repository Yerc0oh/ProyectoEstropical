from django.urls import path

from apps.core.access import public

from . import views

app_name = "destinations"

urlpatterns = [
    # Público (sin cuenta, cliente o administrador)
    path("destinos/", public(views.CatalogoDestinosView.as_view()), name="catalogo"),
    path("destinos/<int:pk>/", public(views.DetalleDestinoView.as_view()), name="detalle"),
    # Gestión: solo Administrador
    path("gestion/destinos/", views.DestinoListaGestion.as_view(), name="gestion_lista"),
    path("gestion/destinos/nuevo/", views.DestinoCrear.as_view(), name="gestion_crear"),
    path("gestion/destinos/<int:pk>/editar/", views.DestinoEditar.as_view(), name="gestion_editar"),
    path("gestion/destinos/<int:pk>/eliminar/", views.DestinoEliminar.as_view(), name="gestion_eliminar"),
]
