from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import DetailView, ListView

from apps.core.views_base import (AdminCreateView, AdminListView,
                                  AdminSoftDeleteView, AdminUpdateView)
from apps.destinations.models import Destino

from .forms import PaqueteForm
from .models import Paquete


def _publicados():
    """Paquetes visibles al público: publicados, en vigencia de venta y con cupo."""
    hoy = timezone.localdate()
    return (Paquete.objects.filter(estado="publicado", venta_desde__lte=hoy, venta_hasta__gte=hoy)
            .select_related("destino", "destino__pais"))


# ----------------------------------------------------------------- Públicas
class CatalogoPaquetesView(ListView):          # CU-09
    template_name = "packages/paquete_list.html"
    paginate_by = 12

    def get_queryset(self):
        qs, g = _publicados(), self.request.GET
        if g.get("destino"):
            qs = qs.filter(destino_id=g["destino"])
        if g.get("precio_max"):
            qs = qs.filter(precio_persona__lte=g["precio_max"])
        if g.get("salida_desde"):
            qs = qs.filter(fecha_salida__gte=g["salida_desde"])
        if g.get("q"):
            qs = qs.filter(Q(nombre__icontains=g["q"]) | Q(destino__nombre__icontains=g["q"]))
        # TODO: validar los parámetros (precio/fecha inválidos lanzan error 500 hoy).
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["destinos"] = Destino.objects.filter(activo=True)
        return ctx


class DetallePaqueteView(DetailView):          # CU-11
    template_name = "packages/paquete_detail.html"
    context_object_name = "paquete"

    def get_queryset(self):
        return _publicados().prefetch_related("actividades", "paqueteservicio_set__servicio")


def comparar_paquetes(request):                # CU-10
    """Uso: /paquetes/comparar/?ids=1&ids=2&ids=3 (TODO: botón 'comparar' en el catálogo)."""
    ids = request.GET.getlist("ids")[:3]
    paquetes = _publicados().filter(pk__in=ids).prefetch_related("paqueteservicio_set__servicio")
    return render(request, "packages/paquete_compare.html", {"paquetes": paquetes})


# ----------------------------------------------------------------- Gestión (CU-12)
class PaqueteLista(AdminListView):
    model = Paquete
    titulo = "Gestionar paquetes"
    columnas = [("Paquete", "nombre"), ("Destino", "destino"), ("Salida", "fecha_salida"),
                ("Precio (Bs)", "precio_persona"), ("Cupos libres", "cupos_disponibles"),
                ("Estado", "get_estado_display")]
    url_crear = "packages:gestion_crear"
    url_editar = "packages:gestion_editar"
    url_eliminar = "packages:gestion_eliminar"


class PaqueteCrear(AdminCreateView):
    model = Paquete
    form_class = PaqueteForm
    titulo = "Nuevo paquete"
    url_listado = "packages:gestion_lista"


class PaqueteEditar(AdminUpdateView):
    model = Paquete
    form_class = PaqueteForm
    titulo = "Editar paquete"
    url_listado = "packages:gestion_lista"


class PaqueteEliminar(AdminSoftDeleteView):
    """'Eliminar' un paquete = archivarlo (las reservas futuras lo referencian)."""
    model = Paquete
    url_listado = "packages:gestion_lista"
    campo = "estado"
    valor = "archivado"
