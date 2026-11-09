"""Vistas del Sprint 3. Todas exigen sesión (LoginRequiredMiddleware); ninguna es pública.

Cliente: solo ve y opera SUS reservas (si pide otra -> 404).
Administrador: ve todas, reserva en nombre de clientes, confirma, gestiona clientes,
solicitudes a proveedores y el cronograma de los paquetes.
"""
import os

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.forms import PerfilForm
from apps.accounts.services import obtener_perfil
from apps.core.access import admin_required, es_administrador, es_cliente
from apps.packages.models import Paquete, PaqueteActividad

from . import services
from .forms import (MAX_PASAJEROS, ActividadForm, CancelarReservaForm, ClienteNuevoForm,
                    DocumentoViajeForm, ModificarReservaForm, PasajeroEdicionFormSet, PasajeroFormSet,
                    ReservaForm, ReservaPorAgenciaForm, ResponderConfirmacionForm)
from .models import ConfirmacionProveedor, DocumentoViaje, Reserva


def _reserva_visible(request, pk):
    return get_object_or_404(services.reservas_visibles(request.user), pk=pk)


def _errores(request, error):
    for m in getattr(error, "messages", [str(error)]):
        messages.error(request, m)


# ================================================================ CU-18 Realizar reserva
def reservar(request, paquete_pk):
    """Paso único: cantidad de pasajeros (?pasajeros=N) + datos de cada uno + cupón."""
    admin = es_administrador(request.user)
    if not (admin or es_cliente(request.user)):
        raise PermissionDenied
    paquete = get_object_or_404(services.paquetes_reservables().select_related("destino"), pk=paquete_pk)
    try:
        n = int(request.GET.get("pasajeros", 1))
    except ValueError:
        n = 1
    n = max(1, min(n, MAX_PASAJEROS, max(paquete.cupos_disponibles, 1)))

    FormReserva = ReservaPorAgenciaForm if admin else ReservaForm
    form = FormReserva(request.POST or None)
    formset = PasajeroFormSet(request.POST or None, prefix="pas", initial=[{}] * n if not request.POST else None)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        pasajeros = [f.cleaned_data for f in formset.forms if f.cleaned_data]
        perfil = obtener_perfil(request.user)
        cliente = form.cleaned_data["cliente"] if admin else perfil
        try:
            reserva = services.crear_reserva(
                paquete, cliente, perfil, pasajeros, form.cleaned_data["cupon"],
                form.cleaned_data["observaciones"])
        except ValidationError as e:
            _errores(request, e)
        else:
            messages.success(request, f"Reserva {reserva.codigo} registrada. Tienes hasta "
                             f"{timezone.localtime(reserva.fecha_expiracion):%d/%m/%Y %H:%M} para pagarla.")
            return redirect("reservations:detalle", reserva.pk)
    return render(request, "reservations/reservar.html", {
        "paquete": paquete, "form": form, "formset": formset, "n": n, "max_pasajeros": MAX_PASAJEROS})


# ================================================================ CU-19 Consultar mis reservas
def mis_reservas(request):
    services.expirar_reservas_vencidas()
    qs = services.reservas_visibles(request.user).filter(cliente__usuario=request.user)
    estado = request.GET.get("estado", "")
    if estado:
        qs = qs.filter(estado=estado)
    return render(request, "reservations/mis_reservas.html", {
        "reservas": qs, "estado": estado, "estados": Reserva.Estado.choices})


def detalle(request, pk):
    reserva = _reserva_visible(request, pk)
    from apps.payments.services import saldo_pendiente
    return render(request, "reservations/detalle.html", {
        "reserva": reserva,
        "pasajeros": reserva.pasajeros.prefetch_related("documentos").select_related("nacionalidad"),
        "pagado": services.total_pagado(reserva), "saldo": saldo_pendiente(reserva),
        "confirmaciones": reserva.confirmaciones_proveedor.select_related("proveedor"),
        "doc_form": DocumentoViajeForm(reserva=reserva), "es_admin_vista": es_administrador(request.user)})


