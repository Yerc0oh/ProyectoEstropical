from django.db import migrations
import importlib


def corregir_cierre_caja(apps, schema_editor):
    modulo = importlib.import_module(
        "apps.payments.migrations.0002_funciones_y_vista_saldos"
    )

    sql = modulo.FN_CERRAR_CAJA

    # Añadir fecha_cierre si todavía no está incluida
    if "realizado_por_id, fecha_cierre" not in sql:
        sql = sql.replace(
            "realizado_por_id)",
            "realizado_por_id, fecha_cierre)"
        ).replace(
            "p_perfil_id)",
            "p_perfil_id, CURRENT_TIMESTAMP)"
        )

    # Añadir observaciones con una cadena vacía
    sql = sql.replace(
        "realizado_por_id, fecha_cierre)",
        "realizado_por_id, fecha_cierre, observaciones)"
    ).replace(
        "p_perfil_id, CURRENT_TIMESTAMP)",
        "p_perfil_id, CURRENT_TIMESTAMP, '')"
    )

    schema_editor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0002_funciones_y_vista_saldos"),
    ]

    operations = [
        migrations.RunPython(corregir_cierre_caja),
    ]