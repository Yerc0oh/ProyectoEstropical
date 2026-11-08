"""Vistas del Sprint 4. Ninguna es pública. Cliente: solo sus reservas, pagos y facturas.
El Administrador cumple también el papel de cajero/contador (no hay más roles en el sistema)."""
from datetime import date

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.services import obtener_perfil
from apps.core.access import admin_required, es_administrador
from apps.core.views_base import AdminCreateView, AdminListView
from apps.reservations.models import Reserva
from apps.reservations.services import reservas_visibles

from . import services
from .forms import (AnularFacturaForm, CierreCajaForm, ExtractoForm, FacturaForm, PagoEnLineaForm,
                    PagoProveedorForm, PagoVentanillaForm, PlanCuotasForm, ProcesarReembolsoForm)
from .models import CierreCaja, Factura, Pago, PagoProveedor, Reembolso, SaldoReserva


def _errores(request, error):
    for m in getattr(error, "messages", [str(error)]):
        messages.error(request, m)


def _reserva(request, pk):
    return get_object_or_404(reservas_visibles(request.user), pk=pk)


# ================================================================ CU-26 Pagar reserva
def pagar(request, pk):
    reserva = _reserva(request, pk)
    try:
        services._verificar_pagable(reserva)
    except ValidationError as e:
        _errores(request, e)
        return redirect("reservations:detalle", pk)
    monto, cuota = services.monto_a_pagar(reserva)
    form = PagoEnLineaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            pago, mensaje = services.pagar_en_linea(reserva, form.cleaned_data["metodo"],
                                                    form.cleaned_data.get("numero_tarjeta", ""))
        except ValidationError as e:
            _errores(request, e)
        else:
            if pago.estado == Pago.Estado.COMPLETADO:
                messages.success(request, f"Pago aprobado. Comprobante {pago.nro_comprobante}.")
                return redirect("payments:pago_resultado", pago.pk)
            messages.error(request, f"Pago rechazado: {mensaje}")
    return render(request, "payments/pagar.html", {
        "reserva": reserva, "monto": monto, "cuota": cuota, "form": form,
        "referencia_qr": f"ESTROPICAL|{reserva.codigo}|{monto}"})


def pago_resultado(request, pk):
    pago = get_object_or_404(Pago.objects.select_related("reserva", "cuota"), pk=pk)
    _reserva(request, pago.reserva_id)        # 404 si no es suya
    return render(request, "payments/pago_resultado.html", {"pago": pago})


def comprobante_pdf(request, pk):
    pago = get_object_or_404(Pago.objects.select_related("reserva", "reserva__paquete", "reserva__cliente",
                                                         "cuota", "registrado_por"),
                             pk=pk, estado=Pago.Estado.COMPLETADO)
    _reserva(request, pago.reserva_id)
    return services.comprobante_pdf(pago).respuesta(f"comprobante_{pago.nro_comprobante}.pdf")


# ================================================================ CU-27 Pagar en cuotas
def cuotas(request, pk):
    reserva = _reserva(request, pk)
    form = PlanCuotasForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            plan = services.crear_plan_cuotas(reserva, form.cleaned_data["cantidad"])
        except ValidationError as e:
            _errores(request, e)
        else:
            messages.success(request, f"Plan de {len(plan)} cuotas creado. Paga la primera para asegurar tu reserva.")
            return redirect("payments:estado_cuenta", pk)
    return render(request, "payments/cuotas.html", {
        "reserva": reserva, "form": form, "saldo": services.saldo_pendiente(reserva),
        "cuotas": reserva.cuotas.all()})


@require_POST
def anular_cuotas(request, pk):
    reserva = _reserva(request, pk)
    n = services.anular_plan_cuotas(reserva)
    messages.success(request, f"Se anularon {n} cuota(s) pendientes. Ahora puedes pagar el saldo completo.")
    return redirect("payments:estado_cuenta", pk)


