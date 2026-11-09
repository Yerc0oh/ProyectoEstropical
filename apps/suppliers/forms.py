from django import forms
from django.contrib.auth.models import User
from django.db.models import Q

from apps.core.forms import BootstrapForm, BootstrapModelForm

from .models import Proveedor, ProveedorDocumento
from .validators import validar_archivo_documento


class ProveedorForm(BootstrapModelForm):
    class Meta:
        model = Proveedor
        fields = ["razon_social", "nit", "tipo", "nombre_contacto", "correo", "telefono",
                  "usuario", "estado_validacion", "activo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usuarios = User.objects.filter(is_active=True)
        if self.instance and self.instance.usuario_id:
            # No perder el propietario actual aunque su cuenta esté bloqueada.
            usuarios = User.objects.filter(
                Q(is_active=True) | Q(pk=self.instance.usuario_id))
        self.fields["usuario"].queryset = usuarios.order_by("email")
        self.fields["usuario"].help_text = (
            "Cuenta que podrá entrar a “Mis documentos” para cargar y consultar "
            "los documentos de este proveedor.")


class DocumentoProveedorForm(BootstrapModelForm):
    class Meta:
        model = ProveedorDocumento
        fields = ["tipo_documento", "archivo", "fecha_vencimiento"]
        widgets = {
            "tipo_documento": forms.TextInput(
                attrs={"placeholder": "NIT, licencia de funcionamiento, contrato..."}),
        }

    def clean_tipo_documento(self):
        tipo = (self.cleaned_data["tipo_documento"] or "").strip()
        if not tipo:
            raise forms.ValidationError("Indica el tipo de documento.")
        return tipo

    def clean_archivo(self):
        # Se valida aquí sobre el UploadedFile para poder comprobar también el
        # content_type declarado antes de que Django lo convierta en FieldFile.
        archivo = self.cleaned_data["archivo"]
        validar_archivo_documento(archivo)
        return archivo


class RevisionDocumentoForm(BootstrapForm):
    DECISIONES = (
        ("aprobar", "Aprobar documento"),
        ("rechazar", "Rechazar documento"),
    )

    decision = forms.ChoiceField(
        choices=DECISIONES, widget=forms.RadioSelect,
        label="Decisión")
    motivo = forms.CharField(
        required=False, max_length=250, widget=forms.Textarea(attrs={"rows": 3}),
        label="Motivo u observación",
        help_text="Obligatorio al rechazar. Se guardará junto con la revisión.")

    def clean(self):
        data = super().clean()
        decision = data.get("decision")
        motivo = (data.get("motivo") or "").strip()
        if decision == "rechazar" and not motivo:
            self.add_error("motivo", "Debes indicar el motivo del rechazo.")
        data["motivo"] = motivo
        return data