# ================================================================ CU-20 Modificar reserva
def modificar(request, pk):
    reserva = _reserva_visible(request, pk)
    if not reserva.puede_modificarse:
        messages.error(request, "Esta reserva ya no puede modificarse.")
        return redirect("reservations:detalle", pk)
    form = ModificarReservaForm(request.POST or None, instance=reserva)
    formset = PasajeroEdicionFormSet(request.POST or None, instance=reserva, prefix="pas")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        try:
            with transaction.atomic():
                form.save()
                formset.save()
                services.actualizar_cantidad(reserva)
        except ValidationError as e:
            _errores(request, e)
        else:
            messages.success(request, "Reserva actualizada.")
            return redirect("reservations:detalle", pk)
    return render(request, "reservations/modificar.html", {"reserva": reserva, "form": form, "formset": formset})


# ================================================================ CU-21 Cancelar reserva
def cancelar(request, pk):
    reserva = _reserva_visible(request, pk)
    if not reserva.puede_cancelarse:
        messages.error(request, "Esta reserva ya no puede cancelarse.")
        return redirect("reservations:detalle", pk)
    calculo = services.calcular_cancelacion(reserva)
    form = CancelarReservaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            calculo = services.cancelar_reserva(reserva, obtener_perfil(request.user), form.cleaned_data["motivo"])
        except ValidationError as e:
            _errores(request, e)
        else:
            msg = f"Reserva {reserva.codigo} cancelada."
            if calculo["reembolsable"] > 0:
                msg += f" Se registró un reembolso de Bs {calculo['reembolsable']} (pendiente de procesar)."
            messages.success(request, msg)
            return redirect("reservations:detalle", pk)
    return render(request, "reservations/cancelar.html", {"reserva": reserva, "calculo": calculo, "form": form})


# ================================================================ CU-22 Confirmar reserva
@admin_required
def gestion_reservas(request):
    services.expirar_reservas_vencidas()
    qs = Reserva.objects.select_related("paquete", "cliente").order_by("-fecha_reserva")
    q, estado = request.GET.get("q", "").strip(), request.GET.get("estado", "")
    if q:
        qs = qs.filter(Q(codigo__icontains=q) | Q(cliente__nombres__icontains=q)
                       | Q(cliente__apellidos__icontains=q) | Q(cliente__nro_documento__icontains=q))
    if estado:
        qs = qs.filter(estado=estado)
    return render(request, "reservations/gestion_reservas.html", {
        "reservas": qs[:200], "q": q, "estado": estado, "estados": Reserva.Estado.choices})


@admin_required
@require_POST
def confirmar(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    try:
        services.confirmar_reserva(reserva, obtener_perfil(request.user))
    except ValidationError as e:
        _errores(request, e)
    else:
        messages.success(request, f"Reserva {reserva.codigo} confirmada. Se generaron las solicitudes a proveedores.")
    return redirect("reservations:detalle", pk)


# ================================================================ CU-17 Confirmar servicios reservados
@admin_required
def confirmaciones(request):
    estado = request.GET.get("estado", "pendiente")
    qs = ConfirmacionProveedor.objects.select_related("reserva", "proveedor", "gestionado_por")
    if estado:
        qs = qs.filter(estado=estado)
    return render(request, "reservations/confirmaciones.html", {
        "confirmaciones": qs[:200], "estado": estado, "estados": ConfirmacionProveedor.Estado.choices})


@admin_required
def responder_confirmacion(request, pk):
    conf = get_object_or_404(ConfirmacionProveedor.objects.select_related("reserva", "proveedor"), pk=pk)
    form = ResponderConfirmacionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.responder_confirmacion(conf, form.cleaned_data["estado"], form.cleaned_data["codigo_confirmacion"],
                                            form.cleaned_data["observacion"], obtener_perfil(request.user))
        except ValidationError as e:
            _errores(request, e)
        else:
            messages.success(request, "Respuesta del proveedor registrada.")
            return redirect("reservations:confirmaciones")
    return render(request, "reservations/responder_confirmacion.html", {"conf": conf, "form": form})


@admin_required
@require_POST
def generar_confirmaciones(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk, estado=Reserva.Estado.CONFIRMADA)
    n = services.generar_solicitudes_proveedor(reserva)
    messages.success(request, f"{n} solicitud(es) nueva(s) a proveedores." if n else "No había servicios nuevos que solicitar.")
    return redirect("reservations:detalle", pk)


# ================================================================ CU-23 Gestionar clientes
@admin_required
def clientes(request):
    qs = services.clientes()
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(nombres__icontains=q) | Q(apellidos__icontains=q) | Q(nro_documento__icontains=q)
                       | Q(usuario__email__icontains=q))
    return render(request, "reservations/clientes.html", {"clientes": qs[:200], "q": q})


