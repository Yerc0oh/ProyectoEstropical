from apps.core.forms import BootstrapModelForm

from .models import Proveedor


class ProveedorForm(BootstrapModelForm):
    class Meta:
        model = Proveedor
        fields = ["razon_social", "nit", "tipo", "nombre_contacto", "correo", "telefono",
                  "estado_validacion", "activo"]

# TODO CU-13: formulario/formset para cargar y validar ProveedorDocumento.
