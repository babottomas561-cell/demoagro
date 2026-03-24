"""
Analytics Service - proyecciones, desvíos, anomalías, sensibilidad.
"""
from typing import Optional
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lote import Lote
from app.models.cosecha_v2 import CosechaV2
from app.models.siembra import Siembra
from app.models.cultivo import Cultivo
from app.models.establecimiento import Establecimiento
from app.models.campania import Campania
from app.models.financiero import FlujoCajaV2, Presupuesto
from app.models.silo import StockActualV2
from app.services.campaign_scope import resolve_campaign_id


RENDIMIENTOS_HISTORICOS = {
    "Soja":    3.5,
    "Maiz":    9.5,
    "Trigo":   4.0,
    "Girasol": 2.4,
    "Sorgo":   7.5,
}

PRECIOS_REF_USD = {
    "Soja":    270,
    "Maiz":    160,
    "Trigo":   200,
    "Girasol": 340,
    "Sorgo":   115,
}


async def get_proyecciones(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
):
    resolved_camp = await resolve_campaign_id(db=db, campania_id=campania_id)

    # Obtener siembras activas (no cosechadas aún)
    q_siembras = (
        select(Siembra, Lote, Cultivo, Establecimiento, Campania)
        .join(Lote, Siembra.lote_id == Lote.id)
        .join(Cultivo, Siembra.cultivo_id == Cultivo.id)
        .join(Establecimiento, Lote.establecimiento_id == Establecimiento.id)
        .join(Campania, Siembra.campania_id == Campania.id)
        .where(Lote.estado == "sembrado")
    )
    if resolved_camp:
        q_siembras = q_siembras.where(Siembra.campania_id == resolved_camp)
    if empresa_id:
        q_siembras = q_siembras.where(Establecimiento.empresa_id == empresa_id)

    siembras_rows = (await db.execute(q_siembras)).all()

    # Cosechas ya realizadas
    q_cosechas = (
        select(CosechaV2, Siembra, Cultivo, Establecimiento)
        .join(Siembra, CosechaV2.siembra_id == Siembra.id)
        .join(Lote, Siembra.lote_id == Lote.id)
        .join(Cultivo, Siembra.cultivo_id == Cultivo.id)
        .join(Establecimiento, Lote.establecimiento_id == Establecimiento.id)
    )
    if resolved_camp:
        q_cosechas = q_cosechas.where(Siembra.campania_id == resolved_camp)
    if empresa_id:
        q_cosechas = q_cosechas.where(Establecimiento.empresa_id == empresa_id)

    cosechas_rows = (await db.execute(q_cosechas)).all()

    # Proyección por cultivo
    proyeccion_por_cultivo = defaultdict(lambda: {
        "ha_sembradas": 0.0,
        "ha_cosechadas": 0.0,
        "produccion_real_tn": 0.0,
        "produccion_proyectada_tn": 0.0,
        "ingreso_proyectado_usd": 0.0,
        "ingreso_proyectado_ars": 0.0,
    })

    for s, l, cult, est, camp in siembras_rows:
        d = proyeccion_por_cultivo[cult.nombre]
        d["ha_sembradas"] += s.ha_sembradas or 0
        rend_hist = RENDIMIENTOS_HISTORICOS.get(cult.nombre, 3.5)
        precio_usd = PRECIOS_REF_USD.get(cult.nombre, 250)
        proy_tn = (s.ha_sembradas or 0) * rend_hist
        d["produccion_proyectada_tn"] += proy_tn
        d["ingreso_proyectado_usd"] += proy_tn * precio_usd

    for c, s, cult, est in cosechas_rows:
        d = proyeccion_por_cultivo[cult.nombre]
        d["ha_cosechadas"] += c.ha_cosechadas or 0
        d["produccion_real_tn"] += (c.ha_cosechadas or 0) * (c.rendimiento_tn_ha or 0)

    tc_actual = 1050.0
    proyeccion_cultivos = []
    total_ingreso_proyectado_usd = 0
    total_produccion_proyectada = 0

    for cult_nombre, d in sorted(proyeccion_por_cultivo.items()):
        d["ingreso_proyectado_ars"] = round(d["ingreso_proyectado_usd"] * tc_actual, 2)
        d["ingreso_proyectado_usd"] = round(d["ingreso_proyectado_usd"], 2)
        d["produccion_proyectada_tn"] = round(d["produccion_proyectada_tn"], 2)
        d["produccion_real_tn"] = round(d["produccion_real_tn"], 2)
        d["ha_sembradas"] = round(d["ha_sembradas"], 2)
        d["ha_cosechadas"] = round(d["ha_cosechadas"], 2)
        total_ingreso_proyectado_usd += d["ingreso_proyectado_usd"]
        total_produccion_proyectada += d["produccion_proyectada_tn"]
        proyeccion_cultivos.append({"cultivo": cult_nombre, **d})

    # Stock final proyectado
    stock_actual_q = select(StockActualV2, Cultivo).join(Cultivo, StockActualV2.cultivo_id == Cultivo.id)
    if empresa_id:
        stock_actual_q = stock_actual_q.join(
            Establecimiento, StockActualV2.establecimiento_id == Establecimiento.id
        ).where(Establecimiento.empresa_id == empresa_id)
    stock_rows = (await db.execute(stock_actual_q)).all()

    stock_final = defaultdict(float)
    for st, cult in stock_rows:
        stock_final[cult.nombre] += (st.tn_disponibles or 0) - (st.tn_comprometidas or 0)

    stock_proyectado = [
        {
            "cultivo": k,
            "stock_neto_tn": round(v, 2),
            "valor_usd": round(v * PRECIOS_REF_USD.get(k, 250), 2),
        }
        for k, v in stock_final.items() if v > 0
    ]

    return {
        "campania_id": resolved_camp,
        "proyeccion_por_cultivo": proyeccion_cultivos,
        "totales": {
            "produccion_proyectada_tn": round(total_produccion_proyectada, 2),
            "ingreso_proyectado_usd": round(total_ingreso_proyectado_usd, 2),
            "ingreso_proyectado_ars": round(total_ingreso_proyectado_usd * tc_actual, 2),
        },
        "stock_final_proyectado": stock_proyectado,
    }


