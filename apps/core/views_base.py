"""Vistas CRUD genéricas para el panel de gestión (solo Administrador).

Cada app define sus vistas heredando de estas clases e indicando modelo, formulario,
columnas del listado y nombres de URL. Plantillas: templates/core/crud_*.html
"""
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .access import AdminRequiredMixin
from .disponibilidad import CapacidadPorDebajoDeOcupado


class AdminListView(AdminRequiredMixin, ListView):
    template_name = "core/crud_list.html"
    paginate_by = 20
    titulo = ""
    columnas = []          # [("Encabezado", "atributo"), ...]
    url_crear = None       # nombre de URL (con namespace)
    url_editar = None
    url_eliminar = None
    url_extra = None       # acción adicional por fila (recibe el pk del objeto)
    texto_extra = "Ver"


class AdminFormMixin(AdminRequiredMixin, SuccessMessageMixin):
    template_name = "core/crud_form.html"
    titulo = ""
    url_listado = None     # nombre de URL a la que se vuelve
    success_message = "Cambios guardados correctamente."

    def get_success_url(self):
        from django.urls import reverse
        return reverse(self.url_listado)


class AdminCreateView(AdminFormMixin, CreateView):
    pass


class AdminUpdateView(AdminFormMixin, UpdateView):
    pass


class AdminCapacidadUpdateView(AdminUpdateView):
    """Edición de un recurso con capacidad total y disponibilidad (CU-16).

    Si entre la validación del formulario y el guardado otra transacción ocupa
    más unidades, el servicio lanza ``CapacidadPorDebajoDeOcupado``. Aquí se
    devuelve el formulario con un error comprensible en vez de un error 500.
    """

    campo_capacidad = None
    campo_disponible = None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obj = getattr(self, "object", None)
        if obj is not None and self.campo_capacidad and self.campo_disponible:
            total = getattr(obj, self.campo_capacidad)
            disponible = getattr(obj, self.campo_disponible)
            ctx["resumen_capacidad"] = {
                "total": total,
                "ocupado": total - disponible,
                "disponible": disponible,
            }
        return ctx

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except CapacidadPorDebajoDeOcupado as exc:
            form.add_error(self.campo_capacidad, str(exc))
            return self.form_invalid(form)


class AdminSoftDeleteView(AdminRequiredMixin, DeleteView):
    """'Eliminar' = marcar el registro (activo=False, estado='archivado'...).
    No se borran filas porque otras tablas (reservas, facturas) las referencian."""
    template_name = "core/crud_confirm_delete.html"
    url_listado = None
    campo = "activo"       # campo a modificar
    valor = False          # valor que lo deja "eliminado"

    def form_valid(self, form):
        obj = self.get_object()
        setattr(obj, self.campo, self.valor)
        obj.save(update_fields=[self.campo])
        messages.success(self.request, "Registro eliminado.")
        from django.urls import reverse
        return HttpResponseRedirect(reverse(self.url_listado))
