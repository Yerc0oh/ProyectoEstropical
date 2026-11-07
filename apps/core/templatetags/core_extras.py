from django import template

register = template.Library()


@register.filter
def valor_de(obj, ruta):
    """{{ obj|valor_de:"destino.nombre" }} - sigue atributos y llama métodos."""
    for parte in ruta.split("."):
        obj = getattr(obj, parte, "")
        if callable(obj):
            obj = obj()
    return "" if obj is None else obj