async def get_desvios(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
):
    resolved_camp = await resolve_campaign_id(db=db, campania_id=campania_id)

    # Desvío de rendimiento vs histórico
    q_cosechas = (
        select(CosechaV2, Siembra, Cultivo, Lote, Establecimiento)
        .join(Siembra, CosechaV2.siembra_id == Siembra.id)
        .join(Lote, Siembra.lote_id == Lote.id)
        .join(Cultivo, Siembra.cultivo_id == Cultivo.id)
        .join(Establecimiento, Lote.establecimiento_id == Establecimiento.id)
    )
    if resolved_camp:
        q_cosechas = q_cosechas.where(Siembra.campania_id == resolved_camp)
    if empresa_id:
        q_cosechas = q_cosechas.where(Establecimiento.empresa_id == empresa_id)

    cosechas_rows = (await db.execute(q_cosechas)).all()

    desvios_rend = []
    for c, s, cult, l, est in cosechas_rows:
        rend_hist = RENDIMIENTOS_HISTORICOS.get(cult.nombre, 3.5)
        rend_real = c.rendimiento_tn_ha or 0
        desvio_pct = round(((rend_real - rend_hist) / rend_hist) * 100, 1) if rend_hist else 0
        desvios_rend.append({
            "lote": l.nombre,
            "establecimiento": est.nombre,
            "cultivo": cult.nombre,
            "rendimiento_real": rend_real,
            "rendimiento_historico": rend_hist,
            "desvio_pct": desvio_pct,
            "status": "sobre" if desvio_pct >= 0 else "bajo",
        })

    desvios_rend.sort(key=lambda x: abs(x["desvio_pct"]), reverse=True)

    # Desvío de costos vs presupuesto
    pres_q = select(Presupuesto)
    if empresa_id:
        pres_q = pres_q.where(Presupuesto.empresa_id == empresa_id)
    if resolved_camp:
        pres_q = pres_q.where(Presupuesto.campania_id == resolved_camp)

    presupuestos = (await db.execute(pres_q)).scalars().all()

    desvios_costos = []
    for p in presupuestos:
        if p.importe_presupuestado and p.importe_presupuestado > 0:
            desvio_pct = round(
                ((p.importe_ejecutado - p.importe_presupuestado) / p.importe_presupuestado) * 100,
                1,
            )
            desvios_costos.append({
                "categoria": p.categoria,
                "presupuestado_ars": p.importe_presupuestado,
                "ejecutado_ars": p.importe_ejecutado,
                "desvio_pct": desvio_pct,
                "status": "sobre" if desvio_pct > 0 else "bajo",
            })

    desvios_costos.sort(key=lambda x: abs(x["desvio_pct"]), reverse=True)

    return {
        "desvios_rendimiento": desvios_rend[:20],
        "desvios_costos": desvios_costos,
        "resumen": {
            "lotes_sobre_historico": len([d for d in desvios_rend if d["desvio_pct"] >= 0]),
            "lotes_bajo_historico": len([d for d in desvios_rend if d["desvio_pct"] < 0]),
            "desvio_rend_promedio_pct": round(
                sum(d["desvio_pct"] for d in desvios_rend) / len(desvios_rend), 1
            ) if desvios_rend else 0,
            "categorias_sobre_presupuesto": len([d for d in desvios_costos if d["desvio_pct"] > 0]),
        },
    }


