from django import forms
from django.forms.models import BaseInlineFormSet, inlineformset_factory

from apps.core.disponibilidad import guardar_con_capacidad
from apps.core.forms import BootstrapModelForm, CapacidadFormMixin
from apps.destinations.models import Destino

from .models import (Paquete, PaqueteActividad, PaqueteHotel, PaqueteServicio,
                     PaqueteVuelo)


class FiltroCatalogoForm(forms.Form):
    """Valida los parámetros GET del catálogo público de paquetes (CU-09).

    Ningún valor sin validar llega al ORM: precios negativos o mal formados,
    fechas inexistentes, destinos manipulados y rangos incoherentes se
    rechazan aquí. Si el formulario no es válido, la vista ignora todos los
    filtros y muestra los errores, por lo que un parámetro manipulado nunca
    provoca un error 500.
    """

    q = forms.CharField(required=False, label="Búsqueda")
    destino = forms.ModelChoiceField(
        queryset=Destino.objects.filter(activo=True), required=False,
        empty_label="Todos los destinos", label="Destino")
    precio_min = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=2,
        label="Precio mínimo (Bs)")
    precio_max = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=2,
        label="Precio máximo (Bs)")
    salida_desde = forms.DateField(required=False, label="Salida desde")
    salida_hasta = forms.DateField(required=False, label="Salida hasta")

    def clean(self):
        data = super().clean()
        minimo = data.get("precio_min")
        maximo = data.get("precio_max")
        if minimo is not None and maximo is not None and minimo > maximo:
            self.add_error(
                "precio_min",
                "El precio mínimo no puede ser mayor que el precio máximo.")

        desde = data.get("salida_desde")
        hasta = data.get("salida_hasta")
        if desde and hasta and desde > hasta:
            self.add_error(
                "salida_desde",
                "La fecha de salida inicial no puede ser posterior a la final.")
        return data


class PaqueteForm(CapacidadFormMixin, BootstrapModelForm):
    """Alta y edición de paquetes.

    Los cupos disponibles no se editan: en el alta se igualan al total y en la
    edición se recalculan conservando los cupos ya ocupados (CU-16).
    """

    campo_total = "cupos_total"
    campo_disponible = "cupos_disponibles"

    class Meta:
        model = Paquete
        fields = ["destino", "nombre", "descripcion", "condiciones", "fecha_salida", "fecha_retorno",
                  "precio_persona", "cupos_total", "venta_desde", "venta_hasta", "estado"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preparar_capacidad()

    def clean_cupos_total(self):
        return self.validar_capacidad_total(self.cleaned_data["cupos_total"])

    def save(self, commit=True):
        paquete = super().save(commit=False)
        if paquete.pk is None:
            paquete.cupos_disponibles = paquete.cupos_total
            if commit:
                paquete.save()
            return paquete
        if not commit:
            return paquete
        return guardar_con_capacidad(paquete, self.campo_total, self.campo_disponible)


class PaqueteHotelForm(BootstrapModelForm):
    class Meta:
        model = PaqueteHotel
        fields = ["tipo_habitacion", "noches"]

    def clean_noches(self):
        noches = self.cleaned_data["noches"]
        if noches is not None and noches < 1:
            raise forms.ValidationError("Debe indicar al menos 1 noche.")
        return noches


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
        fields = ["dia", "orden", "hora_inicio", "titulo", "descripcion"]

    def clean_dia(self):
        dia = self.cleaned_data["dia"]
        if dia is not None and dia < 1:
            raise forms.ValidationError("El día debe ser 1 o mayor.")
        return dia


class ComponenteFormSet(BaseInlineFormSet):
    """Formset inline que rechaza componentes repetidos dentro del mismo envío.

    Django compara los formularios del formset usando las restricciones únicas
    del modelo, algo que la base de datos no puede hacer con filas que todavía
    no existen. Solo se personaliza el mensaje mostrado.
    """

    error_repetido = "Este componente está repetido en el paquete."

    def get_unique_error_message(self, unique_check):
        return self.error_repetido


class PaqueteHotelFormSet(ComponenteFormSet):
    pass


class PaqueteVueloFormSet(ComponenteFormSet):
    pass


class PaqueteServicioFormSet(ComponenteFormSet):
    pass


class PaqueteActividadFormSet(ComponenteFormSet):
    error_repetido = "Ya existe una actividad con ese día y orden en este paquete."


PaqueteHotelInlineFormSet = inlineformset_factory(
    Paquete, PaqueteHotel, form=PaqueteHotelForm, formset=PaqueteHotelFormSet,
    extra=1, can_delete=True)
PaqueteVueloInlineFormSet = inlineformset_factory(
    Paquete, PaqueteVuelo, form=PaqueteVueloForm, formset=PaqueteVueloFormSet,
    extra=1, can_delete=True)
PaqueteServicioInlineFormSet = inlineformset_factory(
    Paquete, PaqueteServicio, form=PaqueteServicioForm, formset=PaqueteServicioFormSet,
    extra=1, can_delete=True)
PaqueteActividadInlineFormSet = inlineformset_factory(
    Paquete, PaqueteActividad, form=PaqueteActividadForm, formset=PaqueteActividadFormSet,
    extra=1, can_delete=True)
