from apps.core.views_base import (AdminCapacidadUpdateView, AdminCreateView,
                                  AdminListView, AdminSoftDeleteView)

from .forms import VueloForm
from .models import Vuelo

from django.utils import timezone
from django.views.generic import ListView, DetailView


class VueloLista(AdminListView):
    model = Vuelo
    titulo = "Gestionar vuelos"
    columnas = [("Vuelo", "numero_vuelo"), ("Origen", "origen"), ("Destino", "destino"),
                ("Salida", "fecha_salida"), ("Asientos totales", "asientos_total"),
                ("Ocupados", "asientos_ocupados"),
                ("Disponibles", "asientos_disponibles"),
                ("Estado", "get_estado_display")]
    url_crear = "flights:gestion_crear"
    url_editar = "flights:gestion_editar"
    url_eliminar = "flights:gestion_eliminar"


class VueloCrear(AdminCreateView):
    model = Vuelo
    form_class = VueloForm
    titulo = "Nuevo vuelo"
    url_listado = "flights:gestion_lista"


class VueloEditar(AdminCapacidadUpdateView):
    model = Vuelo
    form_class = VueloForm
    titulo = "Editar vuelo"
    url_listado = "flights:gestion_lista"
    campo_capacidad = "asientos_total"
    campo_disponible = "asientos_disponibles"


class VueloEliminar(AdminSoftDeleteView):
    """'Eliminar' un vuelo = marcarlo como cancelado."""
    model = Vuelo
    url_listado = "flights:gestion_lista"
    campo = "estado"
    valor = "cancelado"


# CATÁLOGO PÚBLICO DE VUELOS

class VueloCatalogo(ListView):
    model = Vuelo
    template_name = "flights/catalogo.html"
    context_object_name = "vuelos"
    paginate_by = 12

    def get_queryset(self):
        queryset = Vuelo.objects.filter(
            estado=Vuelo.Estado.PROGRAMADO,
            fecha_salida__gte=timezone.now(),
            asientos_disponibles__gt=0
        ).select_related(
            "origen", "destino", "proveedor"
        )

        origen = self.request.GET.get("origen")
        destino = self.request.GET.get("destino")
        fecha = self.request.GET.get("fecha")

        if origen and origen.isdigit():
            queryset = queryset.filter(origen_id=int(origen))

        if destino and destino.isdigit():
            queryset = queryset.filter(destino_id=int(destino))

        if fecha:
            from datetime import date
            try:
                fecha_valida = date.fromisoformat(fecha)
                queryset = queryset.filter(
                    fecha_salida__date=fecha_valida
                )
            except ValueError:
                pass

        return queryset.order_by("fecha_salida")

    def get_context_data(self, **kwargs):
        from apps.destinations.models import Destino

        context = super().get_context_data(**kwargs)
        context["destinos"] = Destino.objects.filter(
            pk__in=Vuelo.objects.values_list(
                "origen_id", flat=True
            )
        ) | Destino.objects.filter(
            pk__in=Vuelo.objects.values_list(
                "destino_id", flat=True
            )
        )
        context["destinos"] = context["destinos"].distinct().order_by("nombre")
        context["origen_seleccionado"] = self.request.GET.get("origen", "")
        context["destino_seleccionado"] = self.request.GET.get("destino", "")
        context["fecha_seleccionada"] = self.request.GET.get("fecha", "")
        return context


class VueloDetalle(DetailView):
    model = Vuelo
    template_name = "flights/detalle.html"
    context_object_name = "vuelo"

    def get_queryset(self):
        return Vuelo.objects.filter(
            estado=Vuelo.Estado.PROGRAMADO,
            fecha_salida__gte=timezone.now()
        ).select_related(
            "origen", "destino", "proveedor"
        )
