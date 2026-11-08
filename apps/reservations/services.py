"""Reglas de negocio del Sprint 3 (fuera de las vistas para poder probarlas).

Cupos: NO se descuentan aquí. Lo hace el trigger trg_reserva_cupos de PostgreSQL
(migración 0002) cada vez que una reserva se crea, cambia de estado o de cantidad de
pasajeros. Aquí solo se verifica antes, para dar un mensaje claro al usuario.
"""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.crypto import get_random_string

from apps.accounts.models import Perfil
from apps.core.access import ROL_CLIENTE, es_administrador
from apps.packages.models import Paquete, PaqueteHotel, PaqueteVuelo

from .models import ConfirmacionProveedor, ParametroSistema, Pasajero, Promocion, Reserva

CENTAVO = Decimal("0.01")


def redondear(valor):
    return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


# ================================================================ consultas comunes
def paquetes_reservables():
    """Publicados, dentro de la vigencia de venta y que todavía no salieron."""
    hoy = timezone.localdate()
    return Paquete.objects.filter(estado=Paquete.Estado.PUBLICADO, venta_desde__lte=hoy,
                                  venta_hasta__gte=hoy, fecha_salida__gt=hoy)


def reservas_visibles(user):
    """Administrador: todas. Cliente: solo las suyas."""
    qs = Reserva.objects.select_related("paquete", "paquete__destino", "cliente")
    if es_administrador(user):
        return qs
    return qs.filter(cliente__usuario=user)


def total_pagado(reserva):
    """Suma de pagos completados (los pagos son del Sprint 4, app payments)."""
    return reserva.pagos.filter(estado="completado").aggregate(s=Sum("monto"))["s"] or Decimal("0")


def expirar_reservas_vencidas():
    """Pasa a 'expirada' las reservas pendientes cuyo plazo de pago venció sin ningún pago.
    El trigger libera los cupos. Se llama al listar reservas y desde
    `python manage.py expirar_reservas` (para programarlo con cron/Task Scheduler)."""
    vencidas = (Reserva.objects.filter(estado=Reserva.Estado.PENDIENTE, fecha_expiracion__lt=timezone.now())
                .exclude(pagos__estado="completado"))
    ids = list(vencidas.values_list("pk", flat=True))
    if ids:
        with transaction.atomic():
            Reserva.objects.filter(pk__in=ids).update(estado=Reserva.Estado.EXPIRADA)
            from apps.payments.models import Cuota
            Cuota.objects.filter(reserva_id__in=ids, estado="pendiente").update(estado="anulada")
    return len(ids)


# ================================================================ CU-18 cupones
def calcular_descuento(promocion, subtotal):
    if promocion is None:
        return Decimal("0")
    if promocion.tipo_descuento == Promocion.TipoDescuento.PORCENTAJE:
        descuento = subtotal * promocion.valor / 100
    else:
        descuento = promocion.valor
    return min(redondear(descuento), redondear(subtotal))


def validar_cupon(codigo, paquete, subtotal, excluir_reserva=None):
    """Devuelve la Promocion válida o lanza ValidationError con el motivo."""
    codigo = (codigo or "").strip().upper()
    promo = Promocion.objects.filter(codigo__iexact=codigo, activo=True).first()
    if not promo:
        raise ValidationError("El cupón no existe o no está activo.")
    hoy = timezone.localdate()
    if not (promo.vigente_desde <= hoy <= promo.vigente_hasta):
        raise ValidationError("El cupón no está vigente.")
    if promo.paquete_id and promo.paquete_id != paquete.pk:
        raise ValidationError("El cupón no aplica a este paquete.")
    if subtotal < promo.monto_minimo:
        raise ValidationError(f"El cupón exige una compra mínima de Bs {promo.monto_minimo}.")
    if promo.usos_maximos is not None:
        usos = promo.reservas.exclude(estado__in=[Reserva.Estado.CANCELADA, Reserva.Estado.EXPIRADA])
        if excluir_reserva is not None:
            usos = usos.exclude(pk=excluir_reserva.pk)
        if usos.count() >= promo.usos_maximos:
            raise ValidationError("El cupón ya alcanzó su número máximo de usos.")
    return promo


# ================================================================ CU-18 disponibilidad
def verificar_disponibilidad(paquete, pasajeros_adicionales):
    """RF-12: hay cupos en el paquete y asientos en todos sus vuelos."""
    if pasajeros_adicionales <= 0:
        return
    if paquete.cupos_disponibles < pasajeros_adicionales:
        raise ValidationError(
            f"Solo quedan {paquete.cupos_disponibles} cupos disponibles en este paquete.")
    for pv in PaqueteVuelo.objects.filter(paquete=paquete).select_related("vuelo"):
        if pv.vuelo.asientos_disponibles < pasajeros_adicionales:
            raise ValidationError(
                f"El vuelo {pv.vuelo.numero_vuelo} solo tiene {pv.vuelo.asientos_disponibles} asientos libres.")


