from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group, User

from apps.core.access import ROL_ADMIN, ROL_CLIENTE
from apps.core.forms import BootstrapFormMixin, BootstrapModelForm

from .models import Perfil


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    username = forms.EmailField(label="Correo electrónico")
    error_messages = {
        "invalid_login": "Correo o contraseña incorrectos.",
        "inactive": "Tu cuenta aún no está verificada o fue bloqueada. Revisa tu correo o contacta a la agencia.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].lower()


class RegistroForm(BootstrapFormMixin, forms.Form):
    nombres = forms.CharField(max_length=80)
    apellidos = forms.CharField(max_length=80)
    email = forms.EmailField(label="Correo electrónico")
    tipo_documento = forms.ChoiceField(choices=Perfil.TipoDocumento.choices)
    nro_documento = forms.CharField(label="Número de documento", max_length=20)
    telefono = forms.CharField(max_length=20, required=False)
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repetir contraseña", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return email

    def clean(self):
        data = super().clean()
        if data.get("tipo_documento") and data.get("nro_documento"):
            if Perfil.objects.filter(tipo_documento=data["tipo_documento"],
                                     nro_documento=data["nro_documento"]).exists():
                self.add_error("nro_documento", "Este documento ya está registrado.")
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2:
            if p1 != p2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            else:
                try:
                    password_validation.validate_password(p1)
                except forms.ValidationError as e:
                    self.add_error("password1", e)
        return data


class PerfilForm(BootstrapModelForm):
    class Meta:
        model = Perfil
        fields = ["nombres", "apellidos", "tipo_documento", "nro_documento", "fecha_nacimiento",
                  "telefono", "direccion", "nacionalidad", "nit", "razon_social"]


class CambiarRolForm(forms.Form):
    rol = forms.ChoiceField(choices=[(ROL_CLIENTE, ROL_CLIENTE), (ROL_ADMIN, ROL_ADMIN)])
