"""Datos iniciales de parametro_sistema y el trigger trg_reserva_cupos del schema.sql.

El trigger evita la sobreventa: cuando una reserva pasa a estado activo (pendiente/
confirmada) descuenta cupos del paquete y asientos de sus vuelos; al cancelar, expirar o
cambiar la cantidad de pasajeros devuelve o ajusta la diferencia. Si no alcanza, el CHECK
de paquete/vuelo (ck_paquete_cupos / ck_vuelo_asientos) hace fallar la operación.
"""
from django.db import migrations

PARAMETROS = [
    ("penalidad_30_dias_o_mas", "10", "% de penalidad si faltan 30 dias o mas para la salida"),
    ("penalidad_15_a_29_dias", "30", "% de penalidad si faltan de 15 a 29 dias"),
    ("penalidad_7_a_14_dias", "50", "% de penalidad si faltan de 7 a 14 dias"),
    ("penalidad_menos_7_dias", "100", "% de penalidad si faltan menos de 7 dias"),
    ("horas_expiracion_reserva", "24", "Horas para pagar antes de que la reserva expire"),
    ("cuotas_maximas", "6", "Numero maximo de cuotas por reserva"),
]


def cargar_parametros(apps, schema_editor):
    ParametroSistema = apps.get_model("reservations", "ParametroSistema")
    for clave, valor, descripcion in PARAMETROS:
        ParametroSistema.objects.get_or_create(clave=clave, defaults={"valor": valor, "descripcion": descripcion})


FN_AJUSTAR_CUPOS = """
CREATE OR REPLACE FUNCTION fn_ajustar_cupos() RETURNS TRIGGER AS $$
DECLARE
    v_antes   INTEGER := 0;
    v_despues INTEGER := 0;
    v_delta   INTEGER;
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.estado IN ('pendiente','confirmada') THEN
        v_antes := OLD.cantidad_pasajeros;
    END IF;
    IF NEW.estado IN ('pendiente','confirmada') THEN
        v_despues := NEW.cantidad_pasajeros;
    END IF;

    v_delta := v_despues - v_antes;          -- >0 ocupa cupos, <0 libera
    IF v_delta <> 0 THEN
        UPDATE paquete
           SET cupos_disponibles = cupos_disponibles - v_delta
         WHERE id = NEW.paquete_id;

        UPDATE vuelo
           SET asientos_disponibles = asientos_disponibles - v_delta
         WHERE id IN (SELECT vuelo_id FROM paquete_vuelo WHERE paquete_id = NEW.paquete_id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
"""

TRG_RESERVA_CUPOS = """
CREATE TRIGGER trg_reserva_cupos
AFTER INSERT OR UPDATE OF estado, cantidad_pasajeros ON reserva
FOR EACH ROW EXECUTE FUNCTION fn_ajustar_cupos()
"""

# Cada sentencia va por separado: Django no debe partir el SQL (los $$ de PL/pgSQL).
REVERSA = [
    "DROP TRIGGER IF EXISTS trg_reserva_cupos ON reserva",
    "DROP FUNCTION IF EXISTS fn_ajustar_cupos()",
]


class Migration(migrations.Migration):
    dependencies = [
        ("reservations", "0001_initial"),
        ("flights", "0001_initial"),
        ("packages", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(cargar_parametros, migrations.RunPython.noop),
        migrations.RunSQL([FN_AJUSTAR_CUPOS, TRG_RESERVA_CUPOS], REVERSA),
    ]
