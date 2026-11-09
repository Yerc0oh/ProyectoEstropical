from django.urls import path

from . import views

app_name = "flights"

urlpatterns = [  # Solo Administrador (CU-15)
    path("gestion/vuelos/", views.VueloLista.as_view(), name="gestion_lista"),
    path("gestion/vuelos/nuevo/", views.VueloCrear.as_view(), name="gestion_crear"),
    path("gestion/vuelos/<int:pk>/editar/", views.VueloEditar.as_view(), name="gestion_editar"),
    path("gestion/vuelos/<int:pk>/eliminar/", views.VueloEliminar.as_view(), name="gestion_eliminar"),

    
    # Catálogo público de vuelos
    path(
        "vuelos/",
        views.VueloCatalogo.as_view(),
        name="catalogo"
    ),
    path(
        "vuelos/<int:pk>/",
        views.VueloDetalle.as_view(),
        name="detalle"
    ),

]
