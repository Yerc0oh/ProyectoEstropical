from apps.core.access import es_administrador, es_cliente


def roles(request):
    """Disponibiliza es_admin / es_cliente y el proveedor del usuario."""
    u = request.user
    return {
        "es_admin": es_administrador(u),
        "es_cliente": es_cliente(u),
        # getattr devuelve None si el usuario no tiene proveedor asociado.
        "proveedor_usuario": getattr(u, "proveedor", None),
    }
