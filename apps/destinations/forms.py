
from django import forms
from django.core.exceptions import ValidationError

from apps.core.forms import BootstrapModelForm
from .models import Destino


class DestinoForm(BootstrapModelForm):
    imagen = forms.ImageField(
        label="Subir fotografía desde mi computadora",
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": "image/jpeg,image/png,image/webp",
            }
        ),
    )

    commons_titulo = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Destino
        fields = [
            "pais",
            "categoria",
            "nombre",
            "codigo_iata",
            "descripcion",
            "activo",
        ]

    def clean_imagen(self):
        imagen = self.cleaned_data.get("imagen")

        if not imagen:
            return imagen

        if imagen.size > 5 * 1024 * 1024:
            raise ValidationError(
                "La fotografía no puede superar los 5 MB."
            )

        if imagen.content_type not in {
            "image/jpeg",
            "image/png",
            "image/webp",
        }:
            raise ValidationError(
                "Solo se permiten JPG, PNG o WebP."
            )

        from PIL import Image
        from PIL import UnidentifiedImageError

        try:
            imagen.seek(0)
            foto = Image.open(imagen)
            foto.verify()
            imagen.seek(0)
        except (UnidentifiedImageError, OSError):
            raise ValidationError(
                "El archivo no es una fotografía válida."
            )

        return imagen

    def clean(self):
        datos = super().clean()

        if (
            datos.get("imagen")
            and datos.get("commons_titulo")
        ):
            raise ValidationError(
                "Selecciona una fotografía de Wikimedia "
                "o sube una propia, pero no ambas."
            )

        return datos
