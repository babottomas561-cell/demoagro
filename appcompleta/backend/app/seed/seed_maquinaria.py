from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta

from app.models.empresa import Empresa
from app.models.establecimiento import Establecimiento
from app.models.maquinaria import Maquinaria
from app.models.mantenimiento import Mantenimiento
from app.seed.campaign_utils import build_campaign_template_map, shift_date_years


async def seed_maquinaria(db: AsyncSession):
    empresas = (await db.execute(select(Empresa))).scalars().all()
    ests = (await db.execute(select(Establecimiento))).scalars().all()

    emp_map = {e.nombre: e for e in empresas}
    est_map = {e.nombre: e for e in ests}

    emp1 = emp_map["El Progreso SA"]
    emp2 = emp_map["Agropecuaria Del Sur SRL"]
    _, year_delta = build_campaign_template_map(date.today())

    # Establecimientos por empresa
    ests_e1 = [e for e in ests if e.empresa_id == emp1.id]
    ests_e2 = [e for e in ests if e.empresa_id == emp2.id]

    maquinas_data = [
        # Empresa 1 - El Progreso SA
        (ests_e1[0], "tractor", "John Deere", "8R 310", 2020, 3200, "operativo"),
        (ests_e1[0], "cosechadora", "John Deere", "S780", 2021, 1850, "operativo"),
        (ests_e1[0], "sembradora", "Bertini", "Air Max 6200", 2019, 4100, "operativo"),
        (ests_e1[0], "pulverizadora", "Metalfor", "Araus 4150", 2022, 980, "operativo"),
        (ests_e1[1], "tractor", "New Holland", "T8.380", 2018, 5800, "operativo"),
        (ests_e1[1], "cosechadora", "Case IH", "Axial Flow 8250", 2020, 2400, "operativo"),
        (ests_e1[1], "sembradora", "Agrometal", "TX Mega 36", 2021, 2850, "operativo"),
        (ests_e1[1], "pulverizadora", "Jacto", "Uniport 4030", 2019, 1680, "mantenimiento"),
        (ests_e1[2], "tractor", "Deutz-Fahr", "9290 TTV", 2017, 7200, "operativo"),
        (ests_e1[2], "cosechadora", "New Holland", "CR 9090", 2019, 3150, "operativo"),
        (ests_e1[3], "tractor", "John Deere", "6195M", 2021, 2100, "operativo"),
        (ests_e1[3], "sembradora", "Crucianelli", "Altina 5800", 2020, 3400, "operativo"),
        # Empresa 2 - Agropecuaria Del Sur SRL
        (ests_e2[0], "tractor", "Case IH", "Puma 185 CVX", 2019, 4500, "operativo"),
        (ests_e2[0], "cosechadora", "CLAAS", "LEXION 760", 2022, 1200, "operativo"),
        (ests_e2[0], "sembradora", "Agrometal", "MX Exacta 32", 2020, 3800, "operativo"),
        (ests_e2[0], "pulverizadora", "Metalfor", "2400 TF", 2021, 1450, "operativo"),
        (ests_e2[1], "tractor", "Massey Ferguson", "8737S", 2018, 6100, "operativo"),
        (ests_e2[1], "cosechadora", "John Deere", "T670i", 2020, 2750, "operativo"),
        (ests_e2[2], "tractor", "New Holland", "T7.245", 2016, 9200, "baja"),
        (ests_e2[2], "cosechadora", "Case IH", "Axial Flow 7250", 2019, 3600, "operativo"),
        (ests_e2[2], "sembradora", "Bertini", "Air Max 5200", 2022, 1950, "operativo"),
        (ests_e2[3], "tractor", "John Deere", "6130M", 2020, 2800, "operativo"),
        (ests_e2[4], "tractor", "Deutz-Fahr", "6180 Agrotron", 2019, 4800, "operativo"),
        (ests_e2[4], "pulverizadora", "Jacto", "Condor Air Master 3030", 2021, 1100, "mantenimiento"),
    ]

    maquinas = []
    for est, tipo, marca, modelo, anio, horas, estado in maquinas_data:
        m = Maquinaria(
            establecimiento_id=est.id,
            tipo=tipo,
            marca=marca,
            modelo=modelo,
            anio=anio,
            horas_totales=horas,
            estado=estado,
        )
        maquinas.append(m)

    db.add_all(maquinas)
    await db.flush()

    # ---- Historial de Mantenimiento ----
    mantenimientos = []

    mantenimiento_data = [
        # John Deere 8R 310 - Tractor (3200 hs)
        (maquinas[0], "preventivo", date(2023, 3, 15), "Service 500 hs - cambio aceite motor y filtros", 185000, 500, 1000),
        (maquinas[0], "preventivo", date(2023, 9, 20), "Service 1000 hs - filtros, correas, liquido frenos", 320000, 1000, 1500),
        (maquinas[0], "preventivo", date(2024, 4, 10), "Service 1500 hs - revision completa", 450000, 1500, 2000),
        (maquinas[0], "correctivo", date(2024, 8, 5), "Reparacion sistema hidraulico - reemplazo bomba", 1200000, 3100, 3600),
        # John Deere S780 - Cosechadora (1850 hs)
        (maquinas[1], "preventivo", date(2022, 12, 1), "Pre-cosecha - revision general trilladero", 580000, 800, 1300),
        (maquinas[1], "preventivo", date(2023, 11, 28), "Pre-cosecha 2023/24 - ajuste cabezal maiz", 620000, 1400, 1900),
        (maquinas[1], "correctivo", date(2024, 2, 14), "Rotura chaveta sinfin - reemplazo en cosecha", 380000, 1780, 2300),
        # Sembradora Bertini Air Max (4100 hs)
        (maquinas[2], "preventivo", date(2023, 8, 10), "Pre-siembra - calibracion dosificadores", 95000, 2800, 3300),
        (maquinas[2], "preventivo", date(2024, 8, 5), "Pre-siembra 2024/25 - revision discos y mangueras", 110000, 4050, 4550),
        # Pulverizadora Metalfor (980 hs)
        (maquinas[3], "preventivo", date(2023, 10, 5), "Service anual - picos, boquillas, bomba", 145000, 500, 1000),
        (maquinas[3], "preventivo", date(2024, 9, 12), "Service pre-campana - revision completa", 165000, 930, 1430),
        # New Holland T8.380 (5800 hs)
        (maquinas[4], "preventivo", date(2022, 6, 15), "Service 4000 hs", 380000, 4000, 4500),
        (maquinas[4], "preventivo", date(2023, 2, 20), "Service 4500 hs - transmision", 520000, 4500, 5000),
        (maquinas[4], "correctivo", date(2023, 8, 18), "Falla turbo - reemplazo turbocompresor", 1850000, 5200, 5700),
        (maquinas[4], "preventivo", date(2024, 1, 10), "Service 5000 hs - revision completa", 490000, 5000, 5500),
        # Case IH Axial Flow 8250 (2400 hs)
        (maquinas[5], "preventivo", date(2022, 11, 25), "Pre-cosecha soja 2022/23", 560000, 1000, 1500),
        (maquinas[5], "preventivo", date(2023, 11, 20), "Pre-cosecha 2023/24 - banda trilladero", 640000, 1800, 2300),
        # Pulverizadora Jacto (en mantenimiento - 1680 hs)
        (maquinas[7], "preventivo", date(2024, 3, 5), "Service anual - revision bomba hidraulica", 285000, 1500, 2000),
        (maquinas[7], "correctivo", date(2024, 10, 18), "Falla sistema GPS - en reparacion en taller", 950000, 1680, 2180),
        # Deutz-Fahr 9290 TTV (7200 hs)
        (maquinas[8], "preventivo", date(2022, 4, 12), "Service 5000 hs", 420000, 5000, 5500),
        (maquinas[8], "preventivo", date(2023, 3, 25), "Service 6000 hs - cambio correas distribucion", 680000, 6000, 6500),
        (maquinas[8], "correctivo", date(2023, 11, 8), "Reparacion caja de cambios", 2800000, 6800, 7300),
        (maquinas[8], "preventivo", date(2024, 5, 30), "Service 7000 hs - motor y transmision", 850000, 7000, 7500),
        # Case IH Puma 185 (4500 hs) - Empresa 2
        (maquinas[12], "preventivo", date(2022, 8, 20), "Service 3000 hs", 350000, 3000, 3500),
        (maquinas[12], "preventivo", date(2023, 6, 15), "Service 3500 hs - filtros, aceite, frenos", 420000, 3500, 4000),
        (maquinas[12], "preventivo", date(2024, 2, 28), "Service 4000 hs - revision completa", 510000, 4000, 4500),
        # CLAAS LEXION 760 (1200 hs)
        (maquinas[13], "preventivo", date(2023, 11, 28), "Pre-cosecha 2023/24 - primer service", 680000, 800, 1300),
        (maquinas[13], "preventivo", date(2024, 11, 15), "Pre-cosecha 2024/25 - ajuste sistems trilladero", 720000, 1150, 1650),
        # New Holland T7.245 (9200 hs - baja)
        (maquinas[18], "correctivo", date(2024, 6, 10), "Motor fundido - no rentable reparar, dado de baja", 0, 9200, None),
        # Pulverizadora Jacto Condor (en mantenimiento - 1100 hs)
        (maquinas[23], "correctivo", date(2024, 11, 5), "Reparacion bomba principal - en taller", 1200000, 1100, 1600),
        # John Deere 6195M (2100 hs)
        (maquinas[10], "preventivo", date(2023, 10, 18), "Service 1500 hs", 280000, 1500, 2000),
        (maquinas[10], "preventivo", date(2024, 9, 22), "Service 2000 hs", 310000, 2000, 2500),
        # Actividad reciente para campaña en curso
        (maquinas[1], "preventivo", date(2025, 1, 18), "Post-trigo - revision sacapajas y zarandas", 540000, 1820, 2320),
        (maquinas[5], "preventivo", date(2025, 2, 25), "Pre-maiz temprano - revision cabezal", 610000, 2360, 2860),
        (maquinas[3], "correctivo", date(2025, 3, 4), "Cambio de bomba de pulverizacion y calibracion", 420000, 970, 1470),
        (maquinas[13], "preventivo", date(2025, 2, 10), "Ajuste pre-cosecha maiz", 590000, 1180, 1680),
        (maquinas[20], "preventivo", date(2025, 3, 6), "Revision de tren de siembra y telemetria", 235000, 1935, 2435),
    ]

    for maq, tipo, fecha, desc, costo, horas_maq, prox_hs in mantenimiento_data:
        m = Mantenimiento(
            maquinaria_id=maq.id,
            tipo=tipo,
            fecha=shift_date_years(fecha, year_delta),
            descripcion=desc,
            costo=float(costo),
            horas_maquina=float(horas_maq),
            proximo_service_hs=float(prox_hs) if prox_hs else None,
        )
        mantenimientos.append(m)

    db.add_all(mantenimientos)
    await db.flush()
