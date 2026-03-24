from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date

from app.models.empresa import Empresa
from app.models.establecimiento import Establecimiento
from app.models.campania import Campania
from app.models.cultivo import Cultivo
from app.models.lote import Lote
from app.models.labor import Labor
from app.models.cosecha import Cosecha
from app.models.insumo import Insumo, MovimientoInsumo
from app.seed.campaign_utils import build_campaign_template_map, shift_date_years


async def seed_agricola(db: AsyncSession):
    # Fetch existing data
    empresas = (await db.execute(select(Empresa))).scalars().all()
    ests = (await db.execute(select(Establecimiento))).scalars().all()
    campanias = (await db.execute(select(Campania).order_by(Campania.fecha_inicio))).scalars().all()
    cultivos = (await db.execute(select(Cultivo))).scalars().all()
    insumos = (await db.execute(select(Insumo))).scalars().all()

    est_map = {e.nombre: e for e in ests}
    camp_map = {c.nombre: c for c in campanias}
    cult_map = {c.nombre: c for c in cultivos}
    ins_map = {i.nombre: i for i in insumos}

    campaign_map, year_delta = build_campaign_template_map(date.today())
    current_campaign_name = campaign_map["2024/2025"]
    today = date.today()

    # ---- Lotes Empresa 1 - El Progreso (4 establecimientos) ----
    lotes_data = [
        # Establecimiento: El Progreso - Lote Norte (850 ha)
        ("El Progreso - Lote Norte", "Cuadro 1 Norte", 250, "Soja", "2022/2023", "cosechado", date(2022, 11, 5), date(2023, 4, 10), 3.45, 3.30),
        ("El Progreso - Lote Norte", "Cuadro 2 Norte", 180, "Maiz", "2022/2023", "cosechado", date(2022, 10, 20), date(2023, 3, 25), 9.80, 9.50),
        ("El Progreso - Lote Norte", "Cuadro 3 Norte", 200, "Soja", "2022/2023", "cosechado", date(2022, 11, 10), date(2023, 4, 15), 3.20, 3.30),
        ("El Progreso - Lote Norte", "Cuadro 1 Norte", 250, "Soja", "2023/2024", "cosechado", date(2023, 11, 8), date(2024, 4, 12), 3.60, 3.30),
        ("El Progreso - Lote Norte", "Cuadro 2 Norte", 180, "Maiz", "2023/2024", "cosechado", date(2023, 10, 25), date(2024, 3, 28), 10.20, 9.50),
        ("El Progreso - Lote Norte", "Cuadro 3 Norte", 200, "Trigo", "2023/2024", "cosechado", date(2023, 6, 20), date(2023, 12, 8), 3.80, 3.60),
        ("El Progreso - Lote Norte", "Cuadro 1 Norte", 250, "Soja", "2024/2025", "sembrado", date(2024, 11, 5), None, None, 3.30),
        ("El Progreso - Lote Norte", "Cuadro 2 Norte", 180, "Maiz", "2024/2025", "cosechado", date(2024, 10, 22), date(2025, 3, 18), 9.15, 9.50),
        ("El Progreso - Lote Norte", "Cuadro 3 Norte", 200, "Trigo", "2024/2025", "cosechado", date(2024, 6, 18), date(2024, 12, 9), 3.65, 3.60),
        # Establecimiento: El Progreso - Lote Sur (1200 ha)
        ("El Progreso - Lote Sur", "Potrero A", 320, "Soja", "2022/2023", "cosechado", date(2022, 11, 15), date(2023, 4, 20), 3.55, 3.40),
        ("El Progreso - Lote Sur", "Potrero B", 280, "Maiz", "2022/2023", "cosechado", date(2022, 10, 30), date(2023, 4, 5), 10.10, 9.80),
        ("El Progreso - Lote Sur", "Potrero C", 250, "Girasol", "2022/2023", "cosechado", date(2022, 10, 10), date(2023, 2, 20), 2.20, 2.10),
        ("El Progreso - Lote Sur", "Potrero A", 320, "Soja", "2023/2024", "cosechado", date(2023, 11, 12), date(2024, 4, 18), 3.72, 3.40),
        ("El Progreso - Lote Sur", "Potrero B", 280, "Maiz", "2023/2024", "cosechado", date(2023, 10, 28), date(2024, 4, 2), 10.40, 9.80),
        ("El Progreso - Lote Sur", "Potrero C", 250, "Soja", "2023/2024", "cosechado", date(2023, 11, 18), date(2024, 4, 22), 3.40, 3.40),
        ("El Progreso - Lote Sur", "Potrero A", 320, "Soja", "2024/2025", "sembrado", date(2024, 11, 10), None, None, 3.40),
        ("El Progreso - Lote Sur", "Potrero B", 280, "Maiz", "2024/2025", "cosechado", date(2024, 10, 26), date(2025, 3, 14), 9.45, 9.80),
        ("El Progreso - Lote Sur", "Potrero C", 250, "Girasol", "2024/2025", "cosechado", date(2024, 10, 9), date(2025, 2, 20), 2.28, 2.10),
        # Establecimiento: El Progreso - Campo Pampeano (680 ha)
        ("El Progreso - Campo Pampeano", "Lote 1", 200, "Soja", "2022/2023", "cosechado", date(2022, 11, 20), date(2023, 4, 25), 3.10, 3.20),
        ("El Progreso - Campo Pampeano", "Lote 2", 220, "Maiz", "2022/2023", "cosechado", date(2022, 11, 1), date(2023, 4, 8), 9.50, 9.30),
        ("El Progreso - Campo Pampeano", "Lote 1", 200, "Soja", "2023/2024", "cosechado", date(2023, 11, 18), date(2024, 4, 22), 3.35, 3.20),
        ("El Progreso - Campo Pampeano", "Lote 2", 220, "Maiz", "2023/2024", "cosechado", date(2023, 10, 30), date(2024, 4, 5), 9.80, 9.30),
        ("El Progreso - Campo Pampeano", "Lote 1", 200, "Soja", "2024/2025", "sembrado", date(2024, 11, 15), None, None, 3.20),
        ("El Progreso - Campo Pampeano", "Lote 2", 220, "Maiz", "2024/2025", "sembrado", date(2024, 10, 30), None, None, 9.30),
        # Establecimiento: El Progreso - Est. La Esperanza (520 ha)
        ("El Progreso - Est. La Esperanza", "Cuartel Norte", 180, "Soja", "2023/2024", "cosechado", date(2023, 11, 5), date(2024, 4, 10), 3.50, 3.35),
        ("El Progreso - Est. La Esperanza", "Cuartel Sur", 160, "Trigo", "2023/2024", "cosechado", date(2023, 6, 15), date(2023, 12, 5), 3.70, 3.50),
        ("El Progreso - Est. La Esperanza", "Cuartel Norte", 180, "Soja", "2024/2025", "sembrado", date(2024, 11, 8), None, None, 3.35),
        ("El Progreso - Est. La Esperanza", "Cuartel Sur", 160, "Trigo", "2024/2025", "cosechado", date(2024, 6, 15), date(2024, 12, 5), 3.82, 3.50),
        # Establecimiento: Del Sur - Est. San Carlos (960 ha)
        ("Del Sur - Est. San Carlos", "Bloque 1", 300, "Soja", "2022/2023", "cosechado", date(2022, 11, 10), date(2023, 4, 15), 3.30, 3.25),
        ("Del Sur - Est. San Carlos", "Bloque 2", 250, "Maiz", "2022/2023", "cosechado", date(2022, 10, 25), date(2023, 4, 1), 9.20, 9.00),
        ("Del Sur - Est. San Carlos", "Bloque 3", 200, "Girasol", "2022/2023", "cosechado", date(2022, 10, 5), date(2023, 2, 15), 2.15, 2.10),
        ("Del Sur - Est. San Carlos", "Bloque 1", 300, "Soja", "2023/2024", "cosechado", date(2023, 11, 8), date(2024, 4, 12), 3.55, 3.25),
        ("Del Sur - Est. San Carlos", "Bloque 2", 250, "Maiz", "2023/2024", "cosechado", date(2023, 10, 22), date(2024, 3, 28), 9.60, 9.00),
        ("Del Sur - Est. San Carlos", "Bloque 1", 300, "Soja", "2024/2025", "sembrado", date(2024, 11, 5), None, None, 3.25),
        ("Del Sur - Est. San Carlos", "Bloque 2", 250, "Maiz", "2024/2025", "sembrado", date(2024, 10, 20), None, None, 9.00),
        ("Del Sur - Est. San Carlos", "Bloque 3", 200, "Girasol", "2024/2025", "cosechado", date(2024, 10, 6), date(2025, 2, 12), 2.22, 2.10),
        # Establecimiento: Del Sur - Campo Meridional (750 ha)
        ("Del Sur - Campo Meridional", "Lote Sur 1", 280, "Soja", "2022/2023", "cosechado", date(2022, 11, 12), date(2023, 4, 18), 3.25, 3.20),
        ("Del Sur - Campo Meridional", "Lote Sur 2", 260, "Sorgo", "2022/2023", "cosechado", date(2022, 11, 5), date(2023, 3, 20), 7.50, 7.20),
        ("Del Sur - Campo Meridional", "Lote Sur 1", 280, "Soja", "2023/2024", "cosechado", date(2023, 11, 10), date(2024, 4, 15), 3.45, 3.20),
        ("Del Sur - Campo Meridional", "Lote Sur 2", 260, "Maiz", "2023/2024", "cosechado", date(2023, 10, 25), date(2024, 3, 30), 9.30, 8.80),
        ("Del Sur - Campo Meridional", "Lote Sur 1", 280, "Soja", "2024/2025", "sembrado", date(2024, 11, 8), None, None, 3.20),
        ("Del Sur - Campo Meridional", "Lote Sur 2", 260, "Maiz", "2024/2025", "cosechado", date(2024, 10, 22), date(2025, 3, 10), 8.95, 8.80),
        # Establecimiento: Del Sur - La Pampa Norte (1100 ha)
        ("Del Sur - La Pampa Norte", "Potrero 1", 350, "Soja", "2023/2024", "cosechado", date(2023, 11, 15), date(2024, 4, 20), 3.20, 3.10),
        ("Del Sur - La Pampa Norte", "Potrero 2", 300, "Maiz", "2023/2024", "cosechado", date(2023, 10, 28), date(2024, 4, 3), 8.90, 8.50),
        ("Del Sur - La Pampa Norte", "Potrero 3", 200, "Girasol", "2023/2024", "cosechado", date(2023, 10, 10), date(2024, 2, 25), 2.05, 2.00),
        ("Del Sur - La Pampa Norte", "Potrero 1", 350, "Soja", "2024/2025", "sembrado", date(2024, 11, 12), None, None, 3.10),
        ("Del Sur - La Pampa Norte", "Potrero 2", 300, "Maiz", "2024/2025", "sembrado", date(2024, 10, 24), None, None, 8.50),
        ("Del Sur - La Pampa Norte", "Potrero 3", 200, "Girasol", "2024/2025", "cosechado", date(2024, 10, 11), date(2025, 2, 24), 2.12, 2.00),
        # Establecimiento: Del Sur - Est. El Amanecer (430 ha)
        ("Del Sur - Est. El Amanecer", "Seccion A", 200, "Soja", "2023/2024", "cosechado", date(2023, 11, 10), date(2024, 4, 15), 3.40, 3.30),
        ("Del Sur - Est. El Amanecer", "Seccion B", 150, "Trigo", "2023/2024", "cosechado", date(2023, 6, 10), date(2023, 12, 2), 3.65, 3.50),
        ("Del Sur - Est. El Amanecer", "Seccion A", 200, "Soja", "2024/2025", "sembrado", date(2024, 11, 6), None, None, 3.30),
        ("Del Sur - Est. El Amanecer", "Seccion B", 150, "Trigo", "2024/2025", "cosechado", date(2024, 6, 12), date(2024, 12, 3), 3.70, 3.50),
        # Establecimiento: Del Sur - Loma Negra (580 ha)
        ("Del Sur - Loma Negra", "Cuartel 1", 220, "Soja", "2023/2024", "cosechado", date(2023, 11, 18), date(2024, 4, 22), 3.15, 3.10),
        ("Del Sur - Loma Negra", "Cuartel 2", 200, "Sorgo", "2023/2024", "cosechado", date(2023, 11, 5), date(2024, 3, 18), 7.20, 7.00),
        ("Del Sur - Loma Negra", "Cuartel 1", 220, "Soja", "2024/2025", "sembrado", date(2024, 11, 18), None, None, 3.10),
        ("Del Sur - Loma Negra", "Cuartel 2", 200, "Maiz", "2024/2025", "sembrado", date(2024, 10, 28), None, None, 8.50),
        # Campaña futura planificada
        ("El Progreso - Lote Norte", "Cuadro 1 Norte", 250, "Trigo", "2025/2026", "barbecho", None, None, None, 3.35),
        ("El Progreso - Lote Sur", "Potrero A", 320, "Maiz", "2025/2026", "barbecho", None, None, None, 9.70),
        ("El Progreso - Campo Pampeano", "Lote 1", 200, "Soja", "2025/2026", "barbecho", None, None, None, 3.25),
        ("Del Sur - Est. San Carlos", "Bloque 1", 300, "Trigo", "2025/2026", "barbecho", None, None, None, 3.55),
        ("Del Sur - Campo Meridional", "Lote Sur 1", 280, "Soja", "2025/2026", "barbecho", None, None, None, 3.25),
        ("Del Sur - La Pampa Norte", "Potrero 2", 300, "Maiz", "2025/2026", "barbecho", None, None, None, 8.70),
        ("Del Sur - Est. El Amanecer", "Seccion A", 200, "Soja", "2025/2026", "barbecho", None, None, None, 3.35),
        ("Del Sur - Loma Negra", "Cuartel 2", 200, "Girasol", "2025/2026", "barbecho", None, None, None, 2.05),
    ]

    lotes = []
    for est_nombre, lote_nombre, ha, cult_nombre, camp_nombre, estado, f_siembra, f_cosecha, rend_real, rend_hist in lotes_data:
        est = est_map.get(est_nombre)
        cult = cult_map.get(cult_nombre)
        mapped_campaign_name = campaign_map.get(camp_nombre, camp_nombre)
        camp = camp_map.get(mapped_campaign_name)
        if not est:
            continue
        lote = Lote(
            establecimiento_id=est.id,
            nombre=lote_nombre,
            hectareas=ha,
            cultivo_id=cult.id if cult else None,
            campania_id=camp.id if camp else None,
            estado=estado,
            fecha_siembra=shift_date_years(f_siembra, year_delta),
            fecha_cosecha=shift_date_years(f_cosecha, year_delta),
            rendimiento_real=rend_real,
            rendimiento_historico=rend_hist,
        )
        lotes.append(lote)

    db.add_all(lotes)
    await db.flush()

    # ---- Labores ----
    labores = []
    tipos_labor = ["siembra", "fumigacion", "fertilizacion", "cosecha", "fumigacion"]
    costos_base = {
        "siembra": 18000,
        "fumigacion": 9500,
        "fertilizacion": 14000,
        "cosecha": 35000,
        "labranza": 12000,
    }

    for lote in lotes:
        if lote.estado in ("cosechado", "sembrado"):
            for tipo, costo_base in [
                ("siembra", 18000),
                ("fumigacion", 9500),
                ("fertilizacion", 14000),
            ]:
                if lote.fecha_siembra:
                    from datetime import timedelta
                    delta_dias = {"siembra": 0, "fumigacion": 30, "fertilizacion": 20}
                    fecha = lote.fecha_siembra + timedelta(days=delta_dias[tipo])
                    labores.append(Labor(
                        lote_id=lote.id,
                        tipo=tipo,
                        fecha=fecha,
                        costo_ha=costo_base * (1 + (lote.establecimiento_id % 3) * 0.1),
                        observacion=f"{tipo.capitalize()} campaña {lote.campania_id}",
                    ))

            if lote.estado == "cosechado" and lote.fecha_cosecha:
                labores.append(Labor(
                    lote_id=lote.id,
                    tipo="cosecha",
                    fecha=lote.fecha_cosecha,
                    costo_ha=35000,
                    observacion="Cosecha contratista",
                ))

            if (
                lote.fecha_siembra
                and lote.campania_id == camp_map[current_campaign_name].id
                and lote.cultivo_id in {
                    cult_map["Soja"].id,
                    cult_map["Maiz"].id,
                    cult_map["Girasol"].id,
                }
            ):
                ref_days = 70 if lote.cultivo_id == cult_map["Girasol"].id else 82 if lote.cultivo_id == cult_map["Soja"].id else 95
                ref_date = lote.fecha_siembra + timedelta(days=ref_days)
                if ref_date <= today:
                    labores.append(Labor(
                        lote_id=lote.id,
                        tipo="fumigacion",
                        fecha=ref_date,
                        costo_ha=11200 * (1 + (lote.establecimiento_id % 3) * 0.08),
                        observacion=f"Refuerzo sanitario verano campaña {lote.campania_id}",
                    ))
                fert_date = lote.fecha_siembra + timedelta(days=55 if lote.cultivo_id == cult_map["Maiz"].id else 48)
                if fert_date <= today and lote.cultivo_id in {cult_map["Soja"].id, cult_map["Maiz"].id}:
                    labores.append(Labor(
                        lote_id=lote.id,
                        tipo="fertilizacion",
                        fecha=fert_date,
                        costo_ha=16800 * (1 + (lote.establecimiento_id % 3) * 0.07),
                        observacion=f"Ajuste nutricional de verano campaña {lote.campania_id}",
                    ))

    db.add_all(labores)
    await db.flush()

    # ---- Cosechas ----
    cosechas = []
    for lote in lotes:
        if lote.estado == "cosechado" and lote.rendimiento_real and lote.fecha_cosecha:
            cosechas.append(Cosecha(
                lote_id=lote.id,
                fecha=lote.fecha_cosecha,
                volumen_cosechado=round(lote.rendimiento_real * lote.hectareas, 2),
                humedad=13.5 + (lote.id % 5) * 0.5,
                merma=1.5 + (lote.id % 3) * 0.2,
                rendimiento=lote.rendimiento_real,
            ))
    db.add_all(cosechas)
    await db.flush()

    # ---- Movimientos de Insumos ----
    movimientos = []
    gas_oil = ins_map.get("Gas Oil")
    urea = ins_map.get("Urea Granulada")
    roundup = ins_map.get("Roundup (Glifosato 48%)")
    semilla_soja = ins_map.get("Soja RR1 Intacta")
    semilla_maiz = ins_map.get("Maiz DK 7010 VT3P")

    for lote in lotes[:20]:  # Movimientos para los primeros 20 lotes
        if not lote.fecha_siembra:
            continue
        if semilla_soja and lote.cultivo_id == cult_map.get("Soja", type("", (), {"id": -1})()).id:
            qty = lote.hectareas * 80  # 80 kg/ha
            movimientos.append(MovimientoInsumo(
                establecimiento_id=lote.establecimiento_id,
                insumo_id=semilla_soja.id,
                tipo="egreso",
                cantidad=qty,
                fecha=lote.fecha_siembra,
                costo_total=qty * semilla_soja.precio_unitario,
                lote_id=lote.id,
            ))
        if roundup:
            qty_r = lote.hectareas * 3  # 3 lt/ha
            movimientos.append(MovimientoInsumo(
                establecimiento_id=lote.establecimiento_id,
                insumo_id=roundup.id,
                tipo="egreso",
                cantidad=qty_r,
                fecha=lote.fecha_siembra,
                costo_total=qty_r * roundup.precio_unitario,
                lote_id=lote.id,
            ))
        if urea:
            qty_u = lote.hectareas * 0.15  # 150 kg/ha -> 0.15 tn
            movimientos.append(MovimientoInsumo(
                establecimiento_id=lote.establecimiento_id,
                insumo_id=urea.id,
                tipo="egreso",
                cantidad=qty_u,
                fecha=lote.fecha_siembra,
                costo_total=qty_u * urea.precio_unitario,
                lote_id=lote.id,
            ))
        if (
            lote.campania_id == camp_map[current_campaign_name].id
            and lote.cultivo_id in {
                cult_map["Soja"].id,
                cult_map["Maiz"].id,
                cult_map["Girasol"].id,
            }
        ):
            extra_herb_date = lote.fecha_siembra + timedelta(days=75)
            if roundup and extra_herb_date <= today:
                qty_extra = lote.hectareas * 1.25
                movimientos.append(MovimientoInsumo(
                    establecimiento_id=lote.establecimiento_id,
                    insumo_id=roundup.id,
                    tipo="egreso",
                    cantidad=qty_extra,
                    fecha=extra_herb_date,
                    costo_total=qty_extra * roundup.precio_unitario,
                    lote_id=lote.id,
                ))
            if urea and lote.cultivo_id == cult_map["Maiz"].id:
                extra_fert_date = lote.fecha_siembra + timedelta(days=52)
                if extra_fert_date <= today:
                    qty_extra_fert = lote.hectareas * 0.06
                    movimientos.append(MovimientoInsumo(
                        establecimiento_id=lote.establecimiento_id,
                        insumo_id=urea.id,
                        tipo="egreso",
                        cantidad=qty_extra_fert,
                        fecha=extra_fert_date,
                        costo_total=qty_extra_fert * urea.precio_unitario,
                        lote_id=lote.id,
                    ))

    # Ingresos de insumos (compras)
    for est in ests[:4]:
        if gas_oil:
            movimientos.append(MovimientoInsumo(
                establecimiento_id=est.id,
                insumo_id=gas_oil.id,
                tipo="ingreso",
                cantidad=5000,
                fecha=shift_date_years(date(2024, 10, 1), year_delta),
                costo_total=5000 * gas_oil.precio_unitario,
                lote_id=None,
            ))
        if urea:
            movimientos.append(MovimientoInsumo(
                establecimiento_id=est.id,
                insumo_id=urea.id,
                tipo="ingreso",
                cantidad=50,  # 50 tn
                fecha=shift_date_years(date(2024, 9, 15), year_delta),
                costo_total=50 * urea.precio_unitario,
                lote_id=None,
            ))

    db.add_all(movimientos)
    await db.flush()
