
from django.contrib import admin
from .models import PreferenciaViaje


@admin.register(PreferenciaViaje)
class PreferenciaViajeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente",
        "nombre",
        "tipo_viaje",
        "presupuesto_minimo",
        "presupuesto_maximo",
        "activa",
    )

    list_filter = ("tipo_viaje", "activa")

    search_fields = (
        "nombre",
        "cliente__nombres",
        "cliente__apellidos",
    )

    filter_horizontal = ("destinos",)
