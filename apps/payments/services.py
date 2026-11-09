"""Reglas de negocio del Sprint 4 (pagos, facturación, reembolsos y caja).

Funciones de PostgreSQL que se usan (migración 0002):
  * fn_penalidad_cancelacion(reserva_id)  -> CU-21
  * fn_cerrar_caja(fecha, perfil_id)      -> CU-37
  * vista v_saldo_reserva                 -> CU-29, CU-35 (modelo SaldoReserva)
"""
import csv
import io
import re
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.pdf import DocumentoPDF
from apps.reservations.models import ParametroSistema, Reserva
from apps.reservations.services import expirar_reservas_vencidas, redondear, total_pagado

from .models import CierreCaja, Cuota, Factura, Metodo, Pago, PagoProveedor, Reembolso

CERO = Decimal("0")


# ================================================================ saldos
def saldo_pendiente(reserva):
    if reserva.estado not in Reserva.ACTIVAS:
        return CERO
    reserva.refresh_from_db(fields=["total"])
    return max(reserva.total - total_pagado(reserva), CERO)


def proxima_cuota(reserva):
    return reserva.cuotas.filter(estado=Cuota.Estado.PENDIENTE).order_by("numero").first()


def monto_a_pagar(reserva):
    """Con plan de cuotas se paga la siguiente cuota; si no, el saldo completo."""
    cuota = proxima_cuota(reserva)
    return (cuota.monto, cuota) if cuota else (saldo_pendiente(reserva), None)


def _verificar_pagable(reserva):
    expirar_reservas_vencidas()
    reserva.refresh_from_db()
    if reserva.estado not in Reserva.ACTIVAS:
        raise ValidationError(f"La reserva está {reserva.get_estado_display().lower()}: no admite pagos.")
    if saldo_pendiente(reserva) <= 0:
        raise ValidationError("La reserva no tiene saldo pendiente.")


# ================================================================ CU-26 pasarela simulada
TARJETA_RECHAZADA = "4000000000000002"     # número de prueba que siempre se rechaza


def _luhn_valido(numero):
    digitos = [int(d) for d in numero][::-1]
    total = sum(digitos[0::2]) + sum(sum(divmod(2 * d, 10)) for d in digitos[1::2])
    return total % 10 == 0


def pasarela_simulada(metodo, monto, numero_tarjeta=""):
    """Simula al 'Sistema de pagos' externo. Devuelve (aprobado, referencia, mensaje).
    El número de tarjeta se usa solo para validar y NO se guarda en ninguna parte (RNF-05)."""
    referencia = "SIM-" + uuid.uuid4().hex[:16].upper()
    if metodo == Metodo.TARJETA:
        numero = re.sub(r"\D", "", numero_tarjeta or "")
        if not (13 <= len(numero) <= 19) or not _luhn_valido(numero):
            return False, referencia, "Número de tarjeta inválido."
        if numero == TARJETA_RECHAZADA:
            return False, referencia, "La entidad emisora rechazó la transacción."
    return True, referencia, "Transacción aprobada."


@transaction.atomic
def _registrar_pago(reserva, cuota, monto, metodo, canal, estado, referencia, registrado_por):
    pago = Pago.objects.create(
        reserva=reserva, cuota=cuota, monto=monto, metodo=metodo, canal=canal, estado=estado,
        referencia_transaccion=referencia or None, registrado_por=registrado_por)
    if estado == Pago.Estado.COMPLETADO:
        pago.nro_comprobante = f"CP-{pago.pk:07d}"
        pago.save(update_fields=["nro_comprobante"])
        if cuota:
            cuota.estado = Cuota.Estado.PAGADA
            cuota.save(update_fields=["estado"])
    return pago


def pagar_en_linea(reserva, metodo, numero_tarjeta=""):
    """CU-26: el cliente paga el saldo (o la siguiente cuota) con QR o tarjeta."""
    if metodo not in (Metodo.QR, Metodo.TARJETA):
        raise ValidationError("En línea solo se acepta QR o tarjeta.")
    with transaction.atomic():
        reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
        _verificar_pagable(reserva)
        monto, cuota = monto_a_pagar(reserva)
    aprobado, referencia, mensaje = pasarela_simulada(metodo, monto, numero_tarjeta)
    estado = Pago.Estado.COMPLETADO if aprobado else Pago.Estado.FALLIDO
    pago = _registrar_pago(reserva, cuota, monto, metodo, Pago.Canal.EN_LINEA, estado, referencia, None)
    return pago, mensaje


