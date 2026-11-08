import mimetypes
import os

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.services import obtener_perfil
from apps.core.access import admin_required, es_administrador
from apps.core.views_base import (AdminCreateView, AdminListView,
                                  AdminSoftDeleteView, AdminUpdateView)

from .forms import DocumentoProveedorForm, ProveedorForm, RevisionDocumentoForm
from .models import Proveedor, ProveedorDocumento
from .services import (DecisionInvalida, DocumentoYaRevisado,
                       revisar_documento as aplicar_revision)


class ProveedorLista(AdminListView):
    model = Proveedor
    titulo = "Gestionar proveedores"
    columnas = [("Razón social", "razon_social"), ("NIT", "nit"), ("Tipo", "get_tipo_display"),
                ("Validación", "get_estado_validacion_display"), ("Activo", "activo")]
    url_crear = "suppliers:gestion_crear"
    url_editar = "suppliers:gestion_editar"
    url_eliminar = "suppliers:gestion_eliminar"
    url_extra = "suppliers:gestion_documentos_proveedor"
    texto_extra = "Documentos"


class ProveedorCrear(AdminCreateView):
    model = Proveedor
    form_class = ProveedorForm
    titulo = "Nuevo proveedor"
    url_listado = "suppliers:gestion_lista"


class ProveedorEditar(AdminUpdateView):
    model = Proveedor
    form_class = ProveedorForm
    titulo = "Editar proveedor"
    url_listado = "suppliers:gestion_lista"


class ProveedorEliminar(AdminSoftDeleteView):
    model = Proveedor
    url_listado = "suppliers:gestion_lista"


# ------------------------------------------------------- CU-13 Portal del proveedor
def _proveedor_del_usuario(user):
    proveedor = getattr(user, "proveedor", None)
    if proveedor is None:
        raise PermissionDenied("Esta cuenta no está asociada a ningún proveedor.")
    return proveedor


def _documentos_de(proveedor):
    return (proveedor.documentos.select_related("revisado_por__usuario")
            .order_by("-fecha_carga"))


def mis_documentos(request):
    proveedor = _proveedor_del_usuario(request.user)
    return render(request, "suppliers/mis_documentos.html", {
        "proveedor": proveedor,
        "documentos": _documentos_de(proveedor),
    })


def cargar_documento(request):
    proveedor = _proveedor_del_usuario(request.user)
    form = DocumentoProveedorForm(
        request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        documento = form.save(commit=False)
        documento.proveedor = proveedor
        documento.estado = ProveedorDocumento.Estado.PENDIENTE
        documento.save()
        messages.success(request, "Documento cargado. Queda pendiente de revisión.")
        return redirect("suppliers:mis_documentos")
    return render(request, "suppliers/documento_form.html", {
        "form": form, "proveedor": proveedor, "titulo": "Cargar documento",
    })


def nueva_version_documento(request, pk):
    proveedor = _proveedor_del_usuario(request.user)
    original = get_object_or_404(
        ProveedorDocumento, pk=pk, proveedor=proveedor)
    if original.estado == ProveedorDocumento.Estado.PENDIENTE:
        messages.error(
            request,
            "Este documento todavía está pendiente de revisión. Espera la "
            "decisión antes de cargar una nueva versión.")
        return redirect("suppliers:mis_documentos")

    form = DocumentoProveedorForm(
        request.POST or None, request.FILES or None,
        initial={"tipo_documento": original.tipo_documento,
                 "fecha_vencimiento": original.fecha_vencimiento})
    if request.method == "POST" and form.is_valid():
        documento = form.save(commit=False)
        documento.proveedor = proveedor
        documento.estado = ProveedorDocumento.Estado.PENDIENTE
        documento.save()
        messages.success(
            request,
            "Nueva versión cargada. El documento anterior se conserva en el historial.")
        return redirect("suppliers:mis_documentos")
    return render(request, "suppliers/documento_form.html", {
        "form": form, "proveedor": proveedor, "original": original,
        "titulo": "Cargar nueva versión",
    })


def descargar_documento(request, pk):
    """Archivo privado: solo el proveedor propietario o un administrador."""
    documento = get_object_or_404(
        ProveedorDocumento.objects.select_related("proveedor"), pk=pk)
    es_propietario = documento.proveedor.usuario_id == request.user.pk
    if not es_propietario and not es_administrador(request.user):
        # 404 para no revelar la existencia de documentos de otros proveedores.
        raise Http404

    try:
        archivo = documento.archivo.open("rb")
    except (FileNotFoundError, OSError):
        raise Http404("El archivo ya no está disponible.")
    nombre = os.path.basename(documento.archivo.name) or "documento"
    tipo_mime = mimetypes.guess_type(nombre)[0] or "application/octet-stream"
    response = FileResponse(archivo, as_attachment=True, filename=nombre,
                            content_type=tipo_mime)
    response["X-Content-Type-Options"] = "nosniff"
    return response


# --------------------------------------------------- CU-13 Revisión (solo admin)
@admin_required
def gestion_documentos(request, proveedor_pk=None):
    qs = (ProveedorDocumento.objects
          .select_related("proveedor", "revisado_por__usuario")
          .order_by("estado", "-fecha_carga"))
    proveedor = None
    if proveedor_pk is not None:
        proveedor = get_object_or_404(Proveedor, pk=proveedor_pk)
        qs = qs.filter(proveedor=proveedor)

    estado = request.GET.get("estado", "")
    estados_validos = dict(ProveedorDocumento.Estado.choices)
    if estado in estados_validos:
        qs = qs.filter(estado=estado)
    else:
        estado = ""

    return render(request, "suppliers/gestion_documentos.html", {
        "documentos": qs,
        "proveedor": proveedor,
        "estado": estado,
        "estados": ProveedorDocumento.Estado.choices,
    })


@admin_required
def revisar_documento(request, pk):
    documento = get_object_or_404(
        ProveedorDocumento.objects.select_related("proveedor", "revisado_por__usuario"),
        pk=pk)

    if request.method == "POST":
        form = RevisionDocumentoForm(request.POST)
        if form.is_valid():
            try:
                aplicar_revision(
                    documento.pk, obtener_perfil(request.user),
                    form.cleaned_data["decision"], form.cleaned_data["motivo"])
            except DocumentoYaRevisado:
                messages.error(
                    request,
                    "Este documento ya fue revisado. No se puede aprobar ni "
                    "rechazar nuevamente.")
                return redirect("suppliers:gestion_documento_revisar", pk=documento.pk)
            except DecisionInvalida:
                form.add_error(
                    "motivo", "Debes indicar el motivo del rechazo.")
            else:
                messages.success(request, "Revisión registrada.")
                return redirect("suppliers:gestion_documentos")
    else:
        form = RevisionDocumentoForm(initial={"decision": "aprobar"})

    return render(request, "suppliers/documento_revisar.html", {
        "documento": documento, "form": form,
    })
