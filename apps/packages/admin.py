from django.contrib import admin

from .models import (Paquete, PaqueteActividad, PaqueteHotel, PaqueteServicio,
                     PaqueteVuelo, Servicio)

admin.site.register([Servicio, PaqueteActividad])


class PaqueteHotelInline(admin.TabularInline):
    model = PaqueteHotel
    extra = 0


class PaqueteVueloInline(admin.TabularInline):
    model = PaqueteVuelo
    extra = 0


class PaqueteServicioInline(admin.TabularInline):
    model = PaqueteServicio
    extra = 0


@admin.register(Paquete)
class PaqueteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "destino", "fecha_salida", "precio_persona", "cupos_disponibles", "estado")
    list_filter = ("estado", "destino")
    inlines = [PaqueteHotelInline, PaqueteVueloInline, PaqueteServicioInline]
