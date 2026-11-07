from apps.core.access import es_administrador, es_cliente


def roles(request):
    """Disponibiliza es_admin / es_cliente en todas las plantillas."""
    u = request.user
    return {"es_admin": es_administrador(u), "es_cliente": es_cliente(u)}