@transaction.atomic
def registrar_pago_ventanilla(reserva, metodo, monto, referencia, cajero):
    """CU-28: pago presencial registrado por el personal de la agencia."""
    reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
    _verificar_pagable(reserva)
    monto = redondear(monto)
    esperado, cuota = monto_a_pagar(reserva)
    if cuota and monto != cuota.monto:
        raise ValidationError(f"La reserva paga en cuotas: el monto debe ser el de la cuota {cuota.numero} "
                              f"(Bs {cuota.monto}).")
    if monto <= 0 or monto > esperado:
        raise ValidationError(f"El monto debe estar entre Bs 0,01 y el saldo pendiente (Bs {esperado}).")
    referencia = (referencia or "").strip()
    if metodo in (Metodo.TRANSFERENCIA, Metodo.QR, Metodo.TARJETA) and not referencia:
        raise ValidationError("Ingresa el número de transacción o depósito.")
    if referencia and Pago.objects.filter(referencia_transaccion=referencia).exists():
        raise ValidationError("Ya existe un pago con esa referencia de transacción.")
    return _registrar_pago(reserva, cuota, monto, metodo, Pago.Canal.VENTANILLA,
                           Pago.Estado.COMPLETADO, referencia, cajero)


# ================================================================ CU-27 cuotas
@transaction.atomic
def crear_plan_cuotas(reserva, cantidad):
    """Divide el saldo en `cantidad` cuotas: la 1ra vence hoy y las demás cada 30 días.
    Todas deben vencer al menos 7 días antes de la salida."""
    reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
    _verificar_pagable(reserva)
    maximo = ParametroSistema.obtener("cuotas_maximas", 6)
    if not 2 <= cantidad <= maximo:
        raise ValidationError(f"Elige entre 2 y {maximo} cuotas.")
    if reserva.cuotas.filter(estado=Cuota.Estado.PENDIENTE).exists():
        raise ValidationError("La reserva ya tiene un plan de cuotas.")
    hoy = timezone.localdate()
    limite = reserva.paquete.fecha_salida - timedelta(days=7)
    ultima = hoy + timedelta(days=30 * (cantidad - 1))
    if ultima > limite:
        posibles = max((limite - hoy).days // 30 + 1, 1)
        raise ValidationError(f"No alcanza el tiempo antes del viaje: como máximo {posibles} cuota(s).")
    saldo = saldo_pendiente(reserva)
    base = redondear(saldo / cantidad)
    siguiente = (reserva.cuotas.order_by("-numero").values_list("numero", flat=True).first() or 0) + 1
    cuotas = []
    for i in range(cantidad):
        monto = base if i < cantidad - 1 else saldo - base * (cantidad - 1)   # el redondeo va a la última
        cuotas.append(Cuota.objects.create(reserva=reserva, numero=siguiente + i, monto=monto,
                                           fecha_vencimiento=hoy + timedelta(days=30 * i)))
    return cuotas


@transaction.atomic
def anular_plan_cuotas(reserva):
    """Anula las cuotas pendientes (por ejemplo, si el cliente prefiere pagar todo junto)."""
    return reserva.cuotas.filter(estado=Cuota.Estado.PENDIENTE).update(estado=Cuota.Estado.ANULADA)


# ================================================================ CU-29 estado de cuenta
def estado_de_cuenta(reserva):
    reserva.refresh_from_db()
    pagado = total_pagado(reserva)
    reembolsado = (reserva.reembolsos.filter(estado=Reembolso.Estado.PROCESADO)
                   .aggregate(s=Sum("monto_reembolso"))["s"] or CERO)
    movimientos = [{"fecha": p.fecha_pago, "concepto": f"Pago {p.get_metodo_display()} ({p.get_canal_display()})"
                    + (f" - cuota {p.cuota.numero}" if p.cuota else ""),
                    "comprobante": p, "abono": p.monto if p.estado == Pago.Estado.COMPLETADO else None,
                    "cargo": None, "estado": p.get_estado_display()}
                   for p in reserva.pagos.select_related("cuota")]
    movimientos += [{"fecha": r.fecha_procesado or r.fecha_solicitud,
                     "concepto": f"Reembolso (penalidad Bs {r.penalidad})", "comprobante": None,
                     "abono": None, "cargo": r.monto_reembolso if r.estado == Reembolso.Estado.PROCESADO else None,
                     "estado": r.get_estado_display()}
                    for r in reserva.reembolsos.all()]
    movimientos.sort(key=lambda m: m["fecha"])
    return {"reserva": reserva, "total": reserva.total, "pagado": pagado, "reembolsado": reembolsado,
            "saldo": saldo_pendiente(reserva), "movimientos": movimientos,
            "cuotas": reserva.cuotas.all(), "proxima_cuota": proxima_cuota(reserva)}


# ================================================================ CU-21 / CU-33 reembolsos
def penalidad_cancelacion(reserva):
    with connection.cursor() as cur:
        cur.execute("SELECT porcentaje, penalidad, reembolsable FROM fn_penalidad_cancelacion(%s)",
                    [reserva.pk])
        porcentaje, penalidad, reembolsable = cur.fetchone()
    return {"porcentaje": porcentaje or CERO, "penalidad": penalidad or CERO,
            "reembolsable": reembolsable or CERO}


def registrar_reembolsos(reserva, penalidad, reembolsable):
    """Al cancelar: reparte penalidad y devolución entre los pagos completados.
    Quedan 'pendiente' hasta que el personal los procese (CU-33)."""
    creados, por_devolver, por_retener = [], Decimal(reembolsable), Decimal(penalidad)
    for pago in reserva.pagos.filter(estado=Pago.Estado.COMPLETADO).order_by("-fecha_pago"):
        devolver = min(pago.monto, por_devolver)
        retener = min(pago.monto - devolver, por_retener)
        por_devolver -= devolver
        por_retener -= retener
        if devolver > 0 or retener > 0:
            creados.append(Reembolso.objects.create(reserva=reserva, pago=pago, penalidad=retener,
                                                    monto_reembolso=devolver))
    return creados


@transaction.atomic
def procesar_reembolso(reembolso, aprobar, metodo, referencia, perfil):
    reembolso = Reembolso.objects.select_for_update().get(pk=reembolso.pk)
    if reembolso.estado != Reembolso.Estado.PENDIENTE:
        raise ValidationError("Este reembolso ya fue procesado.")
    if aprobar:
        if not metodo:
            raise ValidationError("Indica el método de devolución.")
        if metodo != Metodo.EFECTIVO and not referencia:
            raise ValidationError("Ingresa la referencia de la devolución.")
        reembolso.estado = Reembolso.Estado.PROCESADO
        reembolso.metodo = metodo
        reembolso.referencia = referencia or ""
    else:
        reembolso.estado = Reembolso.Estado.RECHAZADO
    reembolso.fecha_procesado = timezone.now()
    reembolso.procesado_por = perfil
    reembolso.save()
    # El pago se deja como 'completado': el ingreso ya entró a caja ese día y la devolución
    # se registra como egreso el día que se procesa (así cuadra fn_cerrar_caja).
    return reembolso


# ================================================================ CU-30/31/32 facturas
NIT_VALIDO = re.compile(r"^(0|\d{4,15})(-\d?[A-Z]{1,2})?$")


def validar_nit(nit, razon_social):
    nit = (nit or "").strip().upper()
    razon_social = (razon_social or "").strip()
    if not NIT_VALIDO.match(nit):
        raise ValidationError("NIT/CI inválido: solo números (4 a 15 dígitos), con complemento opcional (p. ej. 1234567-1A). "
                              "Usa 0 para 'sin NIT'.")
    if nit == "0":
        razon_social = razon_social or "S/N"
    if len(razon_social) < 2:
        raise ValidationError("Ingresa la razón social o nombre para la factura.")
    return nit, razon_social[:150]


def monto_facturable(reserva):
    facturado = (reserva.facturas.filter(estado=Factura.Estado.EMITIDA)
                 .aggregate(s=Sum("monto"))["s"] or CERO)
    return max(total_pagado(reserva) - facturado, CERO)


@transaction.atomic
def emitir_factura(reserva, nit, razon_social, perfil):
    nit, razon_social = validar_nit(nit, razon_social)
    monto = monto_facturable(reserva)
    if monto <= 0:
        raise ValidationError("No hay pagos pendientes de facturar en esta reserva.")
    with connection.cursor() as cur:   # numeración correlativa sin huecos ni duplicados
        cur.execute("LOCK TABLE factura IN SHARE ROW EXCLUSIVE MODE")
    numero = (Factura.objects.order_by("-nro_factura").values_list("nro_factura", flat=True).first() or 0) + 1
    return Factura.objects.create(
        nro_factura=numero, reserva=reserva, nit_cliente=nit, razon_social=razon_social,
        concepto=f"Paquete turístico {reserva.paquete.nombre} - Reserva {reserva.codigo}"[:250],
        monto=monto, emitida_por=perfil)


@transaction.atomic
def anular_factura(factura, motivo, perfil):
    factura = Factura.objects.select_for_update().get(pk=factura.pk)
    if factura.estado == Factura.Estado.ANULADA:
        raise ValidationError("La factura ya está anulada.")
    if not (motivo or "").strip():
        raise ValidationError("Indica el motivo de la anulación.")
    factura.estado = Factura.Estado.ANULADA
    factura.fecha_anulacion = timezone.now()
    factura.anulada_por = perfil
    factura.motivo_anulacion = motivo.strip()[:250]
    factura.save()
    return factura


def _bs(valor):
    """1234.5 -> '1.234,50' (formato boliviano)."""
    entero, dec = f"{Decimal(valor):,.2f}".split(".")
    return f"{entero.replace(',', '.')},{dec}"


def factura_pdf(factura):
    pdf = DocumentoPDF(f"Factura N° {factura.nro_factura}")
    pdf.titulo(f"FACTURA N° {factura.nro_factura}")
    pdf.texto("Tropical Tours Ltda. · NIT 1013389020 · La Paz, Bolivia", 9, color=(0.35, 0.35, 0.35))
    pdf.texto("Documento académico sin validez fiscal (no es facturación electrónica del SIN).", 8,
              color=(0.5, 0.5, 0.5))
    pdf.espacio(6)
    pdf.par("Fecha de emisión", f"{timezone.localtime(factura.fecha_emision):%d/%m/%Y %H:%M}")
    pdf.par("Señor(es)", factura.razon_social)
    pdf.par("NIT / CI", factura.nit_cliente)
    pdf.par("Reserva", factura.reserva.codigo)
    pdf.subtitulo("Detalle")
    r = factura.reserva
    pdf.tabla(["Cant.", "Concepto", "Importe (Bs)"],
              [[str(r.cantidad_pasajeros), factura.concepto, _bs(factura.monto)]],
              [45, 350, 100], alinear_derecha=(0, 2))
    pdf.linea()
    pdf.par("TOTAL Bs", _bs(factura.monto))
    if factura.estado == Factura.Estado.ANULADA:
        pdf.marca_de_agua("ANULADA")
        pdf.espacio(10)
        pdf.par("Anulada el", f"{timezone.localtime(factura.fecha_anulacion):%d/%m/%Y %H:%M}")
        pdf.par("Motivo", factura.motivo_anulacion)
    return pdf


def comprobante_pdf(pago):
    r = pago.reserva
    pdf = DocumentoPDF(f"Comprobante {pago.nro_comprobante}")
    pdf.titulo("Comprobante de pago")
    pdf.par("N° de comprobante", pago.nro_comprobante)
    pdf.par("Fecha", f"{timezone.localtime(pago.fecha_pago):%d/%m/%Y %H:%M}")
    pdf.par("Reserva", f"{r.codigo} - {r.paquete.nombre}")
    pdf.par("Cliente", r.cliente.nombre_completo)
    pdf.par("Método", f"{pago.get_metodo_display()} ({pago.get_canal_display()})")
    if pago.cuota:
        pdf.par("Cuota", f"{pago.cuota.numero}")
    pdf.par("Referencia", pago.referencia_transaccion or "-")
    if pago.registrado_por:
        pdf.par("Atendido por", pago.registrado_por.nombre_completo)
    pdf.linea()
    pdf.par("MONTO PAGADO Bs", _bs(pago.monto), tam=12)
    pdf.espacio(6)
    pdf.par("Saldo pendiente Bs", _bs(saldo_pendiente(r)))
    pdf.espacio(10)
    pdf.texto("Este comprobante no es una factura. Puedes solicitarla en la agencia.", 9,
              color=(0.4, 0.4, 0.4))
    return pdf


# ================================================================ CU-34 conciliación
@transaction.atomic
def conciliar_pago(pago, perfil):
    if pago.estado != Pago.Estado.COMPLETADO:
        raise ValidationError("Solo se concilian pagos completados.")
    if pago.conciliado:
        return pago
    pago.conciliado = True
    pago.fecha_conciliacion = timezone.localdate()
    pago.conciliado_por = perfil
    pago.save(update_fields=["conciliado", "fecha_conciliacion", "conciliado_por"])
    return pago


def conciliar_extracto(archivo, perfil):
    """Compara un extracto CSV (columnas: referencia,monto) con los pagos registrados.
    Devuelve una lista de resultados por fila: conciliado / ya_conciliado / monto_distinto / no_encontrado."""
    try:
        texto = archivo.read().decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValidationError("El archivo debe ser CSV en UTF-8.") from e
    resultados = []
    for fila in csv.reader(io.StringIO(texto)):
        if len(fila) < 2 or not fila[0].strip():
            continue
        referencia = fila[0].strip()
        try:
            monto = redondear(Decimal(fila[1].strip().replace(",", ".")))
        except InvalidOperation:
            continue    # encabezado u otra fila no numérica
        pago = (Pago.objects.filter(referencia_transaccion=referencia).first()
                or Pago.objects.filter(nro_comprobante=referencia).first())
        if not pago or pago.estado != Pago.Estado.COMPLETADO:
            resultado = "no_encontrado"
        elif pago.monto != monto:
            resultado = "monto_distinto"
        elif pago.conciliado:
            resultado = "ya_conciliado"
        else:
            conciliar_pago(pago, perfil)
            resultado = "conciliado"
        resultados.append({"referencia": referencia, "monto": monto, "pago": pago, "resultado": resultado})
    if not resultados:
        raise ValidationError("No se encontraron filas válidas (formato: referencia,monto).")
    return resultados


# ================================================================ CU-36 pagos a proveedores
@transaction.atomic
def marcar_pago_proveedor_pagado(pago_proveedor, referencia=""):
    if pago_proveedor.estado == PagoProveedor.Estado.PAGADO:
        raise ValidationError("Este pago ya fue realizado.")
    if pago_proveedor.cierre_caja_id:
        raise ValidationError("El pago pertenece a una caja cerrada.")
    pago_proveedor.estado = PagoProveedor.Estado.PAGADO
    pago_proveedor.fecha_pago = timezone.now()
    if referencia:
        pago_proveedor.referencia = referencia
    pago_proveedor.save(update_fields=["estado", "fecha_pago", "referencia"])
    return pago_proveedor


# ================================================================ CU-37 cierre de caja
def movimientos_de_caja(fecha):
    """Lo que entraría en el cierre de `fecha` (misma regla que fn_cerrar_caja)."""
    pagos = Pago.objects.filter(estado=Pago.Estado.COMPLETADO, cierre_caja__isnull=True, fecha_pago__date=fecha)
    reembolsos = Reembolso.objects.filter(estado=Reembolso.Estado.PROCESADO, cierre_caja__isnull=True,
                                          fecha_procesado__date=fecha)
    proveedores = PagoProveedor.objects.filter(estado=PagoProveedor.Estado.PAGADO, cierre_caja__isnull=True,
                                               fecha_pago__date=fecha)
    ingresos = pagos.aggregate(s=Sum("monto"))["s"] or CERO
    egresos = ((reembolsos.aggregate(s=Sum("monto_reembolso"))["s"] or CERO)
               + (proveedores.aggregate(s=Sum("monto"))["s"] or CERO))
    return {"fecha": fecha, "pagos": pagos.select_related("reserva"), "reembolsos": reembolsos.select_related("reserva"),
            "proveedores": proveedores.select_related("proveedor"),
            "ingresos": ingresos, "egresos": egresos, "saldo": ingresos - egresos}


def cerrar_caja(fecha, perfil, observaciones=""):
    if fecha > timezone.localdate():
        raise ValidationError("No se puede cerrar la caja de una fecha futura.")
    if CierreCaja.objects.filter(fecha=fecha).exists():
        raise ValidationError("La caja de esa fecha ya fue cerrada.")
    try:
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute("SELECT fn_cerrar_caja(%s, %s)", [fecha, perfil.pk])
                cierre_id = cur.fetchone()[0]
            if observaciones:
                CierreCaja.objects.filter(pk=cierre_id).update(observaciones=observaciones[:250])
    except IntegrityError as e:
        raise ValidationError("La caja de esa fecha ya fue cerrada.") from e
    return CierreCaja.objects.get(pk=cierre_id)
