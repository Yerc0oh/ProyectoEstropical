
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.views.generic import DetailView, ListView


from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from apps.core.access import AdminRequiredMixin


from apps.core.views_base import (
    AdminCreateView,
    AdminListView,
    AdminSoftDeleteView,
    AdminUpdateView,
)

from .forms import DestinoForm
from .models import Categoria, Destino, DestinoFoto, Pais
from .wikimedia import (
    buscar_fotografias,
    obtener_fotografia,
    guardar_portada,
)


# ============================================================
# VISTAS PÚBLICAS
# ============================================================

class CatalogoDestinosView(ListView):
    template_name = "destinations/destino_list.html"
    paginate_by = 12

    def get_queryset(self):
        qs = (
            Destino.objects
            .filter(activo=True)
            .select_related("pais", "categoria")
            .prefetch_related("fotos")
        )

        q = self.request.GET.get("q", "").strip()

        if q:
            qs = qs.filter(
                Q(nombre__icontains=q)
                | Q(descripcion__icontains=q)
            )

        if self.request.GET.get("pais"):
            qs = qs.filter(
                pais_id=self.request.GET["pais"]
            )

        if self.request.GET.get("categoria"):
            qs = qs.filter(
                categoria_id=self.request.GET["categoria"]
            )

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["paises"] = Pais.objects.all()
        ctx["categorias"] = Categoria.objects.all()
        return ctx


class DetalleDestinoView(DetailView):
    template_name = "destinations/destino_detail.html"
    queryset = (
        Destino.objects
        .filter(activo=True)
        .select_related("pais", "categoria")
        .prefetch_related("fotos")
    )
    context_object_name = "destino"


# ============================================================
# GESTIÓN ADMINISTRATIVA
# ============================================================

class DestinoListaGestion(AdminListView):
    model = Destino
    titulo = "Gestionar destinos"

    columnas = [
        ("Nombre", "nombre"),
        ("País", "pais"),
        ("Categoría", "categoria"),
        ("Activo", "activo"),
    ]

    url_crear = "destinations:gestion_crear"
    url_editar = "destinations:gestion_editar"
    url_eliminar = "destinations:gestion_eliminar"


class DestinoImagenMixin:
    template_name = "destinations/destino_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        busqueda = self.request.GET.get(
            "buscar_fotos", ""
        ).strip()[:100]

        pais = self.request.GET.get(
            "pais_fotos", ""
        ).strip()[:80]

        ctx["buscar_fotos"] = busqueda
        ctx["pais_fotos"] = pais
        ctx["fotografias"] = []

        if busqueda:
            try:
                ctx["fotografias"] = buscar_fotografias(
                    busqueda,
                    pais,
                    limite=9,
                )
            except ValidationError as exc:
                ctx["error_fotografias"] = "; ".join(
                    exc.messages
                )

        return ctx

    def form_valid(self, form):
        imagen = form.cleaned_data.get("imagen")
        titulo = form.cleaned_data.get(
            "commons_titulo", ""
        )

        foto_commons = None

        # Comprobar la imagen antes de guardar el destino.
        if titulo:
            try:
                foto_commons = obtener_fotografia(titulo)
            except ValidationError as exc:
                form.add_error(
                    "commons_titulo",
                    "; ".join(exc.messages),
                )
                return self.form_invalid(form)

        try:
            with transaction.atomic():
                respuesta = super().form_valid(form)

                if imagen:
                    foto = DestinoFoto(
                        destino=self.object,
                        descripcion=(
                            f"Fotografía de {self.object.nombre}"
                        ),
                        orden=0,
                        es_portada=False,
                    )

                    foto.archivo = imagen
                    foto.save()

                    DestinoFoto.objects.filter(
                        destino=self.object,
                        es_portada=True,
                    ).exclude(
                        pk=foto.pk
                    ).update(es_portada=False)

                    foto.es_portada = True
                    foto.save(update_fields=["es_portada"])

                elif foto_commons:
                    guardar_portada(
                        self.object,
                        foto_commons,
                        reemplazar=True,
                    )

            return respuesta

        except (ValidationError, OSError) as exc:
            mensaje = (
                "; ".join(exc.messages)
                if isinstance(exc, ValidationError)
                else str(exc)
            )

            form.add_error(None, mensaje)
            return self.form_invalid(form)


class DestinoCrear(DestinoImagenMixin, AdminCreateView):
    model = Destino
    form_class = DestinoForm
    titulo = "Nuevo destino"
    url_listado = "destinations:gestion_lista"


class DestinoEditar(DestinoImagenMixin, AdminUpdateView):
    model = Destino
    form_class = DestinoForm
    titulo = "Editar destino"
    url_listado = "destinations:gestion_lista"


class DestinoEliminar(AdminSoftDeleteView):
    model = Destino
    url_listado = "destinations:gestion_lista"


@method_decorator(never_cache, name="dispatch")
class BuscarFotosWikimediaView(AdminRequiredMixin, View):
    """
    Búsqueda AJAX de fotografías para administradores.
    No crea destinos ni descarga archivos.
    """

    def get(self, request, *args, **kwargs):
        nombre = request.GET.get("nombre", "").strip()[:100]
        pais = request.GET.get("pais", "").strip()[:80]

        if len(nombre) < 2:
            return JsonResponse(
                {"error": "Escribe al menos dos caracteres."},
                status=400,
            )

        try:
            fotografias = buscar_fotografias(
                nombre,
                pais,
                limite=9,
            )

            return JsonResponse({
                "fotografias": fotografias,
            })

        except ValidationError as exc:
            return JsonResponse(
                {"error": "; ".join(exc.messages)},
                status=502,
            )
