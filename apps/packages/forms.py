from apps.core.forms import BootstrapModelForm

from .models import Paquete


class PaqueteForm(BootstrapModelForm):
    class Meta:
        model = Paquete
        fields = ["destino", "nombre", "descripcion", "condiciones", "fecha_salida", "fecha_retorno",
                  "precio_persona", "cupos_total", "venta_desde", "venta_hasta", "estado"]

    def save(self, commit=True):
        paquete = super().save(commit=False)
        if paquete.pk is None:
            paquete.cupos_disponibles = paquete.cupos_total
        # TODO: al editar cupos_total, recalcular cupos_disponibles respetando reservas existentes.
        if commit:
            paquete.save()
        return paquete

# TODO CU-12: formsets para asignar hoteles (PaqueteHotel), vuelos (PaqueteVuelo),
#             servicios (PaqueteServicio) y actividades (PaqueteActividad).
