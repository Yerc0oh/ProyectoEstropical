
from django import forms
from .models import Resena


class ResenaForm(forms.ModelForm):
    class Meta:
        model = Resena
        fields = ["calificacion", "comentario"]

        widgets = {
            "calificacion": forms.Select(
                choices=[
                    (1, "⭐ 1 - Muy malo"),
                    (2, "⭐⭐ 2 - Malo"),
                    (3, "⭐⭐⭐ 3 - Regular"),
                    (4, "⭐⭐⭐⭐ 4 - Bueno"),
                    (5, "⭐⭐⭐⭐⭐ 5 - Excelente"),
                ],
                attrs={"class": "form-select"}
            ),
            "comentario": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Cuéntanos tu experiencia..."
                }
            ),
        }
