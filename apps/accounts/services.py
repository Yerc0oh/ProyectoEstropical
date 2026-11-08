"""Lógica de negocio de cuentas (fuera de las vistas para poder probarla)."""
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.core.access import ROL_CLIENTE

from .models import Perfil
from .tokens import activation_token


def registrar_cliente(datos):
    """Crea usuario INACTIVO + perfil + rol Cliente y envía el correo de verificación.

    Usuario, perfil y rol se guardan en una sola transacción: si algo falla no queda
    ningún registro parcial. El correo solo se envía después de confirmar la transacción.
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
        transaction.on_commit(lambda: enviar_correo_activacion(user))
    return user


def enviar_correo_activacion(user):
    enlace = settings.SITE_URL + reverse("accounts:activar", kwargs={
        "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": activation_token.make_token(user)})
    asunto = render_to_string("accounts/email/activation_subject.txt").strip()
    cuerpo = render_to_string("accounts/email/activation_email.txt",
                              {"user": user, "enlace": enlace})
    send_mail(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, [user.email])


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
