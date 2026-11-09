from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [  # Ninguna vista es pública: el middleware exige sesión en todas.
    # Cliente (el administrador también puede abrirlas para cualquier reserva)
    path("pagos/reserva/<int:pk>/pagar/", views.pagar, name="pagar"),                              # CU-26
    path("pagos/<int:pk>/", views.pago_resultado, name="pago_resultado"),
    path("pagos/<int:pk>/comprobante.pdf", views.comprobante_pdf, name="comprobante_pdf"),
    path("pagos/reserva/<int:pk>/cuotas/", views.cuotas, name="cuotas"),                           # CU-27
    path("pagos/reserva/<int:pk>/cuotas/anular/", views.anular_cuotas, name="anular_cuotas"),
    path("pagos/estado-de-cuenta/", views.estados_de_cuenta, name="estados_de_cuenta"),            # CU-29
    path("pagos/estado-de-cuenta/<int:pk>/", views.estado_cuenta, name="estado_cuenta"),
    path("pagos/facturas/", views.mis_facturas, name="mis_facturas"),                              # CU-31
    path("pagos/facturas/<int:pk>/pdf/", views.factura_pdf, name="factura_pdf"),
    # Gestión: solo Administrador
    path("gestion/pagos/", views.gestion_pagos, name="gestion_pagos"),
    path("gestion/pagos/ventanilla/", views.ventanilla, name="ventanilla"),                        # CU-28
    path("gestion/facturas/", views.gestion_facturas, name="gestion_facturas"),                    # CU-30
    path("gestion/facturas/emitir/<int:reserva_pk>/", views.emitir_factura, name="emitir_factura"),
    path("gestion/facturas/<int:pk>/anular/", views.anular_factura, name="anular_factura"),        # CU-32
    path("gestion/reembolsos/", views.reembolsos, name="reembolsos"),                              # CU-33
    path("gestion/reembolsos/<int:pk>/", views.procesar_reembolso, name="procesar_reembolso"),
    path("gestion/conciliacion/", views.conciliacion, name="conciliacion"),                        # CU-34
    path("gestion/conciliacion/<int:pk>/", views.conciliar, name="conciliar"),
    path("gestion/cuentas-por-cobrar/", views.cuentas_por_cobrar, name="cuentas_por_cobrar"),      # CU-35
    path("gestion/pagos-proveedores/", views.PagoProveedorLista.as_view(), name="pagos_proveedor"),  # CU-36
    path("gestion/pagos-proveedores/nuevo/", views.PagoProveedorCrear.as_view(), name="pago_proveedor_crear"),
    path("gestion/pagos-proveedores/<int:pk>/pagado/", views.pago_proveedor_pagado, name="pago_proveedor_pagado"),
    path("gestion/caja/", views.caja, name="caja"),                                                # CU-37
    path("gestion/caja/<int:pk>/", views.cierre_detalle, name="cierre_detalle"),
]