@admin_required
def cliente_nuevo(request):
    form = ClienteNuevoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        perfil = services.registrar_cliente_por_agencia(form.cleaned_data)
        messages.success(request, f"Cliente registrado. Se envió a {perfil.usuario.email} un enlace para crear su contraseña.")
        return redirect("reservations:cliente_detalle", perfil.pk)
    return render(request, "reservations/cliente_form.html", {"form": form, "titulo": "Nuevo cliente"})


@admin_required
def cliente_editar(request, pk):
    perfil = get_object_or_404(services.clientes(), pk=pk)
    form = PerfilForm(request.POST or None, instance=perfil)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Datos del cliente actualizados.")
        return redirect("reservations:cliente_detalle", pk)
    return render(request, "reservations/cliente_form.html", {"form": form, "titulo": f"Editar cliente: {perfil}"})


@admin_required
def cliente_detalle(request, pk):
    perfil = get_object_or_404(services.clientes(), pk=pk)
    return render(request, "reservations/cliente_detalle.html", {
        "cliente": perfil, "reservas": perfil.reservas.select_related("paquete")})


# ================================================================ CU-24 Documentos de viaje
@require_POST
def documento_subir(request, pk):
    reserva = _reserva_visible(request, pk)
    form = DocumentoViajeForm(request.POST, request.FILES, reserva=reserva)
    if form.is_valid():
        form.save()
        messages.success(request, "Documento cargado.")
    else:
        for campo, errores in form.errors.items():
            for e in errores:
                messages.error(request, f"{form.fields[campo].label if campo in form.fields else ''}: {e}")
    return redirect("reservations:detalle", pk)


def _documento_visible(request, pk):
    doc = get_object_or_404(DocumentoViaje.objects.select_related("pasajero__reserva"), pk=pk)
    if not services.reservas_visibles(request.user).filter(pk=doc.pasajero.reserva_id).exists():
        raise Http404
    return doc


def documento_descargar(request, pk):
    """Se sirve con control de acceso (no por /media/) porque son documentos personales."""
    doc = _documento_visible(request, pk)
    extension = os.path.splitext(doc.archivo.name)[1]
    return FileResponse(doc.archivo.open("rb"), as_attachment=True,
                        filename=f"{doc.tipo}_{doc.pasajero.nro_documento}{extension}")


@require_POST
def documento_eliminar(request, pk):
    doc = _documento_visible(request, pk)
    reserva_pk = doc.pasajero.reserva_id
    doc.archivo.delete(save=False)
    doc.delete()
    messages.success(request, "Documento eliminado.")
    return redirect("reservations:detalle", reserva_pk)


# ================================================================ CU-25 Itinerario
def itinerario(request, pk):
    reserva = _reserva_visible(request, pk)
    return render(request, "reservations/itinerario.html", {"reserva": reserva, **services.itinerario(reserva)})


def itinerario_pdf(request, pk):
    reserva = _reserva_visible(request, pk)
    return services.itinerario_pdf(reserva).respuesta(f"itinerario_{reserva.codigo}.pdf")


@admin_required
def cronograma(request, paquete_pk, actividad_pk=None):
    """Crear el cronograma de actividades del paquete (base de todos los itinerarios)."""
    paquete = get_object_or_404(Paquete, pk=paquete_pk)
    actividad = get_object_or_404(PaqueteActividad, pk=actividad_pk, paquete=paquete) if actividad_pk else None
    form = ActividadForm(request.POST or None, instance=actividad, paquete=paquete)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.paquete = paquete
        obj.save()
        messages.success(request, "Actividad guardada.")
        return redirect("reservations:cronograma", paquete.pk)
    return render(request, "reservations/cronograma.html", {
        "paquete": paquete, "actividades": paquete.actividades.all(), "form": form, "editando": actividad})


@admin_required
@require_POST
def cronograma_eliminar(request, paquete_pk, actividad_pk):
    get_object_or_404(PaqueteActividad, pk=actividad_pk, paquete_id=paquete_pk).delete()
    messages.success(request, "Actividad eliminada.")
    return redirect("reservations:cronograma", paquete_pk)


@admin_required
def cronograma_paquetes(request):
    return render(request, "reservations/cronograma_paquetes.html", {
        "paquetes": Paquete.objects.exclude(estado=Paquete.Estado.ARCHIVADO).select_related("destino")})