# ================================================================ CU-29 Estado de cuenta
def estados_de_cuenta(request):
    saldos = (SaldoReserva.objects.filter(cliente__usuario=request.user)
              .select_related("reserva", "reserva__paquete").order_by("-reserva__fecha_reserva"))
    return render(request, "payments/estados_de_cuenta.html", {
        "saldos": saldos, "total_pendiente": saldos.aggregate(s=Sum("saldo_pendiente"))["s"] or 0})


def estado_cuenta(request, pk):
    reserva = _reserva(request, pk)
    return render(request, "payments/estado_cuenta.html", {
        **services.estado_de_cuenta(reserva), "es_admin_vista": es_administrador(request.user)})


# ================================================================ CU-31 Descargar facturas
def mis_facturas(request):
    facturas = Factura.objects.filter(reserva__cliente__usuario=request.user).select_related("reserva")
    return render(request, "payments/mis_facturas.html", {"facturas": facturas})


def factura_pdf(request, pk):
    factura = get_object_or_404(Factura.objects.select_related("reserva", "reserva__paquete"), pk=pk)
    if not es_administrador(request.user) and factura.reserva.cliente.usuario_id != request.user.pk:
        raise Http404
    return services.factura_pdf(factura).respuesta(f"factura_{factura.nro_factura}.pdf")


# ================================================================ CU-28 Pago en ventanilla
@admin_required
def ventanilla(request):
    codigo = request.GET.get("codigo", "").strip().upper()
    reserva = Reserva.objects.filter(codigo=codigo).select_related("paquete", "cliente").first() if codigo else None
    if codigo and not reserva:
        messages.error(request, f"No existe la reserva {codigo}.")
    contexto = {"codigo": codigo, "reserva": reserva}
    if reserva:
        monto, cuota = services.monto_a_pagar(reserva)
        form = PagoVentanillaForm(request.POST or None, initial={"monto": monto})
        if request.method == "POST" and form.is_valid():
            d = form.cleaned_data
            try:
                pago = services.registrar_pago_ventanilla(reserva, d["metodo"], d["monto"], d["referencia"],
                                                          obtener_perfil(request.user))
            except ValidationError as e:
                _errores(request, e)
            else:
                messages.success(request, f"Pago registrado. Comprobante {pago.nro_comprobante}.")
                return redirect("payments:pago_resultado", pago.pk)
        contexto.update({"form": form, "monto": monto, "cuota": cuota,
                         "saldo": services.saldo_pendiente(reserva)})
    return render(request, "payments/ventanilla.html", contexto)


@admin_required
def gestion_pagos(request):
    qs = Pago.objects.select_related("reserva", "cuota", "registrado_por")
    g = request.GET
    if g.get("q"):
        qs = qs.filter(Q(reserva__codigo__icontains=g["q"]) | Q(nro_comprobante__icontains=g["q"])
                       | Q(referencia_transaccion__icontains=g["q"]))
    if g.get("estado"):
        qs = qs.filter(estado=g["estado"])
    if g.get("canal"):
        qs = qs.filter(canal=g["canal"])
    return render(request, "payments/gestion_pagos.html", {
        "pagos": qs[:300], "estados": Pago.Estado.choices, "canales": Pago.Canal.choices})


# ================================================================ CU-30 / CU-32 Facturas
@admin_required
def gestion_facturas(request):
    qs = Factura.objects.select_related("reserva", "emitida_por")
    q = request.GET.get("q", "").strip()
    if q:
        filtro = Q(reserva__codigo__icontains=q) | Q(nit_cliente__icontains=q) | Q(razon_social__icontains=q)
        if q.isdigit():
            filtro |= Q(nro_factura=int(q))
        qs = qs.filter(filtro)
    # reservas con pagos aún sin facturar
    por_facturar = [r for r in Reserva.objects.filter(pagos__estado="completado").distinct()
                    .select_related("cliente", "paquete")[:300] if services.monto_facturable(r) > 0]
    return render(request, "payments/gestion_facturas.html", {"facturas": qs[:300], "q": q,
                                                               "por_facturar": por_facturar[:50]})


