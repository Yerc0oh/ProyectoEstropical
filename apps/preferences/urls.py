
from django.urls import path
from . import views

app_name = "preferences"

urlpatterns = [
    path(
        "preferencias/",
        views.lista_preferencias,
        name="lista"
    ),
    path(
        "preferencias/nueva/",
        views.crear_preferencia,
        name="crear"
    ),
    path(
        "preferencias/<int:pk>/",
        views.detalle_preferencia,
        name="detalle"
    ),
    path(
        "preferencias/<int:pk>/editar/",
        views.editar_preferencia,
        name="editar"
    ),
    path(
        "preferencias/<int:pk>/eliminar/",
        views.eliminar_preferencia,
        name="eliminar"
    ),
]
