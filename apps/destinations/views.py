from django.db.models import Q
from django.views.generic import DetailView, ListView

from apps.core.views_base import (AdminCreateView, AdminListView,
                                  AdminSoftDeleteView, AdminUpdateView)

from .forms import DestinoForm
from .models import Categoria, Destino, Pais


# ----------------------------------------------------------------- Públicas (CU-07)
class CatalogoDestinosView(ListView):
    template_name = "destinations/destino_list.html"
    paginate_by = 12

    def get_queryset(self):
        qs = Destino.objects.filter(activo=True).select_related("pais", "categoria")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))
        if self.request.GET.get("pais"):
            qs = qs.filter(pais_id=self.request.GET["pais"])
        if self.request.GET.get("categoria"):
            qs = qs.filter(categoria_id=self.request.GET["categoria"])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["paises"] = Pais.objects.all()
        ctx["categorias"] = Categoria.objects.all()
        return ctx


class DetalleDestinoView(DetailView):
    template_name = "destinations/destino_detail.html"
    queryset = Destino.objects.filter(activo=True).select_related("pais", "categoria")
    context_object_name = "destino"


# ----------------------------------------------------------------- Gestión (CU-08)
class DestinoListaGestion(AdminListView):
    model = Destino
    titulo = "Gestionar destinos"
    columnas = [("Nombre", "nombre"), ("País", "pais"), ("Categoría", "categoria"), ("Activo", "activo")]
    url_crear = "destinations:gestion_crear"
    url_editar = "destinations:gestion_editar"
    url_eliminar = "destinations:gestion_eliminar"


class DestinoCrear(AdminCreateView):
    model = Destino
    form_class = DestinoForm
    titulo = "Nuevo destino"
    url_listado = "destinations:gestion_lista"


class DestinoEditar(AdminUpdateView):
    model = Destino
    form_class = DestinoForm
    titulo = "Editar destino"
    url_listado = "destinations:gestion_lista"


class DestinoEliminar(AdminSoftDeleteView):
    model = Destino
    url_listado = "destinations:gestion_lista"
