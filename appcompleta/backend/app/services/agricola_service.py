from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime
import logging

from app.models.lote import Lote
from app.models.labor import Labor
from app.models.cultivo import Cultivo
from app.models.establecimiento import Establecimiento
from app.models.campania import Campania
from app.services.campaign_scope import resolve_campaign_id
from app.services.decision_data import (
    load_alert_rows,
    load_ambiente_rows,
    load_application_rows,
    load_observation_rows,
    load_plan_rows,
    load_recommendation_rows,
    load_task_rows,
)

logger = logging.getLogger(__name__)


async def get_agricola_resumen(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    cultivo_id: Optional[int] = None,
):
    resolved_campania_id = await resolve_campaign_id(db=db, campania_id=campania_id)

    # Base query with joins to get all related data
    base_q = select(Lote, Establecimiento, Cultivo).join(
        Establecimiento, Lote.establecimiento_id == Establecimiento.id
    ).outerjoin(Cultivo, Lote.cultivo_id == Cultivo.id)

    if empresa_id:
        base_q = base_q.where(Establecimiento.empresa_id == empresa_id)
    if resolved_campania_id:
        base_q = base_q.where(Lote.campania_id == resolved_campania_id)
    if establecimiento_id:
        base_q = base_q.where(Lote.establecimiento_id == establecimiento_id)
    if cultivo_id:
        base_q = base_q.where(Lote.cultivo_id == cultivo_id)

    result = await db.execute(base_q)
    rows = result.all()

    # Summary aggregations
    superficie_total = sum(l.hectareas for l, _, _ in rows)
    superficie_sembrada = sum(l.hectareas for l, _, _ in rows if l.estado in ("sembrado", "cosechado"))
    superficie_cosechada = sum(l.hectareas for l, _, _ in rows if l.estado == "cosechado")

    lotes_con_rend = [(l, e, c) for l, e, c in rows if l.rendimiento_real is not None]
    rendimiento_promedio = (
        sum(l.rendimiento_real for l, _, _ in lotes_con_rend) / len(lotes_con_rend)
        if lotes_con_rend else 0
    )
    rendimiento_variabilidad = 0.0
    if lotes_con_rend:
        rend_values = [l.rendimiento_real for l, _, _ in lotes_con_rend]
        avg_sq = sum(value * value for value in rend_values) / len(rend_values)
        variance = max(avg_sq - (rendimiento_promedio * rendimiento_promedio), 0)
        std_dev = variance ** 0.5
        rendimiento_variabilidad = (
            (std_dev / rendimiento_promedio) * 100 if rendimiento_promedio else 0
        )

    # Costo promedio por ha from labores
    lote_ids = [l.id for l, _, _ in rows]
    if lote_ids:
        costos_q = select(func.avg(Labor.costo_ha)).where(Labor.lote_id.in_(lote_ids))
        costo_result = await db.execute(costos_q)
        costo_promedio_ha = costo_result.scalar() or 0
    else:
        costo_promedio_ha = 0

    # Avance by cultivo: sembrado_ha vs total_ha
    cultivo_stats: dict = {}
    for lote, _, cultivo in rows:
        nombre = cultivo.nombre if cultivo else "Sin cultivo"
        if nombre not in cultivo_stats:
            cultivo_stats[nombre] = {"total_ha": 0.0, "sembrado_ha": 0.0}
        cultivo_stats[nombre]["total_ha"] += lote.hectareas
        if lote.estado in ("sembrado", "cosechado"):
            cultivo_stats[nombre]["sembrado_ha"] += lote.hectareas

    avance_cultivos = [
        {
            "cultivo": nombre,
            "sembrado_ha": round(vals["sembrado_ha"], 2),
            "total_ha": round(vals["total_ha"], 2),
            "porcentaje": round(
                vals["sembrado_ha"] / vals["total_ha"] * 100 if vals["total_ha"] > 0 else 0, 1
            ),
        }
        for nombre, vals in sorted(cultivo_stats.items(), key=lambda x: -x[1]["total_ha"])
    ]

    # Lotes list with frontend-compatible field names
    lotes_list = [
        {
            "id": str(lote.id),
            "nombre": lote.nombre,
            "establecimiento": est.nombre if est else "—",
            "cultivo": cultivo.nombre if cultivo else "—",
            "hectareas": lote.hectareas,
            "estado": lote.estado,
            "fecha_siembra": lote.fecha_siembra.isoformat() if lote.fecha_siembra else None,
            "rendimiento_tn_ha": lote.rendimiento_real,
            "costo_por_ha": round(costo_promedio_ha, 2),
        }
        for lote, est, cultivo in rows
    ]

    # Rendimiento historico por campania
    campanias_q = await db.execute(select(Campania).order_by(Campania.nombre))
    campanias = campanias_q.scalars().all()

    rendimiento_historico = []
    for camp in campanias:
        camp_q = select(Lote, Cultivo).outerjoin(
            Cultivo, Lote.cultivo_id == Cultivo.id
        ).where(Lote.campania_id == camp.id)

        if empresa_id:
            camp_q = camp_q.join(
                Establecimiento, Lote.establecimiento_id == Establecimiento.id
            ).where(Establecimiento.empresa_id == empresa_id)

        camp_result = await db.execute(camp_q)
        camp_rows = camp_result.all()

        rend_by_cultivo: dict = {}
        for lote, cultivo in camp_rows:
            if lote.rendimiento_real is not None and cultivo:
                key = cultivo.nombre.lower()
                rend_by_cultivo.setdefault(key, []).append(lote.rendimiento_real)

        if rend_by_cultivo:
            def avg(key):
                vals = rend_by_cultivo.get(key, [])
                return round(sum(vals) / len(vals), 2) if vals else None

            rendimiento_historico.append({
                "campania": camp.nombre,
                "soja": avg("soja"),
                "maiz": avg("maiz"),
                "trigo": avg("trigo"),
                "girasol": avg("girasol"),
            })

    plan_rows = await load_plan_rows(
        db=db,
        empresa_id=empresa_id,
        campania_id=resolved_campania_id,
        establecimiento_id=establecimiento_id,
        cultivo_id=cultivo_id,
    )
    observation_rows = await load_observation_rows(
        db=db,
        empresa_id=empresa_id,
        campania_id=resolved_campania_id,
        establecimiento_id=establecimiento_id,
        cultivo_id=cultivo_id,
    )
    recommendation_rows = await load_recommendation_rows(
        db=db,
        empresa_id=empresa_id,
        campania_id=resolved_campania_id,
        establecimiento_id=establecimiento_id,
        cultivo_id=cultivo_id,
    )
    application_rows = await load_application_rows(
        db=db,
        empresa_id=empresa_id,
        campania_id=resolved_campania_id,
        establecimiento_id=establecimiento_id,
        cultivo_id=cultivo_id,
    )
    ambiente_rows = await load_ambiente_rows(
        db=db,
        empresa_id=empresa_id,
        campania_id=resolved_campania_id,
        establecimiento_id=establecimiento_id,
        cultivo_id=cultivo_id,
    )
    alert_rows = await load_alert_rows(db=db, modules=("agricola",))
    task_rows = await load_task_rows(db=db, modules=("agricola",))

    plan_map: dict[int, dict] = {}
    plan_vs_actual_map: dict[str, dict[str, float]] = {}
    pendientes_establecimiento_map: dict[tuple[str, str], dict[str, float]] = {}
    productividad_map: dict[tuple[str, str], dict[str, float]] = {}
    lotes_atrasados = []
    hectareas_fuera_ventana = 0.0
    today = datetime.now().date()

    for plan, ejecucion, lote, est, cultivo in plan_rows:
        bucket = plan_map.setdefault(
            plan.id,
            {
                "plan": plan,
                "lote": lote,
                "establecimiento": est,
                "cultivo": cultivo,
                "ejecutado": 0.0,
                "horas": 0.0,
                "equipo": plan.equipo,
                "operador": plan.operador,
            },
        )
        if ejecucion:
            bucket["ejecutado"] += ejecucion.hectareas_ejecutadas or 0
            bucket["horas"] += ejecucion.horas_trabajadas or 0

            for tipo_recurso, nombre_recurso in (("equipo", ejecucion.equipo or plan.equipo), ("operador", ejecucion.operador or plan.operador)):
                if not nombre_recurso:
                    continue
                prod = productividad_map.setdefault(
                    (tipo_recurso, nombre_recurso),
                    {"recurso": nombre_recurso, "tipo": tipo_recurso, "hectareas": 0.0, "horas": 0.0},
                )
                prod["hectareas"] += ejecucion.hectareas_ejecutadas or 0
                prod["horas"] += ejecucion.horas_trabajadas or 0

    for bucket in plan_map.values():
        plan = bucket["plan"]
        pendiente = max(plan.hectareas_planificadas - bucket["ejecutado"], 0)
        labor = plan.tipo_labor
        metric = plan_vs_actual_map.setdefault(
            labor,
            {"labor": labor, "plan_ha": 0.0, "real_ha": 0.0, "pendiente_ha": 0.0},
        )
        metric["plan_ha"] += plan.hectareas_planificadas
        metric["real_ha"] += bucket["ejecutado"]
        metric["pendiente_ha"] += pendiente

        if plan.ventana_fin < today and pendiente > 0:
            atraso_dias = (today - plan.ventana_fin).days
            hectareas_fuera_ventana += pendiente
            lotes_atrasados.append(
                {
                    "lote": bucket["lote"].nombre,
                    "establecimiento": bucket["establecimiento"].nombre,
                    "cultivo": bucket["cultivo"].nombre,
                    "labor": labor,
                    "pendiente_ha": round(pendiente, 2),
                    "dias_atraso": atraso_dias,
                    "equipo": plan.equipo,
                }
            )

        est_bucket = pendientes_establecimiento_map.setdefault(
            (bucket["establecimiento"].nombre, labor),
            {
                "establecimiento": bucket["establecimiento"].nombre,
                "labor": labor,
                "pendiente_ha": 0.0,
                "plan_ha": 0.0,
            },
        )
        est_bucket["pendiente_ha"] += pendiente
        est_bucket["plan_ha"] += plan.hectareas_planificadas

    plan_vs_actual = []
    for item in plan_vs_actual_map.values():
        plan_vs_actual.append(
            {
                **item,
                "plan_ha": round(item["plan_ha"], 2),
                "real_ha": round(item["real_ha"], 2),
                "pendiente_ha": round(item["pendiente_ha"], 2),
                "cumplimiento_pct": round((item["real_ha"] / item["plan_ha"]) * 100, 1) if item["plan_ha"] else 0,
            }
        )
    plan_vs_actual.sort(key=lambda item: item["plan_ha"], reverse=True)
    lotes_atrasados.sort(key=lambda item: (-item["dias_atraso"], -item["pendiente_ha"]))

    productividad = []
    for item in productividad_map.values():
        productividad.append(
            {
                "recurso": item["recurso"],
                "tipo": item["tipo"],
                "hectareas": round(item["hectareas"], 2),
                "horas": round(item["horas"], 2),
                "ha_hora": round(item["hectareas"] / item["horas"], 2) if item["horas"] else 0,
            }
        )
    productividad.sort(key=lambda item: item["ha_hora"], reverse=True)

    pendientes_establecimiento = []
    for item in pendientes_establecimiento_map.values():
        pendientes_establecimiento.append(
            {
                **item,
                "pendiente_ha": round(item["pendiente_ha"], 2),
                "plan_ha": round(item["plan_ha"], 2),
                "pendiente_pct": round(
                    (item["pendiente_ha"] / item["plan_ha"]) * 100,
                    1,
                ) if item["plan_ha"] else 0,
            }
        )
    pendientes_establecimiento.sort(
        key=lambda item: (-item["pendiente_ha"], -item["pendiente_pct"])
    )

    ambientes = []
    for ambiente, lote, est, cultivo in ambiente_rows:
        desvio_pct = round(
            ((ambiente.rendimiento_real - ambiente.rendimiento_objetivo) / ambiente.rendimiento_objetivo) * 100,
            1,
        ) if ambiente.rendimiento_objetivo else 0
        ambientes.append(
            {
                "lote": lote.nombre,
                "establecimiento": est.nombre,
                "cultivo": cultivo.nombre,
                "ambiente": ambiente.ambiente,
                "hectareas": round(ambiente.hectareas, 2),
                "rendimiento_objetivo": round(ambiente.rendimiento_objetivo, 2),
                "rendimiento_real": round(ambiente.rendimiento_real, 2),
                "desvio_pct": desvio_pct,
                "margen_ha": round(ambiente.margen_ha or 0, 2),
            }
        )
    ambientes.sort(key=lambda item: item["margen_ha"])

    aplicaciones = []
    desvio_dosis_vals = []
    nutrientes_lote_map: dict[tuple[str, str], dict[str, float | str]] = {}
    for detalle, lote, est, cultivo in application_rows:
        desvio_pct = round(
            ((detalle.dosis_real - detalle.dosis_objetivo) / detalle.dosis_objetivo) * 100,
            1,
        ) if detalle.dosis_objetivo else 0
        desvio_dosis_vals.append(abs(desvio_pct))
        aplicaciones.append(
            {
                "lote": lote.nombre,
                "establecimiento": est.nombre,
                "cultivo": cultivo.nombre,
                "producto": detalle.producto,
                "ingrediente_activo": detalle.ingrediente_activo,
                "dosis_objetivo": detalle.dosis_objetivo,
                "dosis_real": detalle.dosis_real,
                "unidad": detalle.unidad,
                "desvio_pct": desvio_pct,
            }
        )
        nutrient_bucket = nutrientes_lote_map.setdefault(
            (lote.nombre, detalle.producto),
            {
                "lote": lote.nombre,
                "establecimiento": est.nombre,
                "cultivo": cultivo.nombre,
                "producto": detalle.producto,
                "ingrediente_activo": detalle.ingrediente_activo or "—",
                "dosis_aplicada_total": 0.0,
                "dosis_objetivo_total": 0.0,
            },
        )
        nutrient_bucket["dosis_aplicada_total"] += detalle.dosis_real or 0
        nutrient_bucket["dosis_objetivo_total"] += detalle.dosis_objetivo or 0
    aplicaciones.sort(key=lambda item: abs(item["desvio_pct"]), reverse=True)

    nutrientes_lote = []
    for item in nutrientes_lote_map.values():
        dosis_obj = float(item["dosis_objetivo_total"])
        dosis_real = float(item["dosis_aplicada_total"])
        nutrientes_lote.append(
            {
                "lote": item["lote"],
                "establecimiento": item["establecimiento"],
                "cultivo": item["cultivo"],
                "producto": item["producto"],
                "ingrediente_activo": item["ingrediente_activo"],
                "dosis_objetivo": round(dosis_obj, 2),
                "dosis_aplicada": round(dosis_real, 2),
                "desvio_pct": round(
                    ((dosis_real - dosis_obj) / dosis_obj) * 100,
                    1,
                ) if dosis_obj else 0,
            }
        )
    nutrientes_lote.sort(key=lambda item: abs(item["desvio_pct"]), reverse=True)

    observaciones = [
        {
            "lote": lote.nombre,
            "establecimiento": est.nombre,
            "cultivo": cultivo.nombre,
            "categoria": obs.categoria,
            "severidad": obs.severidad,
            "ambiente": obs.ambiente,
            "descripcion": obs.descripcion,
            "accion_sugerida": obs.accion_sugerida,
        }
        for obs, lote, est, cultivo in observation_rows
    ]
    observaciones.sort(key=lambda item: {"alta": 0, "media": 1, "baja": 2}.get(item["severidad"], 3))

    recomendaciones = [
        {
            "lote": lote.nombre,
            "cultivo": cultivo.nombre,
            "tipo_labor": rec.tipo_labor,
            "nutriente": rec.nutriente,
            "ingrediente_activo": rec.ingrediente_activo,
            "dosis_recomendada": rec.dosis_recomendada,
            "dosis_aplicada": rec.dosis_aplicada,
            "desvio_pct": rec.desvio_pct,
            "prioridad": rec.prioridad,
            "recomendacion": rec.recomendacion,
        }
        for rec, lote, _, cultivo in recommendation_rows
    ]
    recomendaciones.sort(key=lambda item: abs(item["desvio_pct"] or 0), reverse=True)

    performance_map: dict[str, dict[str, float | str]] = {}
    for ambiente in ambientes:
        bucket = performance_map.setdefault(
            ambiente["lote"],
            {
                "lote": ambiente["lote"],
                "establecimiento": ambiente["establecimiento"],
                "cultivo": ambiente["cultivo"],
                "margen_ha": 0.0,
                "desvio_pct_total": 0.0,
                "ambientes": 0.0,
            },
        )
        bucket["margen_ha"] += ambiente["margen_ha"]
        bucket["desvio_pct_total"] += ambiente["desvio_pct"]
        bucket["ambientes"] += 1

    performance_lotes = []
    for item in performance_map.values():
        ambientes_count = float(item["ambientes"])
        performance_lotes.append(
            {
                "lote": item["lote"],
                "establecimiento": item["establecimiento"],
                "cultivo": item["cultivo"],
                "margen_ha": round(float(item["margen_ha"]) / ambientes_count, 2),
                "desvio_pct": round(
                    float(item["desvio_pct_total"]) / ambientes_count,
                    1,
                ),
            }
        )
    performance_lotes.sort(key=lambda item: item["margen_ha"])

    actions = []
    if hectareas_fuera_ventana > 0:
        actions.append(
            {
                "titulo": "Recuperar labores atrasadas",
                "descripcion": f"Hay {hectareas_fuera_ventana:.0f} ha fuera de ventana optima. Priorizar los lotes con mayor contribucion esperada.",
                "owner": "Jefe de campo",
                "impacto": "Protege rinde y reduce sobrecostos",
                "severity": "critical" if hectareas_fuera_ventana > 200 else "warning",
            }
        )
    if desvio_dosis_vals and max(desvio_dosis_vals) > 10:
        actions.append(
            {
                "titulo": "Corregir aplicaciones con desvio de dosis",
                "descripcion": "Se detectaron lotes aplicados por fuera de la recomendacion. Revisar calibracion y receta.",
                "owner": "Agronomia",
                "impacto": "Reduce perdida de eficacia y costo extra",
                "severity": "warning",
            }
        )
    if observaciones:
        first = observaciones[0]
        actions.append(
            {
                "titulo": f"Atender {first['categoria']} en {first['lote']}",
                "descripcion": first["accion_sugerida"],
                "owner": "Monitoreo",
                "impacto": "Evita escalamiento del dano",
                "severity": "critical" if first["severidad"] == "alta" else "warning",
            }
        )
    for task in task_rows[:2]:
        actions.append(
            {
                "titulo": task.descripcion,
                "descripcion": task.impacto or "Tarea critica del frente agricola",
                "owner": task.responsable or "Campo",
                "impacto": task.impacto or "Operacion",
                "severity": "critical" if task.prioridad == "alta" else "warning",
            }
        )

    alerts = [
        {
            "titulo": alert.titulo,
            "descripcion": alert.descripcion,
            "accion": alert.accion_sugerida,
            "severidad": alert.severidad,
            "prioridad": alert.prioridad,
        }
        for alert in alert_rows
    ]

    delayed_lot_names = {item["lote"] for item in lotes_atrasados}

    return {
        "summary": {
            "superficie_total": round(superficie_total, 2),
            "sembrado": round(superficie_sembrada, 2),
            "cosechado": round(superficie_cosechada, 2),
            "rendimiento_promedio": round(rendimiento_promedio, 2),
            "variabilidad_rinde_pct": round(rendimiento_variabilidad, 1),
            "hectareas_fuera_ventana": round(hectareas_fuera_ventana, 2),
            "lotes_atrasados": len(delayed_lot_names),
            "desvio_aplicacion_promedio": round(sum(desvio_dosis_vals) / len(desvio_dosis_vals), 1) if desvio_dosis_vals else 0,
        },
        "avance_cultivos": avance_cultivos,
        "lotes": lotes_list,
        "rendimiento_historico": rendimiento_historico,
        "plan_vs_actual": plan_vs_actual,
        "lotes_atrasados": lotes_atrasados[:8],
        "pendientes_establecimiento": pendientes_establecimiento[:8],
        "productividad": productividad[:8],
        "performance_lotes": performance_lotes[:10],
        "rendimiento_ambientes": ambientes[:12],
        "aplicaciones": aplicaciones[:10],
        "nutrientes_lote": nutrientes_lote[:10],
        "observaciones": observaciones[:8],
        "recomendaciones": recomendaciones[:8],
        "alerts": alerts[:5],
        "actions": actions[:5],
        "ultima_actualizacion": datetime.now().isoformat(),
    }


