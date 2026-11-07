"""Control de acceso del proyecto: tres tipos de visitante.

  * Sin cuenta  -> solo vistas públicas (marcadas con @public / login_not_required)
  * Cliente     -> grupo "Cliente"
  * Administrador -> grupo "Administrador" (o superusuario)

El middleware LoginRequiredMiddleware (config/settings/base.py) bloquea TODA vista
que no sea pública. Aquí se añade la distinción de rol.
"""
from functools import wraps

from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

ROL_ADMIN = "Administrador"
ROL_CLIENTE = "Cliente"

# Alias legible: @public marca una vista como accesible sin iniciar sesión.
public = login_not_required


def es_administrador(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name=ROL_ADMIN).exists()
    )


def es_cliente(user):
    return user.is_authenticated and user.groups.filter(name=ROL_CLIENTE).exists()


def rol_de(user):
    """'anonimo' | 'administrador' | 'cliente' | 'sin_rol'."""
    if not user.is_authenticated:
        return "anonimo"
    if es_administrador(user):
        return "administrador"
    if es_cliente(user):
        return "cliente"
    return "sin_rol"


# Decoradores para vistas basadas en funciones.
# Anónimo -> redirige al login; autenticado sin el rol -> 403.
def _rol_requerido(test):
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not test(request.user):
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


admin_required = _rol_requerido(es_administrador)
cliente_required = _rol_requerido(es_cliente)


# Mixins para vistas basadas en clases.
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return es_administrador(self.request.user)


class ClienteRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return es_cliente(self.request.user)
