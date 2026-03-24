"""
Adaptador SQL para conectar con un ERP real.

═══════════════════════════════════════════════════════════════
INSTRUCCIONES DE USO
═══════════════════════════════════════════════════════════════

1. Copiá este archivo y renombralo según tu ERP:
   - sielro_adapter.py
   - totvs_adapter.py
   - agroerp_adapter.py

2. En cada query, reemplazá:
   - el esquema/prefijo  (ej: "erp." → "sielro_prod.")
   - el nombre de tabla  (ej: "ordenes_cosecha" → tu tabla real)
   - el nombre de columna en el SELECT AS (el alias DEBE mantenerse igual)

3. Conectá la base del ERP en DATABASE_URL del .env:
   DATABASE_URL=postgresql+asyncpg://user:pass@erp-server:5432/erp_db

4. Listo. No hay que tocar ningún otro archivo.

═══════════════════════════════════════════════════════════════
COLUMNAS REQUERIDAS POR PANEL
═══════════════════════════════════════════════════════════════

Cada query retorna exactamente las columnas que el servicio espera.
Si tu ERP no tiene una columna, usá un literal: 0 AS jornales
"""

# ─────────────────────────────────────────────────────────────
# PRODUCCION DE CAMPO
# ─────────────────────────────────────────────────────────────

COSECHA = """
    SELECT
        h.id                        AS cosecha_id,
        lc.lote_campania_id,
        h.fecha_cosecha             AS fecha_cosecha,
        h.kg_netos                  AS kg_cosechados,
        h.cant_jornales             AS jornales,
        h.cant_cuadrillas           AS cuadrillas,
        h.bins_cosechados           AS bins_cosechados,
        h.costo_labor_ars           AS costo_cosecha_ars,
        0.0                         AS fruta_danada_pct
    FROM erp.ordenes_cosecha h
    JOIN erp.lote_campania lc ON lc.lote_id = h.lote_id
                              AND lc.campania_id = :campania_id
    WHERE lc.lote_campania_id = ANY(:ids)
      AND h.fecha_cosecha BETWEEN :desde AND :hasta
    ORDER BY h.fecha_cosecha
"""

RENDIMIENTO_LOTE = """
    SELECT
        rl.id                       AS rendimiento_lote_id,
        lc.lote_campania_id,
        rl.kg_totales,
        rl.kg_totales / NULLIF(lc.superficie_ha, 0) AS kg_ha,
        rl.pct_exportable           AS fruta_exportable_pct,
        rl.pct_industria            AS fruta_industria_pct,
        rl.pct_descarte             AS fruta_descarte_pct,
        NULL                        AS semana_pico,
        0.0                         AS desvio_vs_objetivo_pct
    FROM erp.rendimiento_lote rl
    JOIN erp.lote_campania lc ON lc.lote_id = rl.lote_id
                              AND lc.campania_id = :campania_id
    WHERE lc.lote_campania_id = ANY(:ids)
"""

# ─────────────────────────────────────────────────────────────
# CALIDAD DE FRUTA
# ─────────────────────────────────────────────────────────────

RECEPCION_FRUTA = """
    SELECT
        r.id                        AS recepcion_id,
        lc.lote_campania_id,
        r.fecha_recepcion,
        r.kg_ingresados             AS kg_recibidos,
        r.fecha_recepcion           AS fecha_id
    FROM erp.recepciones_fruta r
    JOIN erp.lote_campania lc ON lc.lote_id = r.lote_id
                              AND lc.campania_id = :campania_id
    WHERE lc.lote_campania_id = ANY(:ids)
      AND r.fecha_recepcion BETWEEN :desde AND :hasta
    ORDER BY r.fecha_recepcion
"""

PACKOUT = """
    SELECT
        p.id                        AS packout_id,
        lc.lote_campania_id,
        p.fecha_clasificacion       AS fecha_packout,
        p.pct_exportable            AS packout_pct,
        p.pct_rechazo               AS rechazo_pct,
        p.pct_descarte              AS descarte_pct,
        p.pct_industria             AS industria_pct
    FROM erp.packout_diario p
    JOIN erp.lote_campania lc ON lc.lote_id = p.lote_id
                              AND lc.campania_id = :campania_id
    WHERE lc.lote_campania_id = ANY(:ids)
      AND p.fecha_clasificacion BETWEEN :desde AND :hasta
    ORDER BY p.fecha_clasificacion
"""

