from apps.core.forms import BootstrapModelForm

from .models import Hotel


class HotelForm(BootstrapModelForm):
    class Meta:
        model = Hotel
        fields = ["proveedor", "destino", "nombre", "estrellas", "direccion", "descripcion", "activo"]

# TODO CU-14: formularios de TipoHabitacion y TarifaHabitacion (anidados al hotel).
# TODO CU-16: actualizar habitaciones_disponibles.
