
from django.contrib import admin

from .models import Ticket, RespuestaTicket


class RespuestaTicketInline(admin.TabularInline):
    model = RespuestaTicket
    extra = 0
    readonly_fields = ("fecha_creacion",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "asunto",
        "cliente",
        "categoria",
        "prioridad",
        "estado",
        "fecha_creacion",
    )

    list_filter = (
        "categoria",
        "prioridad",
        "estado",
        "fecha_creacion",
    )

    search_fields = (
        "asunto",
        "descripcion",
        "cliente__username",
        "cliente__email",
    )

    readonly_fields = (
        "fecha_creacion",
        "fecha_actualizacion",
        "fecha_cierre",
    )

    inlines = [RespuestaTicketInline]