def _guardar_con_trigger(objeto, **kwargs):
    """Guarda dentro de un savepoint: si el trigger deja cupos/asientos negativos, el CHECK
    de paquete/vuelo falla y se informa como error de disponibilidad."""
    try:
        with transaction.atomic():
            objeto.save(**kwargs)
    except IntegrityError as e:
        raise ValidationError("No hay disponibilidad suficiente para esta cantidad de pasajeros.") from e


# ================================================================ CU-18 realizar reserva
@transaction.atomic
def crear_reserva(paquete, cliente, creada_por, pasajeros, codigo_cupon="", observaciones=""):
    """`pasajeros`: lista de dicts con los campos de Pasajero.
    El cliente reserva para sí mismo; un administrador puede reservar para un cliente."""
    paquete = Paquete.objects.select_for_update().get(pk=paquete.pk)   # evita sobreventa concurrente
    if not paquetes_reservables().filter(pk=paquete.pk).exists():
        raise ValidationError("Este paquete ya no está a la venta.")
    n = len(pasajeros)
    if n == 0:
        raise ValidationError("Registra al menos un pasajero.")
    verificar_disponibilidad(paquete, n)

    subtotal = paquete.precio_persona * n
    promo = validar_cupon(codigo_cupon, paquete, subtotal) if codigo_cupon else None

    horas = ParametroSistema.obtener("horas_expiracion_reserva", 24)
    limite = timezone.now() + timedelta(hours=horas)
    reserva = Reserva(
        codigo=Reserva.nuevo_codigo(), cliente=cliente, creada_por=creada_por, paquete=paquete,
        promocion=promo, cantidad_pasajeros=n, precio_unitario=paquete.precio_persona,
        descuento=calcular_descuento(promo, subtotal), fecha_expiracion=limite,
        observaciones=observaciones or "")
    _guardar_con_trigger(reserva)          # el trigger descuenta cupos y asientos
    for datos in pasajeros:
        Pasajero.objects.create(reserva=reserva, **datos)
    return reserva


# ================================================================ CU-20 modificar reserva
@transaction.atomic
def actualizar_cantidad(reserva):
    """Después de editar los pasajeros: ajusta cantidad, precio y descuento.
    Reglas: con plan de cuotas no se cambia la cantidad; el nuevo total no puede
    quedar por debajo de lo ya pagado."""
    reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
    nueva = reserva.pasajeros.count()
    if nueva == 0:
        raise ValidationError("La reserva debe tener al menos un pasajero.")
    if nueva == reserva.cantidad_pasajeros:
        return reserva
    if reserva.cuotas.exclude(estado="anulada").exists():
        raise ValidationError("La reserva tiene un plan de cuotas: no se puede cambiar la cantidad de pasajeros.")
    paquete = Paquete.objects.select_for_update().get(pk=reserva.paquete_id)
    verificar_disponibilidad(paquete, nueva - reserva.cantidad_pasajeros)

    subtotal = reserva.precio_unitario * nueva
    if reserva.promocion and subtotal < reserva.promocion.monto_minimo:
        reserva.promocion = None      # ya no cumple el mínimo del cupón
    descuento = calcular_descuento(reserva.promocion, subtotal)
    if subtotal - descuento < total_pagado(reserva):
        raise ValidationError("El nuevo total sería menor que lo ya pagado. Solicita una cancelación parcial a la agencia.")
    reserva.cantidad_pasajeros = nueva
    reserva.descuento = descuento
    _guardar_con_trigger(reserva, update_fields=["cantidad_pasajeros", "descuento", "promocion"])
    return reserva


# ================================================================ CU-21 cancelar reserva
def calcular_cancelacion(reserva):
    """Usa la función fn_penalidad_cancelacion de PostgreSQL (migración payments 0002)."""
    from apps.payments.services import penalidad_cancelacion
    datos = penalidad_cancelacion(reserva)
    datos["dias"] = (reserva.paquete.fecha_salida - timezone.localdate()).days
    datos["pagado"] = total_pagado(reserva)
    return datos


