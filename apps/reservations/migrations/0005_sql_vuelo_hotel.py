"""Reservas de vuelo solo y hotel solo: actualiza el trigger de cupos y la función de penalidad.

- fn_ajustar_cupos: además de los paquetes, descuenta/devuelve asientos de un vuelo reservado solo.
- fn_penalidad_cancelacion: la fecha del viaje sale del paquete, del vuelo o de la entrada al hotel.
"""
from django.db import migrations

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
        IF NEW.paquete_id IS NOT NULL THEN   -- paquete: cupos del paquete y asientos de sus vuelos
            UPDATE paquete
               SET cupos_disponibles = cupos_disponibles - v_delta
             WHERE id = NEW.paquete_id;

            UPDATE vuelo
               SET asientos_disponibles = asientos_disponibles - v_delta
             WHERE id IN (SELECT vuelo_id FROM paquete_vuelo WHERE paquete_id = NEW.paquete_id);
        END IF;
        IF NEW.vuelo_id IS NOT NULL THEN     -- vuelo solo: asientos de ese vuelo
            UPDATE vuelo
               SET asientos_disponibles = asientos_disponibles - v_delta
             WHERE id = NEW.vuelo_id;
        END IF;
        -- hotel solo: las habitaciones las controla asignacion_habitacion (alojamiento.py)
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
"""

FN_PENALIDAD = r"""
CREATE OR REPLACE FUNCTION fn_penalidad_cancelacion(p_reserva_id BIGINT)
RETURNS TABLE (porcentaje NUMERIC, penalidad NUMERIC, reembolsable NUMERIC) AS $$
DECLARE
    v_dias    INTEGER;
    v_total   NUMERIC;
    v_pagado  NUMERIC;
    v_pct     NUMERIC;
BEGIN
    SELECT (COALESCE(p.fecha_salida,
                     (v.fecha_salida AT TIME ZONE 'America/La_Paz')::date,
                     r.fecha_inicio) - CURRENT_DATE),
           r.total
      INTO v_dias, v_total
      FROM reserva r
      LEFT JOIN paquete p ON p.id = r.paquete_id
      LEFT JOIN vuelo   v ON v.id = r.vuelo_id
     WHERE r.id = p_reserva_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Reserva % no existe', p_reserva_id;
    END IF;

    SELECT COALESCE(SUM(monto), 0) INTO v_pagado
      FROM pago WHERE reserva_id = p_reserva_id AND estado = 'completado';

    SELECT valor::NUMERIC INTO v_pct FROM parametro_sistema
     WHERE clave = CASE
                     WHEN v_dias >= 30 THEN 'penalidad_30_dias_o_mas'
                     WHEN v_dias >= 15 THEN 'penalidad_15_a_29_dias'
                     WHEN v_dias >= 7  THEN 'penalidad_7_a_14_dias'
                     ELSE 'penalidad_menos_7_dias'
                   END;

    porcentaje   := v_pct;
    penalidad    := LEAST(v_pagado, ROUND(v_total * v_pct / 100, 2));
    reembolsable := v_pagado - penalidad;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql STABLE
"""


class Migration(migrations.Migration):

    dependencies = [
        ("reservations", "0004_reserva_vuelo_hotel"),
        ("payments", "0002_funciones_y_vista_saldos"),
    ]

    operations = [
        migrations.RunSQL([FN_AJUSTAR_CUPOS, FN_PENALIDAD], migrations.RunSQL.noop),
    ]