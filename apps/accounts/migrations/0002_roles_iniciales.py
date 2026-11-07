"""Crea los dos roles del sistema como grupos de Django.
Los usuarios sin cuenta (anónimos) no necesitan rol."""
from django.db import migrations

ROLES = ["Administrador", "Cliente"]


def crear_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nombre in ROLES:
        Group.objects.get_or_create(name=nombre)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]
    operations = [migrations.RunPython(crear_roles, migrations.RunPython.noop)]
