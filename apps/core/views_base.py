"""Vistas CRUD genéricas para el panel de gestión (solo Administrador).

Cada app define sus vistas heredando de estas clases e indicando modelo, formulario,
columnas del listado y nombres de URL. Plantillas: templates/core/crud_*.html
"""
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .access import AdminRequiredMixin


class AdminListView(AdminRequiredMixin, ListView):
    template_name = "core/crud_list.html"
    paginate_by = 20
    titulo = ""
    columnas = []          # [("Encabezado", "atributo"), ...]
    url_crear = None       # nombre de URL (con namespace)
    url_editar = None
    url_eliminar = None


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
