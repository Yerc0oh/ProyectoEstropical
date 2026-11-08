from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group, User
from django.db.models import Q
from django.utils import timezone

from apps.core.access import ROL_ADMIN, ROL_CLIENTE
from apps.core.forms import BootstrapFormMixin, BootstrapModelForm

from .models import Perfil


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    username = forms.CharField(label="Correo o usuario")
    error_messages = {
        "invalid_login": "Correo o contraseña incorrectos.",
        "inactive": "Tu cuenta aún no está verificada o fue bloqueada. Revisa tu correo o contacta a la agencia.",
    }

    def clean(self):
        identificador = self.cleaned_data.get("username", "").strip()
        if identificador:
            # Django autentica por username exacto: resuelve primero el usuario
            # sin distinguir mayúsculas y acepta tanto el correo como el usuario.
            user = (User.objects.filter(Q(username__iexact=identificador) |
                                        Q(email__iexact=identificador))
                    .order_by("id").first())
            self.cleaned_data["username"] = user.username if user else identificador
        return super().clean()


class ReenviarActivacionForm(BootstrapFormMixin, forms.Form):
    email = forms.EmailField(label="Correo electrónico")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


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
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
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

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get("fecha_nacimiento")
        if fecha and fecha > timezone.localdate():
            raise forms.ValidationError("La fecha de nacimiento no puede ser futura.")
        return fecha

    def clean(self):
        data = super().clean()
        tipo_documento = data.get("tipo_documento")
        nro_documento = data.get("nro_documento")
        if tipo_documento and nro_documento:
            # Django ya valida ModelForm/UniqueConstraint, pero su mensaje genérico
            # no es comprensible. Se conserva la exclusión del propio perfil.
            duplicados = Perfil.objects.filter(tipo_documento=tipo_documento,
                                               nro_documento=nro_documento)
            if self.instance.pk:
                duplicados = duplicados.exclude(pk=self.instance.pk)
            if duplicados.exists():
                self._documento_duplicado = True
                self.add_error("nro_documento",
                               "Ya existe un perfil con este tipo y número de documento.")
        return data

    def _get_validation_exclusions(self):
        # Si ya se informó el duplicado, evita que la restricción de BD agregue
        # además su mensaje genérico en __all__.
        exclude = super()._get_validation_exclusions()
        if getattr(self, "_documento_duplicado", False):
            exclude.update({"tipo_documento", "nro_documento"})
        return exclude


class CambiarRolForm(forms.Form):
    rol = forms.ChoiceField(choices=[(ROL_CLIENTE, ROL_CLIENTE), (ROL_ADMIN, ROL_ADMIN)])
