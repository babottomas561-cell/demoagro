from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campania import Campania
from app.models.contrato import Contrato
from app.models.cultivo import Cultivo
from app.models.decision_support import (
    AlertaOperativa,
    AplicacionDetalle,
    ConsumoCombustible,
    CostosIndirectosAsignados,
    DesvioPlanReal,
    DowntimeMaquinaria,
    EjecucionLabor,
    EntregaComercial,
    ObservacionCampo,
    PlanLabor,
    PosicionComercial,
    PresupuestoInsumo,
    PresupuestoLote,
    RecomendacionAgronomica,
    RendimientoAmbiente,
    ServiceSchedule,
    StockProyectado,
    TareaCritica,
)
from app.models.establecimiento import Establecimiento
from app.models.insumo import Insumo, MovimientoInsumo
from app.models.lote import Lote
from app.models.maquinaria import Maquinaria
from app.models.producto import Producto
from app.models.stock import Stock


CROP_CONFIG = {
    "Soja": {"yield": 3.45, "direct": 392000, "indirect": 78000, "semilla": 80, "ferti": 115, "herb": 2.3},
    "Maiz": {"yield": 9.35, "direct": 548000, "indirect": 94000, "semilla": 24, "ferti": 165, "herb": 2.0},
    "Trigo": {"yield": 3.7, "direct": 318000, "indirect": 72000, "semilla": 130, "ferti": 140, "herb": 1.8},
    "Girasol": {"yield": 2.15, "direct": 286000, "indirect": 68000, "semilla": 7, "ferti": 95, "herb": 1.6},
    "Sorgo": {"yield": 7.2, "direct": 255000, "indirect": 65000, "semilla": 18, "ferti": 75, "herb": 1.7},
}

OPERATORS = {
    1: ["Martin Pereyra", "Luciano Rojas", "Ana Bianchi", "Gaston Ferrero"],
    2: ["Diego Bustos", "Pablo Mendez", "Carla Suarez", "Nicolas Rosales"],
}

OBSERVATION_TEMPLATES = [
    ("malezas", "Alta presion de rama negra", "Reforzar control con aplicacion post-emergente esta semana"),
    ("plagas", "Presencia de isoca por encima del umbral", "Priorizar monitoreo y correccion sectorizada"),
    ("nutricion", "Ambiente con respuesta baja a nitrogeno", "Ajustar dosis variable y monitorear disponibilidad"),
    ("humedad", "Baja humedad superficial en loma", "Reprogramar labor para evitar implantacion despareja"),
]


def _company_id(establecimiento: Establecimiento) -> int:
    return establecimiento.empresa_id


def _machine_by_type(maqs: list[Maquinaria], empresa_id: int, tipo: str) -> str:
    for maq in maqs:
        if maq.establecimiento and maq.establecimiento.empresa_id == empresa_id and maq.tipo == tipo:
            return f"{maq.marca} {maq.modelo}"
    return tipo.capitalize()


def _operator_for_company(empresa_id: int, index: int) -> str:
    pool = OPERATORS.get(empresa_id, OPERATORS[1])
    return pool[index % len(pool)]


