from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from apps.core.access import public

from . import views
from .forms import LoginForm

app_name = "accounts"

urlpatterns = [
    # CU-01 Registrarse (+ verificación de correo)
    path("registro/", views.registro, name="registro"),
    path("activar/<uidb64>/<token>/", views.activar, name="activar"),
    path("reenviar-verificacion/", views.reenviar_activacion, name="reenviar_activacion"),
    # CU-02 / CU-04 Iniciar y cerrar sesión (el cierre es solo POST)
    path("ingresar/", public(auth_views.LoginView.as_view(
        template_name="accounts/login.html", authentication_form=LoginForm,
        redirect_authenticated_user=True)), name="login"),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    # CU-03 Recuperar contraseña
    path("recuperar/", public(auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset_form.html",
        email_template_name="accounts/email/password_reset_email.txt",
        subject_template_name="accounts/email/password_reset_subject.txt",
        success_url=reverse_lazy("accounts:password_reset_done"))), name="password_reset"),
    path("recuperar/enviado/", public(auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html")), name="password_reset_done"),
    path("recuperar/<uidb64>/<token>/", public(auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html",
        success_url=reverse_lazy("accounts:password_reset_complete"))), name="password_reset_confirm"),
    path("recuperar/listo/", public(auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html")), name="password_reset_complete"),
    # CU-05 Perfil
    path("perfil/", views.perfil, name="perfil"),
    path("perfil/correo/", views.cambio_correo, name="cambio_correo"),
    path("perfil/correo/confirmar/<uidb64>/<token>/", views.confirmar_cambio_correo,
         name="confirmar_cambio_correo"),
    path("perfil/contrasena/", views.CambiarPasswordView.as_view(), name="cambiar_password"),
    # CU-06 Gestionar usuarios (solo Administrador)
    path("gestion/usuarios/", views.usuarios, name="usuarios"),
    path("gestion/usuarios/<int:pk>/activo/", views.usuario_alternar_activo, name="usuario_activo"),
    path("gestion/usuarios/<int:pk>/rol/", views.usuario_cambiar_rol, name="usuario_rol"),
]
