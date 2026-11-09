from django.urls import path

from . import views

app_name = "reservations"

urlpatterns = [  # Ninguna vista es pública: el middleware exige sesión en todas.
    # Cliente (y administrador, que también puede abrir cualquier reserva)
    path("reservas/", views.mis_reservas, name="mis_reservas"),                                   # CU-19
    path("reservas/nueva/<int:paquete_pk>/", views.reservar, name="reservar"),                    # CU-18
    path("reservas/<int:pk>/", views.detalle, name="detalle"),                                    # CU-19
    path("reservas/<int:pk>/modificar/", views.modificar, name="modificar"),                      # CU-20
    path("reservas/<int:pk>/cancelar/", views.cancelar, name="cancelar"),                         # CU-21
    path("reservas/<int:pk>/documentos/", views.documento_subir, name="documento_subir"),         # CU-24
    path("reservas/documentos/<int:pk>/descargar/", views.documento_descargar, name="documento_descargar"),
    path("reservas/documentos/<int:pk>/eliminar/", views.documento_eliminar, name="documento_eliminar"),
    path("reservas/<int:pk>/itinerario/", views.itinerario, name="itinerario"),                   # CU-25
    path("reservas/<int:pk>/itinerario.pdf", views.itinerario_pdf, name="itinerario_pdf"),
    # Gestión: solo Administrador
    path("gestion/reservas/", views.gestion_reservas, name="gestion_lista"),                      # CU-22
    path("gestion/reservas/<int:pk>/confirmar/", views.confirmar, name="confirmar"),
    path("gestion/reservas/<int:pk>/solicitar-proveedores/", views.generar_confirmaciones,
         name="generar_confirmaciones"),
    path("gestion/confirmaciones/", views.confirmaciones, name="confirmaciones"),                 # CU-17
    path("gestion/confirmaciones/<int:pk>/", views.responder_confirmacion, name="responder_confirmacion"),
    path("gestion/clientes/", views.clientes, name="clientes"),                                   # CU-23
    path("gestion/clientes/nuevo/", views.cliente_nuevo, name="cliente_nuevo"),
    path("gestion/clientes/<int:pk>/", views.cliente_detalle, name="cliente_detalle"),
    path("gestion/clientes/<int:pk>/editar/", views.cliente_editar, name="cliente_editar"),
    path("gestion/cronogramas/", views.cronograma_paquetes, name="cronograma_paquetes"),          # CU-25
    path("gestion/cronogramas/<int:paquete_pk>/", views.cronograma, name="cronograma"),
    path("gestion/cronogramas/<int:paquete_pk>/<int:actividad_pk>/", views.cronograma, name="cronograma_editar"),
    path("gestion/cronogramas/<int:paquete_pk>/<int:actividad_pk>/eliminar/", views.cronograma_eliminar,
         name="cronograma_eliminar"),
]