@transaction.atomic
def cancelar_reserva(reserva, perfil, motivo):
    reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
    if not reserva.puede_cancelarse:
        raise ValidationError("Esta reserva ya no puede cancelarse.")
    calculo = calcular_cancelacion(reserva)
    reserva.estado = Reserva.Estado.CANCELADA
    reserva.fecha_cancelacion = timezone.now()
    reserva.motivo_cancelacion = (motivo or "")[:250]
    reserva.save(update_fields=["estado", "fecha_cancelacion", "motivo_cancelacion"])  # trigger libera cupos
    reserva.cuotas.filter(estado="pendiente").update(estado="anulada")
    ConfirmacionProveedor.objects.filter(reserva=reserva, estado="pendiente").update(
        estado="rechazada", fecha_respuesta=timezone.now(), observacion="Reserva cancelada por el cliente")
    from apps.payments.services import registrar_reembolsos
    registrar_reembolsos(reserva, calculo["penalidad"], calculo["reembolsable"])
    return calculo


# ================================================================ CU-22 confirmar reserva
@transaction.atomic
def confirmar_reserva(reserva, perfil):
    """Confirmación explícita del administrador: exige al menos un pago completado y
    que todos los pasajeros estén registrados. Genera las solicitudes a proveedores (CU-17)."""
    reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
    if not reserva.puede_confirmarse:
        raise ValidationError("Solo se confirman reservas pendientes.")
    if total_pagado(reserva) <= 0:
        raise ValidationError("La reserva aún no tiene pagos registrados.")
    if reserva.pasajeros.count() != reserva.cantidad_pasajeros:
        raise ValidationError("Faltan datos de pasajeros.")
    reserva.estado = Reserva.Estado.CONFIRMADA
    reserva.confirmada_por = perfil
    reserva.fecha_confirmacion = timezone.now()
    reserva.save(update_fields=["estado", "confirmada_por", "fecha_confirmacion"])
    generar_solicitudes_proveedor(reserva)
    return reserva


# ================================================================ CU-17 confirmar servicios
def generar_solicitudes_proveedor(reserva):
    """Una solicitud por cada vuelo y hotel del paquete (si no existe ya)."""
    creadas = 0
    detalle = f"{reserva.cantidad_pasajeros} pasajero(s)"
    for pv in PaqueteVuelo.objects.filter(paquete=reserva.paquete).select_related(
            "vuelo", "vuelo__proveedor", "vuelo__origen", "vuelo__destino"):
        v = pv.vuelo
        concepto = f"Vuelo {v.numero_vuelo} {v.origen.nombre} - {v.destino.nombre} ({pv.get_tramo_display()})"
        _, nueva = ConfirmacionProveedor.objects.get_or_create(
            reserva=reserva, proveedor=v.proveedor, concepto=concepto[:200],
            defaults={"observacion": detalle})
        creadas += nueva
    for ph in PaqueteHotel.objects.filter(paquete=reserva.paquete).select_related(
            "tipo_habitacion", "tipo_habitacion__hotel", "tipo_habitacion__hotel__proveedor"):
        hotel = ph.tipo_habitacion.hotel
        concepto = f"Hotel {hotel.nombre} - {ph.tipo_habitacion.nombre}, {ph.noches} noche(s)"
        _, nueva = ConfirmacionProveedor.objects.get_or_create(
            reserva=reserva, proveedor=hotel.proveedor, concepto=concepto[:200],
            defaults={"observacion": detalle})
        creadas += nueva
    return creadas


def responder_confirmacion(confirmacion, estado, codigo, observacion, perfil):
    if confirmacion.estado != ConfirmacionProveedor.Estado.PENDIENTE:
        raise ValidationError("Esta solicitud ya fue respondida.")
    if estado == ConfirmacionProveedor.Estado.CONFIRMADA and not codigo:
        raise ValidationError("Ingresa el código de confirmación que dio el proveedor.")
    confirmacion.estado = estado
    confirmacion.codigo_confirmacion = codigo or ""
    confirmacion.observacion = observacion or confirmacion.observacion
    confirmacion.gestionado_por = perfil
    confirmacion.fecha_respuesta = timezone.now()
    confirmacion.save()
    return confirmacion


# ================================================================ CU-23 gestionar clientes
@transaction.atomic
def registrar_cliente_por_agencia(datos):
    """El administrador registra a un cliente que llegó a la agencia. La cuenta queda activa y
    se le envía el correo de 'restablecer contraseña' para que defina la suya."""
    email = datos["email"].lower()
    user = User.objects.create_user(
        username=email, email=email, password=get_random_string(32),
        first_name=datos["nombres"], last_name=datos["apellidos"], is_active=True)
    campos = {k: v for k, v in datos.items() if k != "email"}
    perfil = Perfil.objects.create(usuario=user, **campos)
    user.groups.add(Group.objects.get(name=ROL_CLIENTE))
    form = PasswordResetForm({"email": email})
    if form.is_valid():
        url = urlparse(settings.SITE_URL)
        form.save(domain_override=url.netloc, use_https=url.scheme == "https",
                  email_template_name="accounts/email/password_reset_email.txt",
                  subject_template_name="accounts/email/password_reset_subject.txt")
    return perfil