async def get_lotes_list(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    estado: Optional[str] = None,
    cultivo_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
):
    q = select(Lote, Establecimiento, Cultivo).join(
        Establecimiento, Lote.establecimiento_id == Establecimiento.id
    ).outerjoin(Cultivo, Lote.cultivo_id == Cultivo.id)

    if empresa_id:
        q = q.where(Establecimiento.empresa_id == empresa_id)
    if campania_id:
        q = q.where(Lote.campania_id == campania_id)
    if establecimiento_id:
        q = q.where(Lote.establecimiento_id == establecimiento_id)
    if estado:
        q = q.where(Lote.estado == estado)
    if cultivo_id:
        q = q.where(Lote.cultivo_id == cultivo_id)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    rows = result.all()

    items = [
        {
            "id": str(lote.id),
            "nombre": lote.nombre,
            "establecimiento": est.nombre if est else "—",
            "cultivo": cultivo.nombre if cultivo else "—",
            "hectareas": lote.hectareas,
            "estado": lote.estado,
            "fecha_siembra": lote.fecha_siembra.isoformat() if lote.fecha_siembra else None,
            "rendimiento_tn_ha": lote.rendimiento_real,
            "costo_por_ha": None,
        }
        for lote, est, cultivo in rows
    ]

    return {"total": total, "page": page, "page_size": page_size, "items": items}
