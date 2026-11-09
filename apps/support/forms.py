
from django import forms

from .models import Ticket, RespuestaTicket


class TicketForm(forms.ModelForm):

    class Meta:
        model = Ticket
        fields = [
            "asunto",
            "categoria",
            "descripcion",
        ]

        widgets = {
            "asunto": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. Consulta sobre mi reserva",
                }
            ),
            "categoria": forms.Select(
                attrs={"class": "form-select"}
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Describe tu consulta o problema...",
                }
            ),
        }


class RespuestaTicketForm(forms.ModelForm):

    class Meta:
        model = RespuestaTicket
        fields = ["mensaje"]

        widgets = {
            "mensaje": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Escribe tu respuesta...",
                }
            ),
        }


class GestionTicketForm(forms.ModelForm):

    class Meta:
        model = Ticket
        fields = ["estado", "prioridad"]

        widgets = {
            "estado": forms.Select(
                attrs={"class": "form-select"}
            ),
            "prioridad": forms.Select(
                attrs={"class": "form-select"}
            ),
        }
