from django.contrib import admin

from .models import Proveedor, ProveedorDocumento

admin.site.register(Proveedor)


@admin.register(ProveedorDocumento)
class ProveedorDocumentoAdmin(admin.ModelAdmin):
    """La revisión se hace desde la interfaz de CU-13, no editando el admin.

    Los campos de revisión quedan de solo lectura para no saltarse el flujo
    (POST + motivo obligatorio + bloqueo de documentos ya revisados).
    """

    list_display = ("tipo_documento", "proveedor", "estado", "fecha_carga",
                    "revisado_por", "fecha_revision")
    list_filter = ("estado", "proveedor")
    search_fields = ("tipo_documento", "proveedor__razon_social")
    readonly_fields = ("estado", "observacion", "revisado_por", "fecha_revision",
                       "fecha_carga")
