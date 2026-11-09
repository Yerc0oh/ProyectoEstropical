
from django.contrib import admin
from .models import Resena


@admin.register(Resena)
class ResenaAdmin(admin.ModelAdmin):
    list_display = (
        "cliente",
        "paquete",
        "calificacion",
        "estado",
        "fecha_creacion"
    )

    list_filter = (
        "estado",
        "calificacion",
        "fecha_creacion"
    )

    search_fields = (
        "cliente__username",
        "paquete__nombre",
        "comentario"
    )

    readonly_fields = (
        "cliente",
        "paquete",
        "fecha_creacion",
        "fecha_actualizacion"
    )

    actions = ["aprobar_resenas", "rechazar_resenas"]

    @admin.action(description="Aprobar reseñas seleccionadas")
    def aprobar_resenas(self, request, queryset):
        queryset.update(estado="aprobada")

    @admin.action(description="Rechazar reseñas seleccionadas")
    def rechazar_resenas(self, request, queryset):
        queryset.update(estado="rechazada")
