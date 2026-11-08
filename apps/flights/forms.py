from apps.core.disponibilidad import guardar_con_capacidad
from apps.core.forms import BootstrapModelForm, CapacidadFormMixin

from .models import Vuelo


class VueloForm(CapacidadFormMixin, BootstrapModelForm):
    """Alta y edición de vuelos.

    La disponibilidad no se edita directamente: en el alta se iguala al total y
    en la edición se recalcula conservando los asientos ya ocupados (CU-16).
    """

    campo_total = "asientos_total"
    campo_disponible = "asientos_disponibles"

    class Meta:
        model = Vuelo
        fields = ["proveedor", "numero_vuelo", "origen", "destino", "fecha_salida", "fecha_llegada",
                  "asientos_total", "precio_referencial", "estado"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preparar_capacidad()

    def clean_asientos_total(self):
        return self.validar_capacidad_total(self.cleaned_data["asientos_total"])

    def save(self, commit=True):
        vuelo = super().save(commit=False)
        if vuelo.pk is None:
            # Al crear, todos los asientos están disponibles.
            vuelo.asientos_disponibles = vuelo.asientos_total
            if commit:
                vuelo.save()
            return vuelo
        if not commit:
            return vuelo
        return guardar_con_capacidad(vuelo, self.campo_total, self.campo_disponible)
