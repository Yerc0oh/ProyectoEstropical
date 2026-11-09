
from django.urls import path
from . import views

app_name = "reviews"

urlpatterns = [
    path(
        "mis-resenas/",
        views.mis_resenas,
        name="mis_resenas"
    ),
    path(
        "crear/<int:paquete_id>/",
        views.crear_resena,
        name="crear"
    ),
    path(
        "editar/<int:pk>/",
        views.editar_resena,
        name="editar"
    ),
    path(
        "eliminar/<int:pk>/",
        views.eliminar_resena,
        name="eliminar"
    ),
    path(
        "paquete/<int:paquete_id>/",
        views.resenas_paquete,
        name="paquete"
    ),
]
