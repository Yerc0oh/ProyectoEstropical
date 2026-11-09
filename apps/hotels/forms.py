from django import forms

from apps.core.disponibilidad import guardar_con_capacidad
from apps.core.forms import BootstrapModelForm, CapacidadFormMixin

from .models import Hotel, TarifaHabitacion, TipoHabitacion


class HotelForm(BootstrapModelForm):
    class Meta:
        model = Hotel
        fields = ["proveedor", "destino", "nombre", "estrellas", "direccion", "descripcion", "activo"]


class TipoHabitacionForm(CapacidadFormMixin, BootstrapModelForm):
    """Tipo de habitación siempre asociado al hotel indicado en la URL.

    La disponibilidad no se edita: en el alta se iguala al total y en la
    edición se recalcula conservando las habitaciones ya ocupadas (CU-16).
    """

    campo_total = "habitaciones_total"
    campo_disponible = "habitaciones_disponibles"
    total_minimo = 1
    mensaje_total_minimo = "Debe existir al menos 1 habitación."

    class Meta:
        model = TipoHabitacion
        fields = ["nombre", "capacidad", "habitaciones_total", "descripcion"]

    def __init__(self, *args, hotel=None, **kwargs):
        self.hotel = hotel or getattr(kwargs.get("instance"), "hotel", None)
        super().__init__(*args, **kwargs)
        self.preparar_capacidad()

    def clean_habitaciones_total(self):
        return self.validar_capacidad_total(self.cleaned_data["habitaciones_total"])

    def clean(self):
        data = super().clean()
        capacidad = data.get("capacidad")

        if capacidad is not None and capacidad < 1:
            self.add_error("capacidad", "La capacidad debe ser al menos 1.")

        nombre = data.get("nombre")
        if nombre and self.hotel:
            duplicados = TipoHabitacion.objects.filter(hotel=self.hotel, nombre__iexact=nombre)
            if self.instance.pk:
                duplicados = duplicados.exclude(pk=self.instance.pk)
            if duplicados.exists():
                self.add_error("nombre", "Ya existe un tipo de habitación con ese nombre en este hotel.")
        return data

    def save(self, commit=True):
        tipo = super().save(commit=False)
        if tipo.pk is None:
            # Al crear, todas las habitaciones están disponibles.
            tipo.habitaciones_disponibles = tipo.habitaciones_total
            if commit:
                tipo.save()
            return tipo
        if not commit:
            return tipo
        return guardar_con_capacidad(tipo, self.campo_total, self.campo_disponible)


class TarifaHabitacionForm(BootstrapModelForm):
    """Tarifa por temporada asociada al tipo de habitación indicado en la URL."""

    class Meta:
        model = TarifaHabitacion
        fields = ["fecha_inicio", "fecha_fin", "precio_noche"]

    def __init__(self, *args, tipo_habitacion=None, **kwargs):
        self.tipo_habitacion = tipo_habitacion or getattr(
            kwargs.get("instance"), "tipo_habitacion", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        inicio = data.get("fecha_inicio")
        fin = data.get("fecha_fin")
        precio = data.get("precio_noche")

        if precio is not None and precio <= 0:
            self.add_error("precio_noche", "El precio por noche debe ser mayor que cero.")

        if inicio and fin:
            if fin < inicio:
                self._fechas_invalidas = True
                self.add_error("fecha_fin", "La fecha de fin no puede ser anterior a la de inicio.")
            elif self.tipo_habitacion:
                solapadas = TarifaHabitacion.objects.filter(
                    tipo_habitacion=self.tipo_habitacion,
                    fecha_inicio__lte=fin, fecha_fin__gte=inicio)
                if self.instance.pk:
                    solapadas = solapadas.exclude(pk=self.instance.pk)
                if solapadas.exists():
                    self.add_error(
                        "fecha_inicio",
                        "Ya existe una tarifa para este tipo de habitación que se solapa "
                        "con ese rango de fechas.")
        return data

    def _get_validation_exclusions(self):
        # La CheckConstraint de fechas ya se tradujo a un error de campo.
        exclude = super()._get_validation_exclusions()
        if getattr(self, "_fechas_invalidas", False):
            exclude.update({"fecha_inicio", "fecha_fin"})
        return exclude