async def seed_decisional_data(db: AsyncSession):
    existing = (await db.execute(select(PresupuestoLote.id).limit(1))).scalar_one_or_none()
    if existing:
        return

    lotes = (await db.execute(select(Lote))).scalars().all()
    campanias = (await db.execute(select(Campania))).scalars().all()
    establecimientos = (await db.execute(select(Establecimiento))).scalars().all()
    productos = (await db.execute(select(Producto))).scalars().all()
    insumos = (await db.execute(select(Insumo))).scalars().all()
    movimientos = (await db.execute(select(MovimientoInsumo))).scalars().all()
    maquinarias = (await db.execute(select(Maquinaria).join(Establecimiento))).scalars().all()
    contratos = (await db.execute(select(Contrato))).scalars().all()
    stocks = (await db.execute(select(Stock))).scalars().all()
    cultivos = (await db.execute(select(Cultivo))).scalars().all()

    camp_map = {camp.id: camp for camp in campanias}
    camp_name_map = {camp.nombre: camp for camp in campanias}
    est_map = {est.id: est for est in establecimientos}
    product_by_cultivo = {prod.cultivo_id: prod for prod in productos if prod.cultivo_id}
    cultivo_map = {cult.id: cult for cult in cultivos}
    insumo_map = {insumo.nombre: insumo for insumo in insumos}
    today = date.today()
    active_campaign = next((camp for camp in campanias if camp.activa), max(campanias, key=lambda item: item.fecha_inicio))
    active_campaign_id = active_campaign.id

    # Attach establecimiento lookup to machines for helper use.
    for maq in maquinarias:
        maq.establecimiento = est_map.get(maq.establecimiento_id)

    presupuestos_lote = []
    costos_indirectos = []
    desvios = []
    planes = []
    ejecuciones = []
    observaciones = []
    recomendaciones = []
    aplicaciones = []
    ambientes = []
    tareas = []
    alertas = []

    for index, lote in enumerate(lotes):
        cultivo = cultivo_map.get(lote.cultivo_id)
        campania = camp_map.get(lote.campania_id)
        establecimiento = est_map.get(lote.establecimiento_id)
        if not cultivo or not campania or not establecimiento:
            continue
        is_future_campaign = campania.fecha_inicio > today

        cfg = CROP_CONFIG.get(cultivo.nombre, CROP_CONFIG["Soja"])
        producto = product_by_cultivo.get(cultivo.id)
        price_plan = producto.precio_referencia if producto and producto.precio_referencia else cfg["direct"] / max(cfg["yield"], 1)
        yield_target = lote.rendimiento_historico or cfg["yield"]
        yield_real = lote.rendimiento_real if lote.rendimiento_real is not None else round(yield_target * (0.84 + (index % 5) * 0.04), 2)
        price_real = round(price_plan * (0.94 + (index % 6) * 0.018), 2)
        cost_plan = round(cfg["direct"] * (0.96 + (establecimiento.id % 4) * 0.04), 2)
        cost_real = round(cost_plan * (0.93 + (index % 7) * 0.045), 2)
        indirect_ha = round(cfg["indirect"] * (0.95 + (establecimiento.id % 3) * 0.05), 2)
        ingreso_plan_ha = round(yield_target * price_plan, 2)
        ingreso_real_ha = round(yield_real * price_real, 2)
        margen_objetivo = round(ingreso_plan_ha - cost_plan - indirect_ha, 2)

        presupuestos_lote.append(
            PresupuestoLote(
                lote_id=lote.id,
                campania_id=campania.id,
                rendimiento_objetivo_tn_ha=yield_target,
                rendimiento_real_tn_ha=yield_real,
                precio_objetivo_tn=price_plan,
                precio_real_tn=price_real,
                ingreso_plan_ha=ingreso_plan_ha,
                ingreso_real_ha=ingreso_real_ha,
                costo_directo_plan_ha=cost_plan,
                costo_directo_real_ha=cost_real,
                costo_indirecto_ha=indirect_ha,
                margen_objetivo_ha=margen_objetivo,
            )
        )

        for concepto, peso in (("administracion", 0.35), ("arrendamiento", 0.4), ("seguros", 0.25)):
            costos_indirectos.append(
                CostosIndirectosAsignados(
                    lote_id=lote.id,
                    campania_id=campania.id,
                    concepto=concepto,
                    monto_total=round(indirect_ha * lote.hectareas * peso, 2),
                    costo_ha=round(indirect_ha * peso, 2),
                )
            )

        margen_real = ingreso_real_ha - cost_real - indirect_ha
        desvio_margen = round(((margen_real - margen_objetivo) / margen_objetivo) * 100, 2) if margen_objetivo else 0
        desvios.append(
            DesvioPlanReal(
                modulo="finanzas",
                referencia=f"{establecimiento.nombre} / {lote.nombre}",
                metrica="margen_ha",
                plan_valor=margen_objetivo,
                real_valor=round(margen_real, 2),
                desvio_pct=desvio_margen,
                impacto_ars=round((margen_real - margen_objetivo) * lote.hectareas, 2),
                criticidad="alta" if desvio_margen < -15 else "media" if desvio_margen < -5 else "baja",
            )
        )

        for ambiente_nombre, factor in (("Loma", 0.88), ("Media loma", 1.0), ("Bajo", 1.09)):
            rend_real = round(yield_real * factor, 2)
            rend_obj = round(yield_target * factor, 2)
            ambientes.append(
                RendimientoAmbiente(
                    lote_id=lote.id,
                    ambiente=ambiente_nombre,
                    hectareas=round(lote.hectareas / 3, 2),
                    rendimiento_objetivo=rend_obj,
                    rendimiento_real=rend_real,
                    margen_ha=round((rend_real * price_real) - cost_real - indirect_ha, 2),
                )
            )

        if lote.fecha_siembra:
            base_date = lote.fecha_siembra
        elif is_future_campaign:
            base_date = campania.fecha_inicio + timedelta(days=95 + (index % 12))
        else:
            base_date = today - timedelta(days=20 - (index % 9))
        company_id = establecimiento.empresa_id
        siembra_equipo = _machine_by_type(maquinarias, company_id, "sembradora")
        fert_equipo = _machine_by_type(maquinarias, company_id, "tractor")
        aplica_equipo = _machine_by_type(maquinarias, company_id, "pulverizadora")
        cosecha_equipo = _machine_by_type(maquinarias, company_id, "cosechadora")

        plan_templates = [
            ("siembra", base_date - timedelta(days=5), base_date + timedelta(days=4), siembra_equipo, cfg["semilla"], "semilla"),
            ("fertilizacion", base_date + timedelta(days=15), base_date + timedelta(days=28), fert_equipo, cfg["ferti"], "Nitrogeno"),
            ("aplicacion", base_date + timedelta(days=32), base_date + timedelta(days=46), aplica_equipo, cfg["herb"], "Control malezas"),
        ]
        if lote.estado == "cosechado" and lote.fecha_cosecha:
            plan_templates.append(
                ("cosecha", lote.fecha_cosecha - timedelta(days=7), lote.fecha_cosecha + timedelta(days=3), cosecha_equipo, None, "cosecha")
            )

        for plan_idx, (tipo, ventana_ini, ventana_fin, equipo, dosis, etiqueta) in enumerate(plan_templates):
            prioridad = "alta" if tipo in {"siembra", "cosecha"} or index % 4 == 0 else "media"
            plan = PlanLabor(
                lote_id=lote.id,
                tipo_labor=tipo,
                ventana_inicio=ventana_ini,
                ventana_fin=ventana_fin,
                hectareas_planificadas=lote.hectareas,
                horas_estimadas=round(max(lote.hectareas / (18 if tipo == "siembra" else 26), 4), 1),
                equipo=equipo,
                operador=_operator_for_company(company_id, index + plan_idx),
                prioridad=prioridad,
                dosis_objetivo=dosis,
                nutriente_objetivo="Nitrogeno" if tipo == "fertilizacion" else None,
                ingrediente_activo="Glifosato + 2,4D" if tipo == "aplicacion" else None,
            )
            planes.append(plan)

            if is_future_campaign:
                progreso = 0.0
            elif lote.estado == "cosechado":
                progreso = 1.0
            elif tipo == "siembra":
                progreso = 1.0 if lote.estado == "sembrado" else 0.72 if index % 5 == 0 else 0.95
            elif tipo == "fertilizacion":
                progreso = 0.35 if index % 4 == 0 else 0.72 if index % 3 == 0 else 0.95
            elif tipo == "aplicacion":
                progreso = 0.0 if index % 5 == 0 else 0.55 if index % 2 == 0 else 0.9
            else:
                progreso = 0.0

            executed_ha = round(lote.hectareas * progreso, 2)
            if executed_ha > 0:
                ejecuciones.append(
                    EjecucionLabor(
                        plan_labor_id=0,  # set after flush
                        fecha=min(ventana_fin, today - timedelta(days=max(1, (index + plan_idx) % 4))),
                        hectareas_ejecutadas=executed_ha,
                        horas_trabajadas=round(max(executed_ha / (20 if tipo == "aplicacion" else 15), 2), 1),
                        equipo=equipo,
                        operador=_operator_for_company(company_id, index + plan_idx),
                        dosis_aplicada=(dosis or 0) * (0.9 + ((index + plan_idx) % 4) * 0.06) if dosis else None,
                        combustible_litros=round(executed_ha * (3.6 if tipo == "siembra" else 2.2), 1),
                        estado="completado" if progreso >= 0.98 else "parcial",
                        observacion=f"{tipo.capitalize()} registrada en lote {lote.nombre}",
                    )
                )

            if campania.id == active_campaign_id and tipo in {"fertilizacion", "aplicacion"} and index % 2 == 0:
                sev = "alta" if (index + plan_idx) % 4 == 0 else "media"
                categoria, descripcion, accion = OBSERVATION_TEMPLATES[(index + plan_idx) % len(OBSERVATION_TEMPLATES)]
                observaciones.append(
                    ObservacionCampo(
                        lote_id=lote.id,
                        fecha=today - timedelta(days=(index % 6) + plan_idx),
                        categoria=categoria,
                        severidad=sev,
                        ambiente="Loma" if index % 3 == 0 else "Bajo",
                        cobertura_pct=round(12 + (index % 6) * 6.5, 1),
                        descripcion=descripcion,
                        accion_sugerida=accion,
                    )
                )
                desvio_dosis = round((((executed_ha / max(lote.hectareas, 1)) * 100) - 100) * 0.18, 1)
                recomendaciones.append(
                    RecomendacionAgronomica(
                        lote_id=lote.id,
                        tipo_labor=tipo,
                        nutriente="Nitrogeno" if tipo == "fertilizacion" else None,
                        ingrediente_activo="Glifosato + graminicida" if tipo == "aplicacion" else None,
                        dosis_recomendada=dosis,
                        dosis_aplicada=round((dosis or 0) * (1 + (desvio_dosis / 100)), 2) if dosis else None,
                        desvio_pct=desvio_dosis,
                        prioridad="alta" if abs(desvio_dosis) > 10 else "media",
                        recomendacion=accion,
                    )
                )
                aplicaciones.append(
                    AplicacionDetalle(
                        lote_id=lote.id,
                        fecha=today - timedelta(days=(index % 4) + 1),
                        producto="Urea granulada" if tipo == "fertilizacion" else "Roundup + 2,4D",
                        ingrediente_activo="N" if tipo == "fertilizacion" else "Glifosato",
                        dosis_objetivo=dosis,
                        dosis_real=round((dosis or 0) * (0.92 + (index % 3) * 0.05), 2) if dosis else None,
                        unidad="kg/ha" if tipo == "fertilizacion" else "lt/ha",
                    )
                )

        if campania.id == active_campaign_id and (index % 4 == 0 or desvio_margen < -10):
            tareas.append(
                TareaCritica(
                    modulo="agricola",
                    lote_id=lote.id,
                    descripcion=f"Revisar {lote.nombre}: fuera de ventana o con desvio de margen",
                    responsable=_operator_for_company(company_id, index),
                    vence_el=today + timedelta(days=3 + (index % 4)),
                    estado="abierta",
                    prioridad="alta" if desvio_margen < -15 else "media",
                    impacto="Riesgo de perdida de rinde y mayor costo operativo",
                )
            )

    db.add_all(presupuestos_lote + costos_indirectos + desvios + planes + observaciones + recomendaciones + aplicaciones + ambientes + tareas)
    await db.flush()

    # Link execution rows to created plan rows using insertion order.
    plan_index = 0
    pending_execs = []
    for lote in lotes:
        cultivo = cultivo_map.get(lote.cultivo_id)
        campania = camp_map.get(lote.campania_id)
        if not cultivo or not campania:
            continue
        template_count = 4 if lote.estado == "cosechado" and lote.fecha_cosecha else 3
        lote_plans = planes[plan_index: plan_index + template_count]
        plan_index += template_count
        for plan in lote_plans:
            for exec_row in ejecuciones:
                if exec_row.plan_labor_id == 0 and exec_row.observacion.endswith(f"lote {lote.nombre}") and exec_row.equipo == plan.equipo and exec_row.observacion.startswith(plan.tipo_labor.capitalize()):
                    exec_row.plan_labor_id = plan.id
                    pending_execs.append(exec_row)
                    break

    db.add_all(pending_execs)
    await db.flush()

    # Presupuesto y stock proyectado de insumos.
    stock_actual_by_key: dict[tuple[int, int], float] = defaultdict(float)
    for movimiento in movimientos:
        sign = 1 if movimiento.tipo == "ingreso" else -1
        stock_actual_by_key[(movimiento.establecimiento_id, movimiento.insumo_id)] += sign * (movimiento.cantidad or 0)

    presupuestos_insumo = []
    stock_proyectado_rows = []
    for (est_id, insumo_id), stock_actual in stock_actual_by_key.items():
        insumo = next((item for item in insumos if item.id == insumo_id), None)
        if not insumo:
            continue
        consumo_plan = max(abs(stock_actual) * 0.35, 1)
        consumo_real = max(consumo_plan * (0.84 + (insumo_id % 4) * 0.08), 0.5)
        cobertura_dias = round(max(stock_actual, 0) / max(consumo_real / 30, 0.1), 1)
        cobertura_ha = round(max(stock_actual, 0) / max((consumo_real / 180), 0.1), 1)
        quiebre = None if cobertura_dias > 45 else max(int(cobertura_dias), 1)
        compra = max(round(consumo_plan * 1.4 - max(stock_actual, 0), 2), 0)
        severidad = "critical" if cobertura_dias < 10 else "warning" if cobertura_dias < 25 else "ok"

        presupuestos_insumo.append(
            PresupuestoInsumo(
                establecimiento_id=est_id,
                insumo_id=insumo_id,
                campania_id=active_campaign_id,
                consumo_plan=round(consumo_plan, 2),
                costo_plan=round(consumo_plan * insumo.precio_unitario, 2),
                unidad=insumo.unidad,
            )
        )
        stock_proyectado_rows.append(
            StockProyectado(
                establecimiento_id=est_id,
                insumo_id=insumo_id,
                fecha_corte=today,
                stock_actual=round(max(stock_actual, 0), 2),
                consumo_plan_mes=round(consumo_plan, 2),
                consumo_real_mes=round(consumo_real, 2),
                cobertura_dias=cobertura_dias,
                cobertura_ha=cobertura_ha,
                quiebre_en_dias=quiebre,
                compra_sugerida=compra,
                stock_inmovilizado=round(max(stock_actual - (consumo_plan * 2), 0), 2),
                costo_inventario=round(max(stock_actual, 0) * insumo.precio_unitario, 2),
                severidad=severidad,
            )
        )

    # Commercial position and deliveries.
    entregas = []
    posiciones = []
    delivered_by_contract = defaultdict(float)
    for idx, contrato in enumerate(contratos):
        if contrato.estado == "cumplido":
            delivered_ratio = 1.0
            delivery_state = "entregada"
        else:
            delivered_ratio = 0.62 if idx % 3 == 0 else 0.38 if idx % 2 == 0 else 0.18
            delivery_state = "programada" if idx % 2 == 0 else "pendiente"
        delivered = round((contrato.volumen_contratado or 0) * delivered_ratio, 2)
        delivered_by_contract[contrato.id] = delivered
        entregas.append(
            EntregaComercial(
                contrato_id=contrato.id,
                fecha_programada=contrato.fecha_entrega - timedelta(days=7 if contrato.estado != "cumplido" else 21),
                fecha_entrega=contrato.fecha_entrega if contrato.estado == "cumplido" else None,
                volumen_tn=delivered,
                estado=delivery_state if contrato.estado != "cumplido" else "entregada",
            )
        )

    stock_by_company_crop = defaultdict(float)
    for stock in stocks:
        producto = next((prod for prod in productos if prod.id == stock.producto_id), None)
        establecimiento = est_map.get(stock.establecimiento_id)
        if not producto or not establecimiento or not producto.cultivo_id:
            continue
        stock_by_company_crop[(establecimiento.empresa_id, producto.cultivo_id)] += stock.volumen_disponible or 0

    contracts_by_key = defaultdict(list)
    for contrato in contratos:
        contracts_by_key[(contrato.empresa_id, contrato.campania_id, contrato.cultivo_id)].append(contrato)

    for key, contract_rows in contracts_by_key.items():
        empresa_id, campania_id, cultivo_id = key
        comprometidas = sum(c.volumen_contratado or 0 for c in contract_rows)
        fijadas = sum(
            c.volumen_contratado or 0
            for c in contract_rows
            if c.precio_fijado is not None
        )
        entregadas = sum(delivered_by_contract[c.id] for c in contract_rows)
        stock_fisico = stock_by_company_crop.get((empresa_id, cultivo_id), 0)
        producidas = round(max(stock_fisico + entregadas + (comprometidas * 0.15), comprometidas * 1.12), 2)
        precio_ref = product_by_cultivo.get(cultivo_id).precio_referencia if product_by_cultivo.get(cultivo_id) else 0
        abierto = producidas - fijadas
        if abierto > producidas * 0.35:
            recomendacion = "fijar"
        elif stock_fisico < comprometidas * 0.25:
            recomendacion = "cubrir"
        else:
            recomendacion = "esperar"

        posiciones.append(
            PosicionComercial(
                empresa_id=empresa_id,
                campania_id=campania_id,
                cultivo_id=cultivo_id,
                toneladas_producidas=producidas,
                toneladas_comprometidas=round(comprometidas, 2),
                toneladas_fijadas=round(fijadas, 2),
                toneladas_entregadas=round(entregadas, 2),
                stock_fisico=round(stock_fisico, 2),
                precio_referencia=precio_ref or 0,
                recomendacion=recomendacion,
            )
        )

    # Fleet support data.
    downtime_rows = []
    consumo_rows = []
    service_rows = []
    for idx, maquina in enumerate(maquinarias):
        criticidad = "alta" if maquina.tipo in {"sembradora", "cosechadora"} else "media"
        next_service_days = 6 + (idx % 8) * 4
        service_rows.append(
            ServiceSchedule(
                maquinaria_id=maquina.id,
                fecha_programada=today + timedelta(days=next_service_days),
                horas_programadas=round((maquina.horas_totales or 0) + 180, 1),
                tipo_service="Service preventivo",
                criticidad_operativa=criticidad,
                riesgo_si_falla=(
                    "Puede frenar siembra en 180 ha"
                    if maquina.tipo == "sembradora"
                    else "Puede atrasar cosecha y entrega"
                    if maquina.tipo == "cosechadora"
                    else "Reduce capacidad de apoyo operativo"
                ),
                completado=False,
            )
        )

        if idx % 3 == 0 or maquina.estado != "operativo":
            downtime_hours = round(6 + (idx % 5) * 5.5, 1)
            downtime_rows.append(
                DowntimeMaquinaria(
                    maquinaria_id=maquina.id,
                    fecha_inicio=datetime.combine(today - timedelta(days=idx % 6 + 3), time(8, 0)),
                    fecha_fin=datetime.combine(today - timedelta(days=idx % 6 + 2), time(16, 0)),
                    motivo="Falla hidraulica" if idx % 2 == 0 else "Espera repuesto",
                    horas_downtime=downtime_hours,
                    criticidad="alta" if criticidad == "alta" else "media",
                    impacto_ha=round(downtime_hours * (7 if maquina.tipo == "sembradora" else 5), 1),
                )
            )

        linked_lote = next((l for l in lotes if l.establecimiento_id == maquina.establecimiento_id and l.campania_id == active_campaign_id), None)
        consumo_rows.append(
            ConsumoCombustible(
                maquinaria_id=maquina.id,
                lote_id=linked_lote.id if linked_lote else None,
                fecha=today - timedelta(days=idx % 7),
                litros=round((32 + (idx % 6) * 8) * (1.4 if maquina.tipo == "cosechadora" else 1), 1),
                hectareas=round(18 + (idx % 5) * 7, 1),
                labor_tipo="siembra" if maquina.tipo == "sembradora" else "cosecha" if maquina.tipo == "cosechadora" else "aplicacion",
            )
        )

        if idx % 4 == 0:
            tareas.append(
                TareaCritica(
                    modulo="maquinaria",
                    maquinaria_id=maquina.id,
                    descripcion=f"Confirmar repuesto y disponibilidad de {maquina.marca} {maquina.modelo}",
                    responsable=_operator_for_company(est_map[maquina.establecimiento_id].empresa_id, idx),
                    vence_el=today + timedelta(days=2 + (idx % 3)),
                    estado="abierta",
                    prioridad="alta" if criticidad == "alta" else "media",
                    impacto="Riesgo de cuello de botella en labores clave",
                )
            )

    # Cross-module alerts.
    alert_specs = [
        ("dashboard", "warning", "lote", "margen", "Hay lotes con margen por ha debajo del objetivo", "Revisar top/bottom lotes y ajustar paquete tecnologico", 10),
        ("agricola", "critical", "labor", "siembra", "Hay hectareas fuera de ventana optima de siembra", "Priorizar lotes de mayor margen esperado", 5),
        ("comercial", "warning", "cultivo", "maiz", "El maiz mantiene una posicion abierta relevante sin fijar", "Evaluar cobertura parcial o fijacion escalonada", 15),
        ("stock", "critical", "insumo", "urea", "Urea con cobertura menor a 10 dias al ritmo actual", "Emitir compra corta y reprogramar aplicaciones", 8),
        ("maquinaria", "warning", "maquinaria", "sembradora", "Sembradora principal concentra riesgo operativo", "Adelantar service y reservar reemplazo", 12),
        ("finanzas", "warning", "caja", "flujo", "La caja proyectada entra en zona de tension antes de 45 dias", "Coordinar entregas y diferir egresos no criticos", 9),
    ]
    for modulo, severidad, entidad_tipo, entidad_id, titulo, accion, prioridad in alert_specs:
        alertas.append(
            AlertaOperativa(
                modulo=modulo,
                severidad=severidad,
                entidad_tipo=entidad_tipo,
                entidad_id=entidad_id,
                titulo=titulo,
                descripcion=accion,
                accion_sugerida=accion,
                prioridad=prioridad,
            )
        )

    db.add_all(
        presupuestos_insumo
        + stock_proyectado_rows
        + entregas
        + posiciones
        + downtime_rows
        + consumo_rows
        + service_rows
        + alertas
    )
    await db.flush()