async def get_anomalias(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
):
    # Anomalías en rendimientos (outliers: +/- 2 std dev)
    q_cosechas = (
        select(CosechaV2, Siembra, Cultivo, Lote, Establecimiento)
        .join(Siembra, CosechaV2.siembra_id == Siembra.id)
        .join(Lote, Siembra.lote_id == Lote.id)
        .join(Cultivo, Siembra.cultivo_id == Cultivo.id)
        .join(Establecimiento, Lote.establecimiento_id == Establecimiento.id)
    )
    if empresa_id:
        q_cosechas = q_cosechas.where(Establecimiento.empresa_id == empresa_id)

    cosechas_rows = (await db.execute(q_cosechas)).all()

    # Agrupar por cultivo y detectar outliers
    rendimientos_by_cult = defaultdict(list)
    for c, s, cult, l, est in cosechas_rows:
        rendimientos_by_cult[cult.nombre].append({
            "rend": c.rendimiento_tn_ha or 0,
            "lote": l.nombre,
            "establecimiento": est.nombre,
            "cosecha_id": c.id,
        })

    anomalias_rend = []
    for cult_nombre, rends in rendimientos_by_cult.items():
        if len(rends) < 3:
            continue
        vals = [r["rend"] for r in rends]
        avg = sum(vals) / len(vals)
        variance = sum((v - avg) ** 2 for v in vals) / len(vals)
        std = variance ** 0.5
        for r in rends:
            zscore = abs(r["rend"] - avg) / std if std > 0 else 0
            if zscore > 1.8:
                anomalias_rend.append({
                    "tipo": "rendimiento_anomalo",
                    "cultivo": cult_nombre,
                    "lote": r["lote"],
                    "establecimiento": r["establecimiento"],
                    "valor": r["rend"],
                    "promedio_cultivo": round(avg, 2),
                    "zscore": round(zscore, 2),
                    "direccion": "alto" if r["rend"] > avg else "bajo",
                    "severidad": "alta" if zscore > 2.5 else "media",
                })

    anomalias_rend.sort(key=lambda x: x["zscore"], reverse=True)

    # Anomalías en costos (flujo de caja inusual)
    flujos_q = select(FlujoCajaV2)
    if empresa_id:
        flujos_q = flujos_q.where(FlujoCajaV2.empresa_id == empresa_id)
    flujos = (await db.execute(flujos_q)).scalars().all()

    gastos_by_cat = defaultdict(list)
    for f in flujos:
        if f.tipo == "egreso":
            gastos_by_cat[f.categoria].append(f.importe_ars or 0)

    anomalias_costos = []
    for cat, gastos in gastos_by_cat.items():
        if len(gastos) < 5:
            continue
        avg = sum(gastos) / len(gastos)
        variance = sum((g - avg) ** 2 for g in gastos) / len(gastos)
        std = variance ** 0.5
        for g in gastos:
            zscore = abs(g - avg) / std if std > 0 else 0
            if zscore > 2.0 and g > avg:
                anomalias_costos.append({
                    "tipo": "costo_inusual",
                    "categoria": cat,
                    "importe_ars": g,
                    "promedio_categoria_ars": round(avg, 2),
                    "zscore": round(zscore, 2),
                    "severidad": "alta" if zscore > 2.5 else "media",
                })

    anomalias_costos.sort(key=lambda x: x["zscore"], reverse=True)

    return {
        "anomalias_rendimiento": anomalias_rend[:15],
        "anomalias_costos": anomalias_costos[:10],
        "resumen": {
            "total_anomalias_rendimiento": len(anomalias_rend),
            "total_anomalias_costos": len(anomalias_costos),
            "anomalias_alta_severidad": len([a for a in anomalias_rend + anomalias_costos if a["severidad"] == "alta"]),
        },
    }


