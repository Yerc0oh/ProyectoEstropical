from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST

from apps.core.access import ROL_ADMIN, ROL_CLIENTE, admin_required, public

from .forms import CambiarRolForm, PerfilForm, RegistroForm
from .services import obtener_perfil, registrar_cliente
from .tokens import activation_token


# ------------------------------------------------------------------ CU-01 Registrarse
@public
def registro(request):
    if request.user.is_authenticated:
        return redirect("core:home")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        registrar_cliente(form.cleaned_data)
        return render(request, "accounts/registro_pendiente.html",
                      {"email": form.cleaned_data["email"]})
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
# CU-02 (login/logout) y CU-03 (recuperar contraseña) usan las vistas de Django: ver urls.py


# ------------------------------------------------------------------ CU-05 Perfil
def perfil(request):
    """Cualquier usuario autenticado (cliente o administrador) edita su perfil."""
    obj = obtener_perfil(request.user)
    form = PerfilForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perfil actualizado.")
        return redirect("accounts:perfil")
    return render(request, "accounts/perfil.html", {"form": form, "email": request.user.email})


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
