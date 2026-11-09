from django.urls import path

from . import views

app_name = "suppliers"

urlpatterns = [
    # CU-13: portal del proveedor (usuario autenticado y vinculado a un proveedor)
    path("proveedor/documentos/", views.mis_documentos, name="mis_documentos"),
    path("proveedor/documentos/nuevo/", views.cargar_documento, name="documento_cargar"),
    path("proveedor/documentos/<int:pk>/nueva-version/",
         views.nueva_version_documento, name="documento_nueva_version"),
    path("proveedor/documentos/<int:pk>/archivo/",
         views.descargar_documento, name="documento_archivo"),

    # CU-13: revisión administrativa (solo Administrador)
    path("gestion/proveedores/documentos/", views.gestion_documentos,
         name="gestion_documentos"),
    path("gestion/proveedores/<int:proveedor_pk>/documentos/",
         views.gestion_documentos, name="gestion_documentos_proveedor"),
    path("gestion/proveedores/documentos/<int:pk>/revisar/",
         views.revisar_documento, name="gestion_documento_revisar"),

    # Gestión de proveedores
    path("gestion/proveedores/", views.ProveedorLista.as_view(), name="gestion_lista"),
    path("gestion/proveedores/nuevo/", views.ProveedorCrear.as_view(), name="gestion_crear"),
    path("gestion/proveedores/<int:pk>/editar/", views.ProveedorEditar.as_view(), name="gestion_editar"),
    path("gestion/proveedores/<int:pk>/eliminar/", views.ProveedorEliminar.as_view(), name="gestion_eliminar"),
]
