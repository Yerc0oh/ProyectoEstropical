
from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path(
        "",
        views.lista_notificaciones,
        name="lista"
    ),
    path(
        "<int:pk>/leer/",
        views.marcar_leida,
        name="marcar_leida"
    ),
    path(
        "leer-todas/",
        views.marcar_todas_leidas,
        name="marcar_todas"
    ),
]
