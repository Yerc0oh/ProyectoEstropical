from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import DetailView, ListView

from apps.core.disponibilidad import CapacidadPorDebajoDeOcupado
from apps.core.views_base import (AdminCreateView, AdminListView,
                                  AdminSoftDeleteView, AdminUpdateView)
from apps.destinations.models import Destino

from .forms import (FiltroCatalogoForm, PaqueteActividadInlineFormSet,
                    PaqueteForm, PaqueteHotelInlineFormSet,
                    PaqueteServicioInlineFormSet, PaqueteVueloInlineFormSet)
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

    def get_filtro_form(self):
        """Formulario de filtros enlazado a los parámetros GET (CU-09)."""
        if not hasattr(self, "_filtro_form"):
            self._filtro_form = FiltroCatalogoForm(self.request.GET or None)
        return self._filtro_form

    def get_queryset(self):
        qs = _publicados()
        form = self.get_filtro_form()
        if not form.is_valid():
            # Con cualquier parámetro inválido se ignora el filtrado completo:
            # no se ejecuta ninguna consulta con datos sin validar y la
            # plantilla muestra los errores. Así no hay errores 500.
            return qs

        data = form.cleaned_data
        if data.get("destino"):
            qs = qs.filter(destino=data["destino"])
        if data.get("precio_min") is not None:
            qs = qs.filter(precio_persona__gte=data["precio_min"])
        if data.get("precio_max") is not None:
            qs = qs.filter(precio_persona__lte=data["precio_max"])
        if data.get("salida_desde"):
            qs = qs.filter(fecha_salida__gte=data["salida_desde"])
        if data.get("salida_hasta"):
            qs = qs.filter(fecha_salida__lte=data["salida_hasta"])
        if data.get("q"):
            q = data["q"]
            qs = qs.filter(Q(nombre__icontains=q) | Q(destino__nombre__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["destinos"] = Destino.objects.filter(activo=True)
        ctx["filtro_form"] = self.get_filtro_form()
        return ctx



class DetallePaqueteView(DetailView):
    template_name = "packages/paquete_detail.html"
    context_object_name = "paquete"

    def get_queryset(self):
        return _publicados().prefetch_related(
            "actividades",
            "paqueteservicio_set__servicio",
            "paquetehotel_set__tipo_habitacion__hotel",
            "paquetevuelo_set__vuelo__origen",
            "paquetevuelo_set__vuelo__destino",
            "paquetevuelo_set__vuelo__proveedor",
        )


MAX_PAQUETES_COMPARAR = 3


def _ids_comparador(request):
    """Normaliza y valida ?ids=... del comparador (CU-10).

    Devuelve ``(ids, error)``: identificadores únicos en orden de selección o
    un mensaje de error. Un identificador no numérico/negativo se rechaza (antes
    provocaba un ValueError en el ORM) y una selección de más de tres paquetes
    se rechaza explícitamente, sin confiar solo en el JavaScript del catálogo.
    """
    ids = []
    for valor in request.GET.getlist("ids"):
        try:
            pk = int(valor)
        except (TypeError, ValueError):
            return [], "La selección contiene identificadores no válidos."
        if pk <= 0:
            return [], "La selección contiene identificadores no válidos."
        if pk not in ids:
            ids.append(pk)
    if len(ids) > MAX_PAQUETES_COMPARAR:
        return [], (f"Puedes comparar como máximo {MAX_PAQUETES_COMPARAR} paquetes. "
                    "Desmarca alguno para continuar.")
    return ids, None


def comparar_paquetes(request):                # CU-10
    """Uso: /paquetes/comparar/?ids=1&ids=2&ids=3"""
    ids, error = _ids_comparador(request)
    if error:
        messages.warning(request, error)
        paquetes = Paquete.objects.none()
    else:
        paquetes = (_publicados().filter(pk__in=ids)
                    .prefetch_related("paqueteservicio_set__servicio"))
    return render(request, "packages/paquete_compare.html", {"paquetes": paquetes})


# ----------------------------------------------------------------- Gestión (CU-12)
class PaqueteLista(AdminListView):
    model = Paquete
    titulo = "Gestionar paquetes"
    columnas = [("Paquete", "nombre"), ("Destino", "destino"), ("Salida", "fecha_salida"),
                ("Precio (Bs)", "precio_persona"), ("Cupos totales", "cupos_total"),
                ("Cupos ocupados", "cupos_ocupados"),
                ("Cupos libres", "cupos_disponibles"),
                ("Estado", "get_estado_display")]
    url_crear = "packages:gestion_crear"
    url_editar = "packages:gestion_editar"
    url_eliminar = "packages:gestion_eliminar"


class PaqueteComponentesMixin:
    """Añade los cuatro formsets de componentes al formulario del paquete.

    La validación ocurre antes de guardar. Después, paquete y componentes se
    guardan dentro de una sola transacción para no dejar registros parciales.
    """

    template_name = "packages/paquete_form.html"
    formset_specs = (
        ("hoteles", PaqueteHotelInlineFormSet, "Hoteles / tipos de habitación"),
        ("vuelos", PaqueteVueloInlineFormSet, "Vuelos"),
        ("servicios", PaqueteServicioInlineFormSet, "Servicios"),
        ("actividades", PaqueteActividadInlineFormSet, "Actividades"),
    )

    def _formularios_componentes(self, instance):
        data = self.request.POST if self.request.method == "POST" else None
        files = self.request.FILES if data is not None else None
        return [(titulo, formset_class(data=data, files=files, instance=instance,
                                       prefix=prefix))
                for prefix, formset_class, titulo in self.formset_specs]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if "formsets" not in ctx:
            instance = getattr(self, "object", None) or Paquete()
            ctx["formsets"] = self._formularios_componentes(instance)
        return ctx

    def form_valid(self, form):
        formsets = self._formularios_componentes(form.instance)
        if not all(formset.is_valid() for _, formset in formsets):
            return self.render_to_response(
                self.get_context_data(form=form, formsets=formsets))

        with transaction.atomic():
            self.object = form.save()
            for _, formset in formsets:
                formset.instance = self.object
                # Los formularios nuevos se construyeron con el paquete aún sin
                # guardar; se reasignan a la instancia definitiva antes de salvar.
                for componente_form in formset.forms:
                    setattr(componente_form.instance, formset.fk.name, self.object)
                formset.save()
            messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())


class PaqueteCrear(PaqueteComponentesMixin, AdminCreateView):
    model = Paquete
    form_class = PaqueteForm
    titulo = "Nuevo paquete"
    url_listado = "packages:gestion_lista"


class PaqueteEditar(PaqueteComponentesMixin, AdminUpdateView):
    model = Paquete
    form_class = PaqueteForm
    titulo = "Editar paquete"
    url_listado = "packages:gestion_lista"

    def form_valid(self, form):
        """Traduce una carrera de cupos a un error de formulario (CU-16)."""
        try:
            return super().form_valid(form)
        except CapacidadPorDebajoDeOcupado as exc:
            form.add_error("cupos_total", str(exc))
            return self.form_invalid(form)


class PaqueteEliminar(AdminSoftDeleteView):
    """'Eliminar' un paquete = archivarlo (las reservas futuras lo referencian)."""
    model = Paquete
    url_listado = "packages:gestion_lista"
    campo = "estado"
    valor = "archivado"
