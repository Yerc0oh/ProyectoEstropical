
from django.urls import path
from . import views

app_name = "support"

urlpatterns = [
    path(
        "mis-tickets/",
        views.mis_tickets,
        name="mis_tickets",
    ),
    path(
        "tickets/nuevo/",
        views.crear_ticket,
        name="crear",
    ),
    path(
        "tickets/<int:pk>/",
        views.detalle_ticket,
        name="detalle",
    ),
    path(
        "gestion/",
        views.gestion_tickets,
        name="gestion",
    ),
    path(
        "gestion/<int:pk>/",
        views.gestionar_ticket,
        name="gestionar",
    ),
]
