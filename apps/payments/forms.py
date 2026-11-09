from decimal import Decimal

from django import forms
from django.utils import timezone

from apps.core.forms import BootstrapForm, BootstrapModelForm
from apps.reservations.models import ConfirmacionProveedor, ParametroSistema

from .models import Metodo, PagoProveedor


class PagoEnLineaForm(BootstrapForm):
    """CU-26. Los datos de tarjeta solo se validan y NO se guardan (RNF-05)."""
    metodo = forms.ChoiceField(label="Método de pago", choices=[(Metodo.QR, "Código QR"), (Metodo.TARJETA, "Tarjeta")],
                               widget=forms.RadioSelect)
    numero_tarjeta = forms.CharField(label="Número de tarjeta", max_length=23, required=False,
                                     widget=forms.TextInput(attrs={"autocomplete": "cc-number", "inputmode": "numeric"}))
    vencimiento = forms.CharField(label="Vencimiento (MM/AA)", max_length=5, required=False,
                                  widget=forms.TextInput(attrs={"autocomplete": "cc-exp", "placeholder": "MM/AA"}))
    cvv = forms.CharField(label="CVV", max_length=4, required=False,
                          widget=forms.PasswordInput(attrs={"autocomplete": "cc-csc", "inputmode": "numeric"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["metodo"].widget.attrs["class"] = "form-check-input"

    def clean(self):
        datos = super().clean()
        if datos.get("metodo") == Metodo.TARJETA:
            if not datos.get("numero_tarjeta"):
                self.add_error("numero_tarjeta", "Ingresa el número de la tarjeta.")
            venc = datos.get("vencimiento", "")
            try:
                mes, anio = (int(x) for x in venc.split("/"))
                hoy = timezone.localdate()
                if not 1 <= mes <= 12 or (2000 + anio, mes) < (hoy.year, hoy.month):
                    raise ValueError
            except ValueError:
                self.add_error("vencimiento", "Fecha de vencimiento inválida o pasada.")
            if not (datos.get("cvv") or "").isdigit() or len(datos.get("cvv") or "") not in (3, 4):
                self.add_error("cvv", "CVV inválido.")
        return datos


class PlanCuotasForm(BootstrapForm):
    cantidad = forms.IntegerField(label="Número de cuotas", min_value=2)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        maximo = ParametroSistema.obtener("cuotas_maximas", 6)
        self.fields["cantidad"].max_value = maximo
        self.fields["cantidad"].widget.attrs.update({"min": 2, "max": maximo})
        self.fields["cantidad"].help_text = f"Entre 2 y {maximo}. La primera vence hoy y las demás cada 30 días."


class PagoVentanillaForm(BootstrapForm):
    metodo = forms.ChoiceField(label="Método", choices=Metodo.choices)
    monto = forms.DecimalField(label="Monto (Bs)", max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    referencia = forms.CharField(label="N° de transacción / depósito", max_length=100, required=False,
                                 help_text="Obligatorio para transferencia, QR y tarjeta.")


class FacturaForm(BootstrapForm):
    nit = forms.CharField(label="NIT / CI", max_length=20)
    razon_social = forms.CharField(label="Razón social / nombre", max_length=150, required=False)


class AnularFacturaForm(BootstrapForm):
    motivo = forms.CharField(label="Motivo de la anulación", max_length=250, widget=forms.Textarea(attrs={"rows": 2}))


class ProcesarReembolsoForm(BootstrapForm):
    accion = forms.ChoiceField(choices=[("aprobar", "Devolver el dinero"), ("rechazar", "Rechazar")])
    metodo = forms.ChoiceField(label="Método de devolución", choices=[("", "---")] + list(Metodo.choices),
                               required=False)
    referencia = forms.CharField(max_length=100, required=False)


class ExtractoForm(BootstrapForm):
    archivo = forms.FileField(label="Extracto (CSV)", help_text="Columnas: referencia,monto. Una transacción por fila.")


class PagoProveedorForm(BootstrapModelForm):
    class Meta:
        model = PagoProveedor
        fields = ["proveedor", "confirmacion", "monto", "metodo", "referencia", "observacion"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["confirmacion"].queryset = (ConfirmacionProveedor.objects.filter(estado="confirmada")
                                                .select_related("reserva", "proveedor"))
        self.fields["proveedor"].queryset = self.fields["proveedor"].queryset.filter(activo=True)

    def clean(self):
        datos = super().clean()
        conf, prov = datos.get("confirmacion"), datos.get("proveedor")
        if conf and prov and conf.proveedor_id != prov.pk:
            self.add_error("confirmacion", "El servicio confirmado es de otro proveedor.")
        return datos


class CierreCajaForm(BootstrapForm):
    fecha = forms.DateField()
    observaciones = forms.CharField(max_length=250, required=False)
