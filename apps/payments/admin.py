from django.contrib import admin

from .models import CierreCaja, Cuota, Factura, IntentoPagoQR, Pago, PagoProveedor, Reembolso

admin.site.register([Cuota, Reembolso, PagoProveedor])


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("nro_comprobante", "reserva", "metodo", "canal", "monto", "estado", "fecha_pago", "conciliado")
    list_filter = ("estado", "canal", "metodo", "conciliado")
    search_fields = ("nro_comprobante", "referencia_transaccion", "reserva__codigo")


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ("nro_factura", "reserva", "nit_cliente", "razon_social", "monto", "estado", "fecha_emision")
    list_filter = ("estado",)


@admin.register(CierreCaja)
class CierreCajaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "total_ingresos", "total_egresos", "saldo", "realizado_por")
    readonly_fields = ("saldo",)



@admin.register(IntentoPagoQR)
class IntentoPagoQRAdmin(admin.ModelAdmin):
    list_display = ("reserva", "monto", "estado", "fecha_creacion", "fecha_expiracion", "pago")
    list_filter = ("estado",)
    search_fields = ("reserva__codigo", "token")