DEFECTOS = """
    SELECT
        d.tipo_defecto              AS defecto,
        d.categoria                 AS categoria,
        SUM(d.kg_rechazados)        AS kg_rechazo,
        SUM(d.kg_rechazados) / NULLIF(SUM(SUM(d.kg_rechazados)) OVER (), 0) * 100
                                    AS participacion_pct
    FROM erp.clasificacion_defectos d
    JOIN erp.lote_campania lc ON lc.lote_id = d.lote_id
                              AND lc.campania_id = :campania_id
    WHERE lc.lote_campania_id = ANY(:ids)
      AND d.fecha BETWEEN :desde AND :hasta
    GROUP BY d.tipo_defecto, d.categoria
    ORDER BY kg_rechazo DESC
"""

# ─────────────────────────────────────────────────────────────
# PACKHOUSE
# ─────────────────────────────────────────────────────────────

TURNO_PRODUCCION = """
    SELECT
        t.id                        AS turno_produccion_id,
        t.linea_id,
        t.fecha_turno               AS fecha,
        t.kg_procesados / 1000.0    AS kg_procesados_tn,
        t.horas_operativas          AS horas_productivas,
        t.horas_paradas             AS horas_downtime,
        t.horas_paradas / NULLIF(t.horas_operativas + t.horas_paradas, 0) * 100
                                    AS downtime_pct,
        t.eficiencia_pct,
        t.costo_total_ars,
        t.turno_id
    FROM erp.turnos_packhouse t
    WHERE t.fecha_turno BETWEEN :desde AND :hasta
      AND (:linea_id IS NULL OR t.linea_id = :linea_id)
    ORDER BY t.fecha_turno
"""

DOWNTIME_MOTIVOS = """
    SELECT
        m.motivo,
        SUM(m.minutos_parada)       AS minutos
    FROM erp.paradas_packhouse m
    WHERE m.fecha BETWEEN :desde AND :hasta
    GROUP BY m.motivo
    ORDER BY minutos DESC
"""

# ─────────────────────────────────────────────────────────────
# SANIDAD Y MONITOREO
# ─────────────────────────────────────────────────────────────

SCOUTING = """
    SELECT
        s.id                        AS scouting_id,
        lc.lote_campania_id,
        s.fecha_scouting            AS fecha_evento,
        s.plaga_id,
        s.enfermedad_id,
        s.severidad,
        s.pct_incidencia            AS incidencia_pct,
        s.pct_lotes_afectados       AS lotes_afectados_pct,
        s.es_alerta                 AS alerta,
        s.observaciones             AS notas
    FROM erp.scouting_eventos s
    JOIN erp.lote_campania lc ON lc.lote_id = s.lote_id
                              AND lc.campania_id = :campania_id
    WHERE lc.lote_campania_id = ANY(:ids)
      AND s.fecha_scouting BETWEEN :desde AND :hasta
    ORDER BY s.fecha_scouting
"""

APLICACION_FITOSANITARIA = """
    SELECT
        a.id                        AS aplicacion_id,
        lc.lote_campania_id,
        a.fecha_aplicacion,
        a.producto_nombre           AS producto,
        a.objetivo_tratamiento      AS objetivo,
        a.dosis_l_ha                AS dosis_litros_ha,
        a.costo_ars_ha              AS costo_ars_ha,
        a.contiene_cobre            AS es_cobre
    FROM erp.aplicaciones_fitosanitarias a
    JOIN erp.lote_campania lc ON lc.lote_id = a.lote_id
                              AND lc.campania_id = :campania_id
    WHERE lc.lote_campania_id = ANY(:ids)
      AND a.fecha_aplicacion BETWEEN :desde AND :hasta
    ORDER BY a.fecha_aplicacion
"""

# ─────────────────────────────────────────────────────────────
# RIEGO Y FERTIRRIEGO
# ─────────────────────────────────────────────────────────────

RIEGO_EVENTOS = """
    SELECT
        r.id                        AS riego_id,
        lc.lote_campania_id,
        r.fecha_riego               AS fecha_evento,
        r.m3_aplicados,
        r.horas_riego,
        r.tipo_riego,
        r.es_fertirriego
    FROM erp.eventos_riego r
    JOIN erp.lote_campania lc ON lc.lote_id = r.lote_id
                              AND lc.campania_id = :campania_id
    WHERE lc.lote_campania_id = ANY(:ids)
      AND r.fecha_riego BETWEEN :desde AND :hasta
    ORDER BY r.fecha_riego
"""

