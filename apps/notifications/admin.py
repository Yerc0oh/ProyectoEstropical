
from django.contrib import admin
from .models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):

    list_display = (
        "usuario",
        "tipo",
        "titulo",
        "leida",
        "fecha_creacion",
    )

    list_filter = (
        "tipo",
        "leida",
        "fecha_creacion",
    )

    search_fields = (
        "titulo",
        "mensaje",
        "usuario__username",
    )

    readonly_fields = ("fecha_creacion",)
