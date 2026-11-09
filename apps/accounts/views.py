import hashlib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import PasswordChangeView
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST

from apps.core.access import ROL_ADMIN, ROL_CLIENTE, admin_required, public

from .forms import (CambiarPasswordForm, CambiarRolForm, CambioCorreoForm, PerfilForm,
                    ReenviarActivacionForm, RegistroForm)
from .services import (confirmar_cambio_correo as aplicar_cambio_correo,
                       enviar_correo_activacion, obtener_perfil, registrar_cliente,
                       solicitar_cambio_correo as guardar_solicitud_correo)
from .tokens import activation_token


# ------------------------------------------------------------------ CU-01 Registrarse
@public
def registro(request):
    if request.user.is_authenticated:
        return redirect("core:home")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        _, correo_enviado = registrar_cliente(form.cleaned_data)
        return render(request, "accounts/registro_pendiente.html",
                      {"email": form.cleaned_data["email"],
                       "correo_enviado": correo_enviado})
    return render(request, "accounts/registro.html", {"form": form})


@public
def activar(request, uidb64, token):
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user and activation_token.check_token(user, token):
        user.is_active = True
        user.save(update_fields=["is_active"])
        messages.success(request, "Correo verificado. Ya puedes iniciar sesión.")
        return redirect("accounts:login")
    return render(request, "accounts/activacion_fallida.html", status=400)


# --------------------------------------------------- CU-01 Reenviar verificación
def _clave_reenvio(email):
    """Marca de throttling; nunca guarda el correo, tokens ni contraseñas."""
    return "accounts:reenvio:" + hashlib.sha256(email.encode("utf-8")).hexdigest()


@public
def reenviar_activacion(request):
    form = ReenviarActivacionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        espera = getattr(settings, "ACTIVATION_RESEND_COOLDOWN", 60)
        if cache.add(_clave_reenvio(email), True, timeout=espera):
            user = User.objects.filter(email__iexact=email, is_active=False).first()
            if user:
                enviar_correo_activacion(user)
        # Misma respuesta exista o no la cuenta, esté activa o se haya limitado.
        return render(request, "accounts/reenvio_confirmacion.html")
    return render(request, "accounts/reenvio_form.html", {"form": form})
# CU-02 (login/logout) y CU-03 (recuperar contraseña) usan las vistas de Django: ver urls.py


# ------------------------------------------------------------------ CU-05 Perfil
@login_required
def perfil(request):
    """Cualquier usuario autenticado edita únicamente su propio perfil.

    El perfil se obtiene siempre desde request.user: la vista no acepta un id de
    usuario, por lo que no es posible editar el perfil de otra persona.
    """
    obj = obtener_perfil(request.user)
    form = PerfilForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perfil actualizado.")
        return redirect("accounts:perfil")
    return render(request, "accounts/perfil.html", {
        "form": form,
        "email": request.user.email,
        "correo_pendiente": obj.correo_pendiente,
        "perfil_provisional": obj.nro_documento == f"USR-{request.user.pk}",
    })


# ------------------------------------------------------- CU-05 Cambiar correo
@login_required
def cambio_correo(request):
    """Solicita un cambio de correo; no modifica la cuenta hasta confirmar."""
    form = CambioCorreoForm(request.POST or None, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        guardar_solicitud_correo(request.user, form.cleaned_data["email"])
        return render(request, "accounts/cambio_correo_solicitado.html",
                      {"nuevo_email": form.cleaned_data["email"]})
    return render(request, "accounts/cambio_correo_form.html", {
        "form": form,
        "email": request.user.email,
        "correo_pendiente": obtener_perfil(request.user).correo_pendiente,
    })


@login_required
def confirmar_cambio_correo(request, uidb64, token):
    """Confirma el cambio desde el enlace enviado al nuevo correo."""
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # El enlace solo puede aplicarse a la cuenta que tiene la sesión iniciada.
    if user is None or user.pk != request.user.pk:
        return render(request, "accounts/cambio_correo_invalido.html", status=400)

    if aplicar_cambio_correo(user, token):
        messages.success(request,
                         "Correo actualizado. A partir de ahora inicia sesión con el nuevo correo.")
        return redirect("accounts:perfil")
    return render(request, "accounts/cambio_correo_invalido.html", status=400)


# ----------------------------------------------------- CU-05 Cambiar contraseña
class CambiarPasswordView(PasswordChangeView):
    """Vista nativa de Django: valida la contraseña actual, los validadores y
    conserva la sesión con update_session_auth_hash()."""

    template_name = "accounts/cambio_password_form.html"
    form_class = CambiarPasswordForm
    success_url = reverse_lazy("accounts:perfil")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Contraseña actualizada.")
        return response


# ------------------------------------------------------------------ CU-06 Gestionar usuarios
@admin_required
def usuarios(request):
    qs = (User.objects.select_related("perfil").prefetch_related("groups")
          .order_by("-date_joined"))
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(email__icontains=q)
    return render(request, "accounts/usuarios.html", {
        "usuarios": qs[:200], "q": q, "roles": [ROL_CLIENTE, ROL_ADMIN]})


@admin_required
@require_POST
def usuario_alternar_activo(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "No puedes bloquear tu propia cuenta.")
    else:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        messages.success(request, f"Cuenta {'activada' if user.is_active else 'bloqueada'}.")
    return redirect("accounts:usuarios")


@admin_required
@require_POST
def usuario_cambiar_rol(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = CambiarRolForm(request.POST)
    if user == request.user:
        messages.error(request, "No puedes cambiar tu propio rol.")
    elif form.is_valid():
        user.groups.remove(*Group.objects.filter(name__in=[ROL_ADMIN, ROL_CLIENTE]))
        user.groups.add(Group.objects.get(name=form.cleaned_data["rol"]))
        messages.success(request, "Rol actualizado.")
    return redirect("accounts:usuarios")
