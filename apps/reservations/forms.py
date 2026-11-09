import os

from django import forms
from django.contrib.auth.models import User
from django.forms import BaseFormSet, BaseInlineFormSet, formset_factory, inlineformset_factory
from django.utils import timezone

from apps.accounts.models import Perfil
from apps.core.forms import BootstrapForm, BootstrapModelForm
from apps.packages.models import PaqueteActividad

from .models import ConfirmacionProveedor, DocumentoViaje, Pasajero, Reserva
from .services import clientes

MAX_PASAJEROS = 10
EXTENSIONES_DOCUMENTO = {".pdf", ".jpg", ".jpeg", ".png"}
TAMANO_MAXIMO_DOCUMENTO = 5 * 1024 * 1024      # 5 MB


# ---------------------------------------------------------------- CU-18 / CU-20 pasajeros
class PasajeroForm(BootstrapModelForm):
    class Meta:
        model = Pasajero
        fields = ["nombres", "apellidos", "tipo_documento", "nro_documento", "fecha_nacimiento", "nacionalidad"]

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data["fecha_nacimiento"]
        if fecha and fecha > timezone.localdate():
            raise forms.ValidationError("La fecha de nacimiento no puede ser futura.")
        return fecha

    def clean_nro_documento(self):
        return self.cleaned_data["nro_documento"].strip().upper()


def _documentos_repetidos(formularios):
    vistos = set()
    for f in formularios:
        if not hasattr(f, "cleaned_data") or not f.cleaned_data or f.cleaned_data.get("DELETE"):
            continue
        clave = (f.cleaned_data.get("tipo_documento"), f.cleaned_data.get("nro_documento"))
        if clave in vistos:
            raise forms.ValidationError("Hay dos pasajeros con el mismo documento.")
        vistos.add(clave)


class _PasajerosNuevosBase(BaseFormSet):
    def clean(self):
        super().clean()
        if not any(self.errors):
            _documentos_repetidos(self.forms)


# Al reservar: tantos formularios como pasajeros (todos obligatorios).
PasajeroFormSet = formset_factory(PasajeroForm, formset=_PasajerosNuevosBase, extra=0,
                                  min_num=1, max_num=MAX_PASAJEROS, validate_min=True, validate_max=True)


class _PasajerosEdicionBase(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        _documentos_repetidos(self.forms)
        quedan = sum(1 for f in self.forms if f.cleaned_data and not f.cleaned_data.get("DELETE"))
        if quedan == 0:
            raise forms.ValidationError("La reserva debe tener al menos un pasajero.")
        if quedan > MAX_PASAJEROS:
            raise forms.ValidationError(f"Máximo {MAX_PASAJEROS} pasajeros por reserva.")


# Al modificar: editar, quitar y agregar un pasajero (la fila vacía se ignora si no se llena).
PasajeroEdicionFormSet = inlineformset_factory(Reserva, Pasajero, form=PasajeroForm,
                                               formset=_PasajerosEdicionBase, extra=1, can_delete=True)


class ReservaForm(BootstrapForm):
    cupon = forms.CharField(label="Cupón de descuento", max_length=30, required=False)
    observaciones = forms.CharField(max_length=300, required=False, widget=forms.Textarea(attrs={"rows": 2}))


class ReservaPorAgenciaForm(ReservaForm):
    """El administrador reserva en nombre de un cliente (CU-18, antes CU-39)."""
    cliente = forms.ModelChoiceField(queryset=Perfil.objects.none(), label="Cliente")

    field_order = ["cliente", "cupon", "observaciones"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente"].queryset = clientes()


class ModificarReservaForm(BootstrapModelForm):
    class Meta:
        model = Reserva
        fields = ["observaciones"]
        widgets = {"observaciones": forms.Textarea(attrs={"rows": 2})}


class CancelarReservaForm(BootstrapForm):
    motivo = forms.CharField(label="Motivo de la cancelación", max_length=250, widget=forms.Textarea(attrs={"rows": 2}))
    acepto = forms.BooleanField(label="Entiendo la penalidad y el monto a reembolsar")


# ---------------------------------------------------------------- CU-24 documentos
class DocumentoViajeForm(BootstrapModelForm):
    class Meta:
        model = DocumentoViaje
        fields = ["pasajero", "tipo", "numero", "fecha_vencimiento", "archivo"]

    def __init__(self, *args, reserva=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pasajero"].queryset = reserva.pasajeros.all() if reserva else Pasajero.objects.none()
        self.fields["archivo"].help_text = "PDF, JPG o PNG de hasta 5 MB."

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if os.path.splitext(archivo.name)[1].lower() not in EXTENSIONES_DOCUMENTO:
            raise forms.ValidationError("Formato no permitido. Sube un PDF, JPG o PNG.")
        if archivo.size > TAMANO_MAXIMO_DOCUMENTO:
            raise forms.ValidationError("El archivo supera los 5 MB.")
        return archivo


# ---------------------------------------------------------------- CU-17
class ResponderConfirmacionForm(BootstrapForm):
    estado = forms.ChoiceField(choices=[(ConfirmacionProveedor.Estado.CONFIRMADA, "Confirmada"),
                                        (ConfirmacionProveedor.Estado.RECHAZADA, "Rechazada")])
    codigo_confirmacion = forms.CharField(label="Código de confirmación", max_length=50, required=False)
    observacion = forms.CharField(max_length=250, required=False)


# ---------------------------------------------------------------- CU-23 clientes
class ClienteNuevoForm(BootstrapModelForm):
    email = forms.EmailField(label="Correo electrónico")

    class Meta:
        model = Perfil
        fields = ["nombres", "apellidos", "tipo_documento", "nro_documento", "fecha_nacimiento",
                  "telefono", "direccion", "nacionalidad", "nit", "razon_social"]

    field_order = ["email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return email


# ---------------------------------------------------------------- CU-25 cronograma
class ActividadForm(BootstrapModelForm):
    class Meta:
        model = PaqueteActividad
        fields = ["dia", "orden", "hora_inicio", "titulo", "descripcion"]

    def __init__(self, *args, paquete=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.paquete = paquete

    def clean(self):
        datos = super().clean()
        dia, orden = datos.get("dia"), datos.get("orden")
        if dia is not None and self.paquete:
            if not 1 <= dia <= self.paquete.duracion_dias:
                self.add_error("dia", f"El paquete dura {self.paquete.duracion_dias} días.")
            repetida = PaqueteActividad.objects.filter(paquete=self.paquete, dia=dia, orden=orden)
            if self.instance.pk:
                repetida = repetida.exclude(pk=self.instance.pk)
            if repetida.exists():
                self.add_error("orden", "Ya hay una actividad con ese orden en ese día.")
        return datos
