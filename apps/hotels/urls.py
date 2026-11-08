from django.urls import path

from . import views

app_name = "hotels"

urlpatterns = [  # Solo Administrador (CU-14)
    path("gestion/hoteles/", views.HotelLista.as_view(), name="gestion_lista"),
    path("gestion/hoteles/nuevo/", views.HotelCrear.as_view(), name="gestion_crear"),
    path("gestion/hoteles/<int:pk>/editar/", views.HotelEditar.as_view(), name="gestion_editar"),
    path("gestion/hoteles/<int:pk>/eliminar/", views.HotelEliminar.as_view(), name="gestion_eliminar"),

    # Tipos de habitación de un hotel
    path("gestion/hoteles/<int:hotel_pk>/habitaciones/",
         views.TipoHabitacionLista.as_view(), name="gestion_habitaciones"),
    path("gestion/hoteles/<int:hotel_pk>/habitaciones/nuevo/",
         views.TipoHabitacionCrear.as_view(), name="gestion_habitacion_crear"),
    path("gestion/hoteles/<int:hotel_pk>/habitaciones/<int:pk>/editar/",
         views.TipoHabitacionEditar.as_view(), name="gestion_habitacion_editar"),
    path("gestion/hoteles/<int:hotel_pk>/habitaciones/<int:pk>/eliminar/",
         views.TipoHabitacionEliminar.as_view(), name="gestion_habitacion_eliminar"),

    # Tarifas por temporada de un tipo de habitación
    path("gestion/hoteles/<int:hotel_pk>/habitaciones/<int:tipo_pk>/tarifas/",
         views.TarifaHabitacionLista.as_view(), name="gestion_tarifas"),
    path("gestion/hoteles/<int:hotel_pk>/habitaciones/<int:tipo_pk>/tarifas/nuevo/",
         views.TarifaHabitacionCrear.as_view(), name="gestion_tarifa_crear"),
    path("gestion/hoteles/<int:hotel_pk>/habitaciones/<int:tipo_pk>/tarifas/<int:pk>/editar/",
         views.TarifaHabitacionEditar.as_view(), name="gestion_tarifa_editar"),
    path("gestion/hoteles/<int:hotel_pk>/habitaciones/<int:tipo_pk>/tarifas/<int:pk>/eliminar/",
         views.TarifaHabitacionEliminar.as_view(), name="gestion_tarifa_eliminar"),
]
