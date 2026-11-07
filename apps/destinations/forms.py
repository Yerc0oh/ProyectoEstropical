from apps.core.forms import BootstrapModelForm

from .models import Destino


class DestinoForm(BootstrapModelForm):
    class Meta:
        model = Destino
        fields = ["pais", "categoria", "nombre", "codigo_iata", "descripcion", "activo"]

# TODO CU-08: formset de fotografías (DestinoFoto) para subir/ordenar fotos y elegir portada.