REQUERIMIENTO_HIDRICO = """
    SELECT
        rh.id                       AS requerimiento_id,
        lc.lote_campania_id,
        rh.semana_inicio,
        rh.m3_requeridos_semana     AS m3_requeridos,
        rh.et0_mm,
        rh.kc
    FROM erp.requerimiento_hidrico rh
    JOIN erp.lote_campania lc ON lc.lote_id = rh.lote_id
                              AND lc.campania_id = :campania_id
    WHERE lc.lote_campania_id = ANY(:ids)
      AND rh.semana_inicio BETWEEN :desde AND :hasta
"""

# ─────────────────────────────────────────────────────────────
# COMERCIAL / EXPORTACION
# ─────────────────────────────────────────────────────────────

EMBARQUES = """
    SELECT
        e.id                        AS embarque_id,
        e.contrato_id               AS contrato_venta_id,
        e.fecha_embarque,
        e.cliente_id,
        e.mercado_id,
        e.canal_id,
        e.kg_embarcados,
        e.cant_cajas                AS cajas,
        e.precio_usd_tn             AS precio_realizado_usd_tn,
        e.estado_logistico,
        e.estado_cobro
    FROM erp.embarques_exportacion e
    WHERE e.fecha_embarque BETWEEN :desde AND :hasta
      AND (:campania_id IS NULL OR e.campania_id = :campania_id)
      AND (:cliente_id IS NULL OR e.cliente_id = :cliente_id)
      AND (:mercado_id IS NULL OR e.mercado_id = :mercado_id)
    ORDER BY e.fecha_embarque DESC
"""

CONTRATOS_VENTA = """
    SELECT
        c.id                        AS contrato_venta_id,
        c.campania_id,
        c.cliente_id,
        c.mercado_id,
        c.canal_id,
        c.fecha_contrato,
        c.estado,
        c.kg_contratados,
        c.kg_entregados,
        c.kg_contratados - c.kg_entregados AS kg_pendientes,
        c.precio_objetivo_usd_tn,
        c.moneda,
        c.condicion_pago_dias
    FROM erp.contratos_venta c
    WHERE c.campania_id = :campania_id
      AND (:cliente_id IS NULL OR c.cliente_id = :cliente_id)
"""

COBRANZAS = """
    SELECT
        co.id                       AS cobranza_id,
        co.cliente_id,
        co.fecha_emision,
        co.fecha_cobro,
        co.importe_ars              AS monto_ars,
        co.importe_usd              AS monto_usd,
        co.estado,
        co.dias_cobro
    FROM erp.cobranzas co
    WHERE co.campania_id = :campania_id
      AND co.fecha_emision BETWEEN :desde AND :hasta
    ORDER BY co.fecha_emision DESC
"""

# ─────────────────────────────────────────────────────────────
# GERENCIA GENERAL (datos financieros consolidados)
# ─────────────────────────────────────────────────────────────

INGRESOS_COSTOS_DIARIO = """
    SELECT
        f.fecha,
        SUM(f.ingresos_ars)         AS ingresos_ars,
        SUM(f.costos_ars)           AS costos_ars,
        SUM(f.ingresos_ars) - SUM(f.costos_ars) AS margen_ars
    FROM erp.flujo_diario f
    WHERE f.campania_id = :campania_id
      AND f.fecha BETWEEN :desde AND :hasta
    GROUP BY f.fecha
    ORDER BY f.fecha
"""

COSTOS_CATEGORIA = """
    SELECT
        c.categoria,
        SUM(c.monto_ars)            AS monto_ars,
        SUM(c.monto_ars) / NULLIF(SUM(SUM(c.monto_ars)) OVER (), 0) * 100
                                    AS participacion_pct
    FROM erp.costos_operativos c
    WHERE c.campania_id = :campania_id
      AND c.fecha BETWEEN :desde AND :hasta
    GROUP BY c.categoria
    ORDER BY monto_ars DESC
"""

# ─────────────────────────────────────────────────────────────
# MACRO / MERCADO (tipo de cambio — fuente interna del ERP)
# Nota: BCRA/USDA se consultan vía API externa, no por aquí.
# ─────────────────────────────────────────────────────────────

TIPO_CAMBIO = """
    SELECT
        tc.fecha,
        tc.tc_exportacion,
        tc.tc_mayorista,
        tc.tc_oficial
    FROM erp.tipos_de_cambio tc
    WHERE tc.fecha BETWEEN :desde AND :hasta
    ORDER BY tc.fecha
"""
