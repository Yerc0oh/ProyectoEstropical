from django import forms


class BootstrapFormMixin:
    """Aplica clases de Bootstrap 5 y widgets de fecha a cualquier formulario."""

    def _bootstrapize(self):
        for field in self.fields.values():
            w = field.widget
            if isinstance(field, forms.DateTimeField):
                field.widget = w = forms.DateTimeInput(
                    attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
            elif isinstance(field, forms.DateField):
                field.widget = w = forms.DateInput(
                    attrs={"type": "date"}, format="%Y-%m-%d")
            elif isinstance(field, forms.TimeField):
                field.widget = w = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")
            css = "form-check-input" if isinstance(w, forms.CheckboxInput) else (
                "form-select" if isinstance(w, forms.Select) else "form-control")
            w.attrs["class"] = f"{w.attrs.get('class', '')} {css}".strip()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bootstrapize()


class BootstrapForm(BootstrapFormMixin, forms.Form):
    pass


class BootstrapModelForm(BootstrapFormMixin, forms.ModelForm):
    pass


class CapacidadFormMixin:
    """Formulario que edita solo la capacidad total de un recurso (CU-16).

    La disponibilidad no se expone como campo: se recalcula al guardar a partir
    de las unidades ya ocupadas. Cada formulario concreto define
    ``campo_total``, ``campo_disponible`` y, si aplica, ``total_minimo`` y
    ``mensaje_total_minimo``.
    """

    campo_total = None
    campo_disponible = None
    total_minimo = 0
    mensaje_total_minimo = "El total no puede ser negativo."

    def preparar_capacidad(self):
        """Debe llamarse al final del ``__init__`` del formulario concreto."""
        self._capacidad_invalida = False
        self.ocupado_actual = 0
        self.disponible_actual = 0
        if self.instance.pk:
            self.ocupado_actual = (getattr(self.instance, self.campo_total)
                                   - getattr(self.instance, self.campo_disponible))
            self.disponible_actual = getattr(self.instance, self.campo_disponible)
            ayuda = (
                f"Ahora hay {self.ocupado_actual} unidades ocupadas o comprometidas "
                f"y {self.disponible_actual} disponibles. Al cambiar el total, la "
                "disponibilidad se recalcula conservando esa ocupación.")
        else:
            ayuda = "Al crear el registro, todas las unidades quedan disponibles."
        self.fields[self.campo_total].help_text = ayuda

    def validar_capacidad_total(self, total):
        """Valida el total y devuelve el valor (o lanza ValidationError)."""
        if total is None:
            return total
        if total < self.total_minimo:
            self._capacidad_invalida = True
            raise forms.ValidationError(self.mensaje_total_minimo)
        if total < self.ocupado_actual:
            self._capacidad_invalida = True
            raise forms.ValidationError(
                f"No puedes reducir el total por debajo de {self.ocupado_actual}, "
                "que ya está ocupado o comprometido.")
        return total

    def _get_validation_exclusions(self):
        # Evita que la CheckConstraint del modelo muestre un mensaje genérico
        # cuando ya se informó un error comprensible sobre la capacidad.
        exclude = super()._get_validation_exclusions()
        if getattr(self, "_capacidad_invalida", False):
            exclude.update({self.campo_total, self.campo_disponible})
        return exclude
