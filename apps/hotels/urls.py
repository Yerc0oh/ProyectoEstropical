from django.urls import path

from . import views

app_name = "hotels"

urlpatterns = [  # Solo Administrador (CU-14)
    path("gestion/hoteles/", views.HotelLista.as_view(), name="gestion_lista"),
    path("gestion/hoteles/nuevo/", views.HotelCrear.as_view(), name="gestion_crear"),
    path("gestion/hoteles/<int:pk>/editar/", views.HotelEditar.as_view(), name="gestion_editar"),
    path("gestion/hoteles/<int:pk>/eliminar/", views.HotelEliminar.as_view(), name="gestion_eliminar"),
]