async def get_sensibilidad(
    db: AsyncSession,
    cultivo: str = "Soja",
    precio_base: float = 270.0,
    costo_base: float = 580.0,
):
    """Tabla de márgenes para distintos precios y rendimientos."""
    precios_usd = [
        precio_base * 0.80,
        precio_base * 0.90,
        precio_base,
        precio_base * 1.10,
        precio_base * 1.20,
    ]
    rendimientos = [
        RENDIMIENTOS_HISTORICOS.get(cultivo, 3.5) * 0.80,
        RENDIMIENTOS_HISTORICOS.get(cultivo, 3.5) * 0.90,
        RENDIMIENTOS_HISTORICOS.get(cultivo, 3.5),
        RENDIMIENTOS_HISTORICOS.get(cultivo, 3.5) * 1.10,
        RENDIMIENTOS_HISTORICOS.get(cultivo, 3.5) * 1.20,
    ]

    tabla = []
    for rend in rendimientos:
        fila = {"rendimiento_tn_ha": round(rend, 2), "margenes": []}
        for precio in precios_usd:
            ingreso = precio * rend
            margen_usd_ha = round(ingreso - costo_base, 2)
            margen_pct = round((margen_usd_ha / ingreso) * 100, 1) if ingreso > 0 else 0
            fila["margenes"].append({
                "precio_usd_tn": round(precio, 2),
                "ingreso_usd_ha": round(ingreso, 2),
                "margen_usd_ha": margen_usd_ha,
                "margen_pct": margen_pct,
                "viable": margen_pct > 0,
            })
        tabla.append(fila)

    return {
        "cultivo": cultivo,
        "precio_base_usd_tn": precio_base,
        "costo_base_usd_ha": costo_base,
        "precios_analizados": [round(p, 2) for p in precios_usd],
        "rendimientos_analizados": [round(r, 2) for r in rendimientos],
        "tabla_sensibilidad": tabla,
        "punto_equilibrio": {
            "rendimiento_para_cubrir_costos_tn_ha": round(costo_base / precio_base, 2) if precio_base > 0 else 0,
            "precio_para_cubrir_costos_usd_tn": round(
                costo_base / RENDIMIENTOS_HISTORICOS.get(cultivo, 3.5), 2
            ),
        },
    }
