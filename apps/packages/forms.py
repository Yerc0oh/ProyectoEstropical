
from django import forms
from django.forms.models import BaseInlineFormSet, inlineformset_factory

from apps.core.disponibilidad import guardar_con_capacidad
from apps.core.forms import BootstrapModelForm, CapacidadFormMixin
from apps.destinations.models import Destino

from .models import (
    Paquete,
    PaqueteActividad,
    PaqueteHotel,
    PaqueteServicio,
    PaqueteVuelo,
)


class FiltroCatalogoForm(forms.Form):
    """Filtros del catálogo público de paquetes."""

    q = forms.CharField(required=False, label="Búsqueda")

    destino = forms.ModelChoiceField(
        queryset=Destino.objects.filter(activo=True),
        required=False,
        empty_label="Todos los destinos",
        label="Destino",
    )

    precio_min = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=12,
        decimal_places=2,
        label="Precio mínimo (Bs)",
    )

    precio_max = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=12,
        decimal_places=2,
        label="Precio máximo (Bs)",
    )

    salida_desde = forms.DateField(
        required=False,
        label="Salida desde",
    )

    salida_hasta = forms.DateField(
        required=False,
        label="Salida hasta",
    )

    def clean(self):
        data = super().clean()

        minimo = data.get("precio_min")
        maximo = data.get("precio_max")

        if (
            minimo is not None
            and maximo is not None
            and minimo > maximo
        ):
            self.add_error(
                "precio_min",
                "El precio mínimo no puede superar el máximo.",
            )

        desde = data.get("salida_desde")
        hasta = data.get("salida_hasta")

        if desde and hasta and desde > hasta:
            self.add_error(
                "salida_desde",
                "La fecha inicial no puede ser posterior a la final.",
            )

        return data


class PaqueteForm(CapacidadFormMixin, BootstrapModelForm):
    """Formulario para crear y editar paquetes."""

    campo_total = "cupos_total"
    campo_disponible = "cupos_disponibles"

    class Meta:
        model = Paquete
        fields = [
            "destino",
            "nombre",
            "descripcion",
            "condiciones",
            "fecha_salida",
            "fecha_retorno",
            "precio_persona",
            "cupos_total",
            "venta_desde",
            "venta_hasta",
            "estado",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preparar_capacidad()

    def clean_cupos_total(self):
        return self.validar_capacidad_total(
            self.cleaned_data["cupos_total"]
        )

    def save(self, commit=True):
        paquete = super().save(commit=False)

        if paquete.pk is None:
            paquete.cupos_disponibles = paquete.cupos_total

            if commit:
                paquete.save()

            return paquete

        if not commit:
            return paquete

        return guardar_con_capacidad(
            paquete,
            self.campo_total,
            self.campo_disponible,
        )


class PaqueteHotelForm(BootstrapModelForm):
    """Formulario de alojamiento incluido en un paquete."""

    class Meta:
        model = PaqueteHotel
        fields = [
            "tipo_habitacion",
            "dia_inicio",
            "noches",
        ]

    def clean_noches(self):
        noches = self.cleaned_data["noches"]

        if noches is not None and noches < 1:
            raise forms.ValidationError(
                "Debe indicar al menos una noche."
            )

        return noches

    def clean_dia_inicio(self):
        dia = self.cleaned_data["dia_inicio"]

        if dia is not None and dia < 1:
            raise forms.ValidationError(
                "El día de inicio debe ser 1 o mayor."
            )

        return dia


class PaqueteVueloForm(BootstrapModelForm):
    class Meta:
        model = PaqueteVuelo
        fields = ["vuelo", "tramo"]


class PaqueteServicioForm(BootstrapModelForm):
    class Meta:
        model = PaqueteServicio
        fields = ["servicio", "detalle"]


class PaqueteActividadForm(BootstrapModelForm):
    class Meta:
        model = PaqueteActividad
        fields = [
            "dia",
            "orden",
            "hora_inicio",
            "titulo",
            "descripcion",
        ]

    def clean_dia(self):
        dia = self.cleaned_data["dia"]

        if dia is not None and dia < 1:
            raise forms.ValidationError(
                "El día debe ser 1 o mayor."
            )

        return dia


class ComponenteFormSet(BaseInlineFormSet):
    """Valida los componentes relacionados con un paquete."""

    error_repetido = (
        "Este componente está repetido en el paquete."
    )

    def get_unique_error_message(self, unique_check):
        return self.error_repetido


class PaqueteHotelFormSet(ComponenteFormSet):
    """Comprueba las fechas de alojamiento del paquete."""

    def clean(self):
        super().clean()

        if any(self.errors):
            return

        paquete = self.instance

        if not paquete.fecha_salida or not paquete.fecha_retorno:
            return

        duracion = paquete.duracion_dias

        for form in self.forms:
            datos = getattr(form, "cleaned_data", None)

            if not datos:
                continue

            if datos.get("DELETE"):
                continue

            dia_inicio = datos.get("dia_inicio")
            noches = datos.get("noches")

            if dia_inicio is None or noches is None:
                continue

            if dia_inicio + noches > duracion:
                form.add_error(
                    "noches",
                    "La estancia supera la duración del paquete.",
                )


class PaqueteVueloFormSet(ComponenteFormSet):
    pass


class PaqueteServicioFormSet(ComponenteFormSet):
    pass


class PaqueteActividadFormSet(ComponenteFormSet):
    error_repetido = (
        "Ya existe una actividad con ese día y orden "
        "en este paquete."
    )


PaqueteHotelInlineFormSet = inlineformset_factory(
    Paquete,
    PaqueteHotel,
    form=PaqueteHotelForm,
    formset=PaqueteHotelFormSet,
    extra=1,
    can_delete=True,
)

PaqueteVueloInlineFormSet = inlineformset_factory(
    Paquete,
    PaqueteVuelo,
    form=PaqueteVueloForm,
    formset=PaqueteVueloFormSet,
    extra=1,
    can_delete=True,
)

PaqueteServicioInlineFormSet = inlineformset_factory(
    Paquete,
    PaqueteServicio,
    form=PaqueteServicioForm,
    formset=PaqueteServicioFormSet,
    extra=1,
    can_delete=True,
)

PaqueteActividadInlineFormSet = inlineformset_factory(
    Paquete,
    PaqueteActividad,
    form=PaqueteActividadForm,
    formset=PaqueteActividadFormSet,
    extra=1,
    can_delete=True,
)
