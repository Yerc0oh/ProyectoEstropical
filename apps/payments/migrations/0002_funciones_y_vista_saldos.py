"""Funciones y vista del schema.sql para el Sprint 4 (copiadas tal cual de docs/estropical_schema.sql).

  * fn_penalidad_cancelacion(reserva_id) -> % aplicado, penalidad y monto reembolsable (CU-21)
  * fn_cerrar_caja(fecha, perfil_id)     -> consolida ingresos/egresos del día (CU-37)
  * v_saldo_reserva                      -> estado de cuenta y cuentas por cobrar (CU-29, CU-35)

(v_reporte_ventas es del Sprint 5.)
"""
from django.db import migrations

FN_PENALIDAD = r"""
CREATE OR REPLACE FUNCTION fn_penalidad_cancelacion(p_reserva_id BIGINT)
RETURNS TABLE (porcentaje NUMERIC, penalidad NUMERIC, reembolsable NUMERIC) AS $$
DECLARE
    v_dias    INTEGER;
    v_total   NUMERIC;
    v_pagado  NUMERIC;
    v_pct     NUMERIC;
BEGIN
    SELECT (p.fecha_salida - CURRENT_DATE), r.total
      INTO v_dias, v_total
      FROM reserva r JOIN paquete p ON p.id = r.paquete_id
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
$$ LANGUAGE plpgsql STABLE;
"""

FN_CERRAR_CAJA = r"""
CREATE OR REPLACE FUNCTION fn_cerrar_caja(p_fecha DATE, p_perfil_id BIGINT)
RETURNS BIGINT AS $$
DECLARE
    v_ingresos NUMERIC(12,2);
    v_egresos  NUMERIC(12,2);
    v_cierre   BIGINT;
    v_tz CONSTANT TEXT := 'America/La_Paz';
BEGIN
    SELECT COALESCE(SUM(monto), 0) INTO v_ingresos
      FROM pago
     WHERE estado = 'completado' AND cierre_caja_id IS NULL
       AND (fecha_pago AT TIME ZONE v_tz)::DATE = p_fecha;

    SELECT COALESCE((SELECT SUM(monto_reembolso) FROM reembolso
                      WHERE estado = 'procesado' AND cierre_caja_id IS NULL
                        AND (fecha_procesado AT TIME ZONE v_tz)::DATE = p_fecha), 0)
         + COALESCE((SELECT SUM(monto) FROM pago_proveedor
                      WHERE estado = 'pagado' AND cierre_caja_id IS NULL
                        AND (fecha_pago AT TIME ZONE v_tz)::DATE = p_fecha), 0)
      INTO v_egresos;

    INSERT INTO cierre_caja (fecha, total_ingresos, total_egresos, realizado_por_id)
    VALUES (p_fecha, v_ingresos, v_egresos, p_perfil_id)
    RETURNING id INTO v_cierre;           -- falla si ya hay cierre de esa fecha (UNIQUE)

    UPDATE pago SET cierre_caja_id = v_cierre
     WHERE estado = 'completado' AND cierre_caja_id IS NULL
       AND (fecha_pago AT TIME ZONE v_tz)::DATE = p_fecha;
    UPDATE reembolso SET cierre_caja_id = v_cierre
     WHERE estado = 'procesado' AND cierre_caja_id IS NULL
       AND (fecha_procesado AT TIME ZONE v_tz)::DATE = p_fecha;
    UPDATE pago_proveedor SET cierre_caja_id = v_cierre
     WHERE estado = 'pagado' AND cierre_caja_id IS NULL
       AND (fecha_pago AT TIME ZONE v_tz)::DATE = p_fecha;

    RETURN v_cierre;
END;
$$ LANGUAGE plpgsql;
"""

V_SALDO_RESERVA = r"""
CREATE OR REPLACE VIEW v_saldo_reserva AS
SELECT r.id AS reserva_id,
       r.codigo,
       r.cliente_id,
       r.estado,
       r.total,
       COALESCE(pg.pagado, 0)     AS pagado,
       COALESCE(rb.reembolsado, 0) AS reembolsado,
       CASE WHEN r.estado IN ('cancelada','expirada') THEN 0
            ELSE r.total - COALESCE(pg.pagado, 0) END AS saldo_pendiente,
       COALESCE(cu.vencidas, 0)   AS cuotas_vencidas
  FROM reserva r
  LEFT JOIN (SELECT reserva_id, SUM(monto) AS pagado
               FROM pago WHERE estado = 'completado' GROUP BY reserva_id) pg
         ON pg.reserva_id = r.id
  LEFT JOIN (SELECT reserva_id, SUM(monto_reembolso) AS reembolsado
               FROM reembolso WHERE estado = 'procesado' GROUP BY reserva_id) rb
         ON rb.reserva_id = r.id
  LEFT JOIN (SELECT reserva_id, COUNT(*) AS vencidas
               FROM cuota WHERE estado = 'pendiente' AND fecha_vencimiento < CURRENT_DATE
              GROUP BY reserva_id) cu
         ON cu.reserva_id = r.id;
"""


# Cada sentencia va por separado: Django no debe partir el SQL (los $$ de PL/pgSQL).
REVERSA = [
    "DROP VIEW IF EXISTS v_saldo_reserva",
    "DROP FUNCTION IF EXISTS fn_cerrar_caja(DATE, BIGINT)",
    "DROP FUNCTION IF EXISTS fn_penalidad_cancelacion(BIGINT)",
]


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
        ("reservations", "0002_parametros_y_trigger_cupos"),
    ]
    operations = [migrations.RunSQL([FN_PENALIDAD, FN_CERRAR_CAJA, V_SALDO_RESERVA], REVERSA)]
