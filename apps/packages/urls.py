from django.urls import path

from apps.core.access import public

from . import views

app_name = "packages"

urlpatterns = [
    # Público
    path("paquetes/", public(views.CatalogoPaquetesView.as_view()), name="catalogo"),
    path("paquetes/comparar/", public(views.comparar_paquetes), name="comparar"),
    path("paquetes/<int:pk>/", public(views.DetallePaqueteView.as_view()), name="detalle"),
    # Gestión: solo Administrador
    path("gestion/paquetes/", views.PaqueteLista.as_view(), name="gestion_lista"),
    path("gestion/paquetes/nuevo/", views.PaqueteCrear.as_view(), name="gestion_crear"),
    path("gestion/paquetes/<int:pk>/editar/", views.PaqueteEditar.as_view(), name="gestion_editar"),
    path("gestion/paquetes/<int:pk>/eliminar/", views.PaqueteEliminar.as_view(), name="gestion_eliminar"),
]
