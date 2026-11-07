"""Datos mínimos para empezar. TODO: ampliar o reemplazar por fixtures propios."""
from django.db import migrations

PAISES = [("BO", "Bolivia"), ("PE", "Perú"), ("BR", "Brasil"), ("AR", "Argentina"),
          ("CL", "Chile"), ("US", "Estados Unidos"), ("ES", "España")]
CATEGORIAS = ["Playa", "Aventura", "Cultural", "Naturaleza", "Ciudad"]


def cargar(apps, schema_editor):
    Pais, Categoria = apps.get_model("destinations", "Pais"), apps.get_model("destinations", "Categoria")
    for iso, nombre in PAISES:
        Pais.objects.get_or_create(codigo_iso=iso, defaults={"nombre": nombre})
    for nombre in CATEGORIAS:
        Categoria.objects.get_or_create(nombre=nombre)


class Migration(migrations.Migration):
    dependencies = [("destinations", "0001_initial")]
    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
