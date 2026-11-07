from apps.core.forms import BootstrapModelForm

from .models import Vuelo


class VueloForm(BootstrapModelForm):
    class Meta:
        model = Vuelo
        fields = ["proveedor", "numero_vuelo", "origen", "destino", "fecha_salida", "fecha_llegada",
                  "asientos_total", "precio_referencial", "estado"]

    def save(self, commit=True):
        vuelo = super().save(commit=False)
        if vuelo.pk is None:  # al crear, todos los asientos están disponibles
            vuelo.asientos_disponibles = vuelo.asientos_total
        # TODO CU-16: al editar asientos_total, recalcular asientos_disponibles
        if commit:
            vuelo.save()
        return vuelo
