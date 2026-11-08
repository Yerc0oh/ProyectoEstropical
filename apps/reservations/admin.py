from django.contrib import admin

from .models import ConfirmacionProveedor, DocumentoViaje, ParametroSistema, Pasajero, Promocion, Reserva

admin.site.register([ParametroSistema, DocumentoViaje, ConfirmacionProveedor])


@admin.register(Promocion)          # gestión completa de cupones: Sprint 6 (CU-50)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ("codigo", "tipo_descuento", "valor", "vigente_desde", "vigente_hasta", "usos_maximos", "activo")
    list_filter = ("activo", "tipo_descuento")
    search_fields = ("codigo",)


class PasajeroInline(admin.TabularInline):
    model = Pasajero
    extra = 0


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "cliente", "paquete", "cantidad_pasajeros", "total", "estado", "fecha_reserva")
    list_filter = ("estado",)
    search_fields = ("codigo", "cliente__nombres", "cliente__apellidos")
    readonly_fields = ("subtotal", "total")
    inlines = [PasajeroInline]