@admin_required
def emitir_factura(request, reserva_pk):
    reserva = get_object_or_404(Reserva.objects.select_related("cliente", "paquete"), pk=reserva_pk)
    form = FacturaForm(request.POST or None, initial={
        "nit": reserva.cliente.nit or reserva.cliente.nro_documento,
        "razon_social": reserva.cliente.razon_social or reserva.cliente.nombre_completo})
    if request.method == "POST" and form.is_valid():
        try:
            factura = services.emitir_factura(reserva, form.cleaned_data["nit"], form.cleaned_data["razon_social"],
                                              obtener_perfil(request.user))
        except ValidationError as e:
            _errores(request, e)
        else:
            messages.success(request, f"Factura N° {factura.nro_factura} emitida por Bs {factura.monto}.")
            return redirect("payments:gestion_facturas")
    return render(request, "payments/emitir_factura.html", {
        "reserva": reserva, "form": form, "monto": services.monto_facturable(reserva)})


@admin_required
def anular_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    form = AnularFacturaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.anular_factura(factura, form.cleaned_data["motivo"], obtener_perfil(request.user))
        except ValidationError as e:
            _errores(request, e)
        else:
            messages.success(request, f"Factura N° {factura.nro_factura} anulada. El monto vuelve a quedar por facturar.")
            return redirect("payments:gestion_facturas")
    return render(request, "payments/anular_factura.html", {"factura": factura, "form": form})


# ================================================================ CU-33 Reembolsos
@admin_required
def reembolsos(request):
    estado = request.GET.get("estado", "pendiente")
    qs = Reembolso.objects.select_related("reserva", "reserva__cliente", "pago", "procesado_por")
    if estado:
        qs = qs.filter(estado=estado)
    return render(request, "payments/reembolsos.html", {
        "reembolsos": qs[:300], "estado": estado, "estados": Reembolso.Estado.choices})


@admin_required
def procesar_reembolso(request, pk):
    reembolso = get_object_or_404(Reembolso.objects.select_related("reserva", "pago"), pk=pk)
    form = ProcesarReembolsoForm(request.POST or None, initial={"metodo": reembolso.pago.metodo})
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            services.procesar_reembolso(reembolso, d["accion"] == "aprobar", d["metodo"], d["referencia"],
                                        obtener_perfil(request.user))
        except ValidationError as e:
            _errores(request, e)
        else:
            messages.success(request, "Reembolso procesado." if d["accion"] == "aprobar" else "Reembolso rechazado.")
            return redirect("payments:reembolsos")
    return render(request, "payments/procesar_reembolso.html", {"reembolso": reembolso, "form": form})


# ================================================================ CU-34 Conciliar pagos
@admin_required
def conciliacion(request):
    form = ExtractoForm(request.POST or None, request.FILES or None)
    resultados = None
    if request.method == "POST" and form.is_valid():
        try:
            resultados = services.conciliar_extracto(form.cleaned_data["archivo"], obtener_perfil(request.user))
        except ValidationError as e:
            _errores(request, e)
        else:
            n = sum(1 for r in resultados if r["resultado"] == "conciliado")
            messages.success(request, f"{n} pago(s) conciliado(s) a partir del extracto.")
    pendientes = (Pago.objects.filter(estado=Pago.Estado.COMPLETADO, conciliado=False)
                  .select_related("reserva").order_by("fecha_pago"))
    return render(request, "payments/conciliacion.html", {
        "form": form, "resultados": resultados, "pendientes": pendientes[:300],
        "total_pendiente": pendientes.aggregate(s=Sum("monto"))["s"] or 0})