def clientes():
    return (Perfil.objects.filter(usuario__groups__name=ROL_CLIENTE)
            .select_related("usuario").order_by("apellidos", "nombres"))


# ================================================================ CU-25 itinerario
def itinerario(reserva):
    """Cronograma día por día: vuelos, hoteles y actividades del paquete."""
    paquete = reserva.paquete
    vuelos = (PaqueteVuelo.objects.filter(paquete=paquete)
              .select_related("vuelo", "vuelo__origen", "vuelo__destino", "vuelo__proveedor")
              .order_by("vuelo__fecha_salida"))
    hoteles = (PaqueteHotel.objects.filter(paquete=paquete)
               .select_related("tipo_habitacion", "tipo_habitacion__hotel"))
    actividades = list(paquete.actividades.all())
    dias = []
    for n in range(1, paquete.duracion_dias + 1):
        fecha = paquete.fecha_salida + timedelta(days=n - 1)
        dias.append({
            "numero": n, "fecha": fecha,
            "vuelos": [pv for pv in vuelos if timezone.localtime(pv.vuelo.fecha_salida).date() == fecha],
            "actividades": [a for a in actividades if a.dia == n],
        })
    return {"paquete": paquete, "dias": dias, "vuelos": vuelos, "hoteles": hoteles,
            "pasajeros": reserva.pasajeros.all()}


def itinerario_pdf(reserva):
    from apps.core.pdf import DocumentoPDF
    datos = itinerario(reserva)
    p = datos["paquete"]
    pdf = DocumentoPDF(f"Itinerario {reserva.codigo}")
    pdf.titulo("Itinerario de viaje")
    pdf.par("Reserva", f"{reserva.codigo} ({reserva.get_estado_display()})")
    pdf.par("Paquete", p.nombre)
    pdf.par("Destino", str(p.destino))
    pdf.par("Fechas", f"{p.fecha_salida:%d/%m/%Y} al {p.fecha_retorno:%d/%m/%Y} ({p.duracion_dias} días)")
    pdf.par("Titular", reserva.cliente.nombre_completo)

    pdf.subtitulo("Pasajeros")
    pdf.tabla(["Nombre", "Documento", "Nacimiento"],
              [[str(x), f"{x.tipo_documento} {x.nro_documento}", f"{x.fecha_nacimiento:%d/%m/%Y}"]
               for x in datos["pasajeros"]], [250, 150, 95])

    if datos["vuelos"]:
        pdf.subtitulo("Vuelos")
        pdf.tabla(["Vuelo", "Ruta", "Salida", "Llegada"],
                  [[pv.vuelo.numero_vuelo, f"{pv.vuelo.origen.nombre} -> {pv.vuelo.destino.nombre}",
                    f"{timezone.localtime(pv.vuelo.fecha_salida):%d/%m/%Y %H:%M}",
                    f"{timezone.localtime(pv.vuelo.fecha_llegada):%d/%m/%Y %H:%M}"] for pv in datos["vuelos"]],
                  [70, 205, 110, 110])
    if datos["hoteles"]:
        pdf.subtitulo("Alojamiento")
        pdf.tabla(["Hotel", "Habitación", "Noches"],
                  [[ph.tipo_habitacion.hotel.nombre, ph.tipo_habitacion.nombre, str(ph.noches)]
                   for ph in datos["hoteles"]], [250, 175, 70], alinear_derecha=(2,))

    pdf.subtitulo("Cronograma")
    for d in datos["dias"]:
        pdf.texto(f"Día {d['numero']} - {d['fecha']:%d/%m/%Y}", 11, negrita=True)
        for pv in d["vuelos"]:
            pdf.texto(f"{timezone.localtime(pv.vuelo.fecha_salida):%H:%M}  Vuelo {pv.vuelo.numero_vuelo} "
                      f"{pv.vuelo.origen.nombre} -> {pv.vuelo.destino.nombre}", sangria=15)
        for a in d["actividades"]:
            hora = f"{a.hora_inicio:%H:%M}  " if a.hora_inicio else ""
            pdf.texto(f"{hora}{a.titulo}", sangria=15)
            if a.descripcion:
                pdf.texto(a.descripcion, 9, sangria=30, color=(0.35, 0.35, 0.35))
        if not d["vuelos"] and not d["actividades"]:
            pdf.texto("Día libre", sangria=15, color=(0.45, 0.45, 0.45))
        pdf.espacio(4)
    if p.condiciones:
        pdf.subtitulo("Condiciones")
        pdf.texto(p.condiciones, 9)
    return pdf
