
from django import forms
from django.core.exceptions import ValidationError

from apps.destinations.models import Destino
from .models import PreferenciaViaje


class PreferenciaViajeForm(forms.ModelForm):

    class Meta:
        model = PreferenciaViaje

        fields = [
            "nombre",
            "tipo_viaje",
            "destinos",
            "presupuesto_minimo",
            "presupuesto_maximo",
            "duracion_minima",
            "duracion_maxima",
            "cantidad_personas",
            "observaciones",
            "activa",
        ]

        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej. Vacaciones familiares",
            }),
            "tipo_viaje": forms.Select(attrs={
                "class": "form-select",
            }),
            "destinos": forms.SelectMultiple(attrs={
                "class": "form-select",
                "size": 6,
            }),
            "presupuesto_minimo": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
            }),
            "presupuesto_maximo": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
            }),
            "duracion_minima": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1",
            }),
            "duracion_maxima": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1",
            }),
            "cantidad_personas": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1",
            }),
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Describe tus intereses de viaje...",
            }),
            "activa": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

    def __init__(self, *args, **kwargs):
        self.cliente = kwargs.pop("cliente", None)
        super().__init__(*args, **kwargs)

        self.fields["destinos"].queryset = (
            Destino.objects.filter(activo=True)
            .select_related("pais")
            .order_by("nombre")
        )

        if self.instance.pk:
            self.fields["destinos"].queryset = (
                Destino.objects.filter(activo=True)
                | Destino.objects.filter(
                    preferencias_viaje=self.instance
                )
            ).distinct().order_by("nombre")

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()

        if not nombre:
            raise ValidationError(
                "Debes ingresar un nombre para la preferencia."
            )

        if self.cliente:
            existentes = PreferenciaViaje.objects.filter(
                cliente=self.cliente,
                nombre__iexact=nombre,
            )

            if self.instance.pk:
                existentes = existentes.exclude(
                    pk=self.instance.pk
                )

            if existentes.exists():
                raise ValidationError(
                    "Ya tienes una preferencia con ese nombre."
                )

        return nombre

    def clean(self):
        cleaned_data = super().clean()

        minimo = cleaned_data.get("presupuesto_minimo")
        maximo = cleaned_data.get("presupuesto_maximo")

        if minimo is not None and maximo is not None:
            if minimo > maximo:
                self.add_error(
                    "presupuesto_maximo",
                    "El presupuesto máximo debe ser mayor o igual al mínimo."
                )

        dias_min = cleaned_data.get("duracion_minima")
        dias_max = cleaned_data.get("duracion_maxima")

        if dias_min is not None and dias_max is not None:
            if dias_min > dias_max:
                self.add_error(
                    "duracion_maxima",
                    "La duración máxima debe ser mayor o igual a la mínima."
                )

        return cleaned_data
