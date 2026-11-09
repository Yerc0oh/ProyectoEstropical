"""Lógica de negocio de cuentas (fuera de las vistas para poder probarla)."""
import logging
import secrets

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.core.access import ROL_CLIENTE

from .models import Perfil
from .tokens import activation_token, email_change_token

logger = logging.getLogger(__name__)


def _enviar_correo(asunto, cuerpo, destinatario):
    """Envía el correo sin tumbar la petición si el transporte falla.

    En Render (plan gratuito) los puertos SMTP están bloqueados; un intento
    fallido puede tardar minutos y terminar en un 500. Registrar el error y
    devolver False permite que la cuenta ya creada siga siendo utilizable y que
    el usuario pueda pedir un reenvío cuando el correo esté bien configurado.
    """
    try:
        send_mail(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, [destinatario])
        return True
    except Exception:
        logger.exception("No se pudo enviar el correo a %s", destinatario)
        return False


def registrar_cliente(datos):
    """Crea usuario INACTIVO + perfil + rol Cliente y envía el correo de verificación.

    Usuario, perfil y rol se guardan en una sola transacción: si algo falla no queda
    ningún registro parcial. El correo se envía después de confirmar la transacción
    y su fallo no revierte la cuenta ni provoca un error 500.

    Devuelve ``(user, correo_enviado)``.
    """
    email = datos["email"].lower()
    with transaction.atomic():
        user = User.objects.create_user(
            username=email, email=email, password=datos["password1"],
            first_name=datos["nombres"], last_name=datos["apellidos"], is_active=False)
        Perfil.objects.create(
            usuario=user, nombres=datos["nombres"], apellidos=datos["apellidos"],
            tipo_documento=datos["tipo_documento"], nro_documento=datos["nro_documento"],
            telefono=datos.get("telefono", ""))
        user.groups.add(Group.objects.get(name=ROL_CLIENTE))
    correo_enviado = enviar_correo_activacion(user)
    return user, correo_enviado


def enviar_correo_activacion(user):
    enlace = settings.SITE_URL + reverse("accounts:activar", kwargs={
        "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": activation_token.make_token(user)})
    asunto = render_to_string("accounts/email/activation_subject.txt").strip()
    cuerpo = render_to_string("accounts/email/activation_email.txt",
                              {"user": user, "enlace": enlace})
    return _enviar_correo(asunto, cuerpo, user.email)


def _enlace_cambio_correo(user):
    """Construye el enlace con uid y token; no incluye correos ni contraseñas."""
    user._state.fields_cache.pop("perfil", None)
    return settings.SITE_URL + reverse("accounts:confirmar_cambio_correo", kwargs={
        "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": email_change_token.make_token(user)})


def enviar_correo_cambio(user, nuevo_email):
    asunto = render_to_string("accounts/email/cambio_correo_subject.txt").strip()
    cuerpo = render_to_string("accounts/email/cambio_correo_email.txt", {
        "user": user, "nuevo_email": nuevo_email,
        "enlace": _enlace_cambio_correo(user)})
    return _enviar_correo(asunto, cuerpo, nuevo_email)


def solicitar_cambio_correo(user, nuevo_email):
    """Guarda el correo pendiente y envía la verificación al nuevo destinatario.

    Cada solicitud reemplaza el correo pendiente y renueva el nonce, por lo que
    cualquier enlace enviado antes deja de ser válido. El correo y username
    actuales no se tocan hasta la confirmación.
    """
    with transaction.atomic():
        perfil = Perfil.objects.select_for_update().get(usuario=user)
        perfil.correo_pendiente = nuevo_email
        perfil.correo_pendiente_nonce = secrets.token_urlsafe(24)
        perfil.save(update_fields=["correo_pendiente", "correo_pendiente_nonce"])
        transaction.on_commit(lambda: enviar_correo_cambio(user, nuevo_email))


def confirmar_cambio_correo(user, token):
    """Aplica el cambio de correo si el token y el estado actual son válidos.

    Devuelve True solo si se actualizaron email y username de forma atómica.
    Ante token inválido, caducado, ya usado, correo ocupado o error de
    integridad, no se modifica nada y devuelve False.
    """
    try:
        with transaction.atomic():
            perfil = Perfil.objects.select_for_update().get(usuario=user)
            user.refresh_from_db(fields=["email", "username"])
            # Evita que el token use un perfil cacheado anterior a la solicitud.
            user._state.fields_cache.pop("perfil", None)

            if not perfil.correo_pendiente:
                return False
            if not email_change_token.check_token(user, token):
                return False

            nuevo_email = perfil.correo_pendiente
            ocupado = (User.objects
                       .filter(Q(email__iexact=nuevo_email) | Q(username__iexact=nuevo_email))
                       .exclude(pk=user.pk).exists())
            if ocupado:
                return False

            user.email = nuevo_email
            user.username = nuevo_email
            user.save(update_fields=["email", "username"])
            perfil.correo_pendiente = None
            perfil.correo_pendiente_nonce = ""
            perfil.save(update_fields=["correo_pendiente", "correo_pendiente_nonce"])
            return True
    except IntegrityError:
        # Colisión de username/email detectada por la base de datos: la
        # transacción revierte y el usuario conserva email y username anteriores.
        return False


def obtener_perfil(user):
    """Devuelve el perfil del usuario; lo crea si no existe (p. ej. superusuarios
    creados con createsuperuser). Nunca sobrescribe un perfil existente.

    Los valores generados (nro_documento "USR-<pk>", nombre de usuario) son
    provisionales, no información personal verificada. TODO: pedir los datos
    reales al administrador.
    """
    perfil, _ = Perfil.objects.get_or_create(usuario=user, defaults={
        "nombres": user.first_name or user.username, "apellidos": user.last_name,
        "nro_documento": f"USR-{user.pk}"})
    return perfil