@admin_required
@require_POST
def conciliar(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    try:
        services.conciliar_pago(pago, obtener_perfil(request.user))
    except ValidationError as e:
        _errores(request, e)
    else:
        messages.success(request, f"Pago {pago.nro_comprobante} conciliado.")
    return redirect("payments:conciliacion")


# ================================================================ CU-35 Cuentas por cobrar
@admin_required
def cuentas_por_cobrar(request):
    qs = (SaldoReserva.objects.filter(saldo_pendiente__gt=0, estado__in=Reserva.ACTIVAS)
          .select_related("reserva", "reserva__paquete", "cliente").order_by("-cuotas_vencidas", "reserva__paquete__fecha_salida"))
    if request.GET.get("vencidas"):
        qs = qs.filter(cuotas_vencidas__gt=0)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(codigo__icontains=q) | Q(cliente__nombres__icontains=q) | Q(cliente__apellidos__icontains=q))
    return render(request, "payments/cuentas_por_cobrar.html", {
        "saldos": qs[:300], "q": q, "total": qs.aggregate(s=Sum("saldo_pendiente"))["s"] or 0,
        "hoy": timezone.localdate()})


# ================================================================ CU-36 Pagos a proveedores
class PagoProveedorLista(AdminListView):
    model = PagoProveedor
    template_name = "payments/pagos_proveedor.html"
    titulo = "Pagos a proveedores"

    def get_queryset(self):
        qs = PagoProveedor.objects.select_related("proveedor", "confirmacion", "registrado_por")
        if self.request.GET.get("estado"):
            qs = qs.filter(estado=self.request.GET["estado"])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["por_pagar"] = (PagoProveedor.objects.filter(estado="pendiente").aggregate(s=Sum("monto"))["s"] or 0)
        return ctx


class PagoProveedorCrear(AdminCreateView):
    model = PagoProveedor
    form_class = PagoProveedorForm
    titulo = "Registrar pago a proveedor"
    url_listado = "payments:pagos_proveedor"
    success_message = "Pago a proveedor registrado como pendiente."

    def get_initial(self):
        inicial = super().get_initial()
        if self.request.GET.get("confirmacion"):
            inicial["confirmacion"] = self.request.GET["confirmacion"]
        return inicial

    def form_valid(self, form):
        form.instance.registrado_por = obtener_perfil(self.request.user)
        return super().form_valid(form)


@admin_required
@require_POST
def pago_proveedor_pagado(request, pk):
    pp = get_object_or_404(PagoProveedor, pk=pk)
    try:
        services.marcar_pago_proveedor_pagado(pp, request.POST.get("referencia", "").strip())
    except ValidationError as e:
        _errores(request, e)
    else:
        messages.success(request, "Pago a proveedor marcado como realizado.")
    return redirect("payments:pagos_proveedor")


# ================================================================ CU-37 Cierre de caja
@admin_required
def caja(request):
    try:
        fecha = date.fromisoformat(request.GET.get("fecha", ""))
    except ValueError:
        fecha = timezone.localdate()
    form = CierreCajaForm(request.POST or None, initial={"fecha": fecha})
    if request.method == "POST" and form.is_valid():
        try:
            cierre = services.cerrar_caja(form.cleaned_data["fecha"], obtener_perfil(request.user),
                                          form.cleaned_data["observaciones"])
        except ValidationError as e:
            _errores(request, e)
        else:
            messages.success(request, f"Caja del {cierre.fecha:%d/%m/%Y} cerrada. Saldo: Bs {cierre.saldo}.")
            return redirect("payments:cierre_detalle", cierre.pk)
    return render(request, "payments/caja.html", {
        "form": form, "mov": services.movimientos_de_caja(fecha), "ya_cerrada": CierreCaja.objects.filter(fecha=fecha).first(),
        "cierres": CierreCaja.objects.select_related("realizado_por")[:30]})


@admin_required
def cierre_detalle(request, pk):
    cierre = get_object_or_404(CierreCaja.objects.select_related("realizado_por"), pk=pk)
    return render(request, "payments/cierre_detalle.html", {
        "cierre": cierre, "pagos": cierre.pagos.select_related("reserva"),
        "reembolsos": cierre.reembolsos.select_related("reserva"),
        "proveedores": cierre.pagos_proveedor.select_related("proveedor")})
