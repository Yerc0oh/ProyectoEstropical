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
