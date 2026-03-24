"""
Seed ERP v2: datos abundantes y coherentes para DemoAgro.
Usa random.seed(42) para determinismo.
"""
import random
import logging
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.empresa import Empresa
from app.models.establecimiento import Establecimiento
from app.models.campania import Campania
from app.models.cultivo import Cultivo
from app.models.cliente import Cliente
from app.models.proveedor import Proveedor
from app.models.lote import Lote
from app.models.siembra import Siembra
from app.models.cosecha_v2 import CosechaV2
from app.models.aplicacion import Aplicacion
from app.models.silo import Silo, StockActualV2, MovimientoStockV2
from app.models.comercial_v2 import VentaV2, ContratoV2, RemitoCampo
from app.models.financiero import CuentaCorriente, FlujoCajaV2, Presupuesto
from app.models.maquinaria_v2 import MaquinariaV2, OrdenTrabajo, MantenimientoV2
from app.models.insumo_v2 import InsumoV2, OrdenCompraInsumo, ItemOrdenCompraInsumo, MovimientoInsumoV2
from app.seed.campaign_utils import build_campaign_template_map, shift_date_years

logger = logging.getLogger(__name__)

rng = random.Random(42)


def rv(low, high, decimals=2):
    """Valor aleatorio deterministico en [low, high]."""
    return round(rng.uniform(low, high), decimals)


def ri(low, high):
    """Entero aleatorio deterministico en [low, high]."""
    return rng.randint(low, high)


def rc(lst):
    """Elección aleatoria deterministico de lista."""
    return rng.choice(lst)


# Precios USD/tn por cultivo y campaña
PRECIOS_USD = {
    "Soja":    {"2022/2023": (250, 280), "2023/2024": (265, 290), "2024/2025": (255, 285)},
    "Maiz":    {"2022/2023": (145, 165), "2023/2024": (155, 175), "2024/2025": (145, 168)},
    "Trigo":   {"2022/2023": (185, 215), "2023/2024": (195, 220), "2024/2025": (185, 215)},
    "Girasol": {"2022/2023": (310, 350), "2023/2024": (330, 360), "2024/2025": (320, 355)},
    "Sorgo":   {"2022/2023": (100, 125), "2023/2024": (110, 135), "2024/2025": (105, 130)},
}

# Tipo de cambio ARS/USD por campaña (promedio)
TC_CAMP = {
    "2022/2023": (200, 350),
    "2023/2024": (500, 950),
    "2024/2025": (900, 1100),
}

# Rendimientos tn/ha por cultivo
RENDIMIENTOS = {
    "Soja":    (3.2, 3.8),
    "Maiz":    (8.5, 10.5),
    "Trigo":   (3.5, 4.5),
    "Girasol": (2.0, 2.8),
    "Sorgo":   (6.5, 8.5),
}

# Costos USD/ha por cultivo
COSTOS_USD_HA = {
    "Soja":    (500, 650),
    "Maiz":    (700, 900),
    "Trigo":   (450, 600),
    "Girasol": (520, 680),
    "Sorgo":   (400, 550),
}

CAMP_NOMBRES_TEMPLATE = ["2022/2023", "2023/2024", "2024/2025"]


def get_camp_nombre_template(campania, camp_map_inv):
    """Retorna nombre template (ej: '2022/2023') dado el objeto Campania."""
    return camp_map_inv.get(campania.id, "2023/2024")


def tc(camp_nombre_template):
    lo, hi = TC_CAMP.get(camp_nombre_template, (800, 1000))
    return rv(lo, hi, 0)


def precio_usd(cultivo_nombre, camp_nombre_template):
    lo, hi = PRECIOS_USD.get(cultivo_nombre, {}).get(camp_nombre_template, (200, 280))
    return rv(lo, hi, 2)


def rendimiento(cultivo_nombre):
    lo, hi = RENDIMIENTOS.get(cultivo_nombre, (3.0, 5.0))
    return rv(lo, hi, 2)


async def seed_erp_v2(db: AsyncSession):
    """Carga datos abundantes en las tablas v2."""
    random.seed(42)

    # Fetch base data
    empresas = (await db.execute(select(Empresa))).scalars().all()
    ests = (await db.execute(select(Establecimiento))).scalars().all()
    campanias = (await db.execute(select(Campania).order_by(Campania.fecha_inicio))).scalars().all()
    cultivos = (await db.execute(select(Cultivo))).scalars().all()
    clientes = (await db.execute(select(Cliente))).scalars().all()
    proveedores = (await db.execute(select(Proveedor))).scalars().all()

    emp_map = {e.nombre: e for e in empresas}
    est_by_emp = {}
    for e in ests:
        est_by_emp.setdefault(e.empresa_id, []).append(e)

    camp_map = {c.nombre: c for c in campanias}
    cult_map = {c.nombre: c for c in cultivos}
    cli_list = clientes
    prov_list = proveedores

    emp1 = emp_map.get("El Progreso SA")
    emp2 = emp_map.get("Agropecuaria Del Sur SRL")

    campaign_name_map, year_delta = build_campaign_template_map(date.today())
    # Reverse map: campaña real -> template name
    camp_map_inv = {v_camp.id: k for k, v_camp in
                    {k: camp_map.get(v) for k, v in campaign_name_map.items() if camp_map.get(v)}.items()}

    # Seleccionar solo las 3 campañas de operación
    camp_templates = ["2022/2023", "2023/2024", "2024/2025"]
    camp_objs = [camp_map[campaign_name_map[t]] for t in camp_templates if campaign_name_map.get(t) in camp_map]

    # Seleccionar cultivos principales
    cult_siembra = ["Soja", "Maiz", "Trigo", "Girasol", "Sorgo"]
    cult_objs = {n: cult_map[n] for n in cult_siembra if n in cult_map}

    # ------------------------------------------------------------------ #
    # 1. SILOS
    # ------------------------------------------------------------------ #
    silos = []
    tipos_silo = ["chapa", "bolsa", "planchada"]
    for est in ests:
        n_silos = ri(2, 4)
        for i in range(n_silos):
            silo = Silo(
                establecimiento_id=est.id,
                nombre=f"Silo {i+1} - {est.nombre[:20]}",
                capacidad_tn=rv(800, 3000, 0),
                tipo=rc(tipos_silo),
            )
            silos.append(silo)
    db.add_all(silos)
    await db.flush()

    # ------------------------------------------------------------------ #
    # 2. CUENTAS CORRIENTES
    # ------------------------------------------------------------------ #
    bancos = ["Banco Nacion Argentina", "Banco Santander", "Banco Galicia", "BBVA Argentina"]
    cuentas = []
    for emp in [emp1, emp2]:
        if not emp:
            continue
        for banco in bancos[:2]:
            cuentas.append(CuentaCorriente(
                empresa_id=emp.id,
                banco=banco,
                nro_cuenta=f"{ri(10000, 99999)}-{ri(1, 9)}",
                tipo="corriente",
                moneda="ARS",
            ))
        cuentas.append(CuentaCorriente(
            empresa_id=emp.id,
            banco="Banco Nacion Argentina",
            nro_cuenta=f"USD-{ri(10000, 99999)}",
            tipo="caja_ahorro",
            moneda="USD",
        ))
    db.add_all(cuentas)
    await db.flush()

    cuenta_map = {c.empresa_id: c for c in cuentas if c.moneda == "ARS"}

    # ------------------------------------------------------------------ #
    # 3. INSUMOS V2
    # ------------------------------------------------------------------ #
    insumos_v2_data = [
        ("Roundup Max (Glifosato 75%)", "agroquimico", "kg", 4200, 5000),
        ("2,4-D Amina 72%", "agroquimico", "lt", 2100, 3000),
        ("Atrazina 90%", "agroquimico", "kg", 3200, 2000),
        ("Carbendazim + Tebuconazol", "agroquimico", "lt", 8500, 1500),
        ("Azoxistrobina + Ciproconazol", "agroquimico", "lt", 12000, 800),
        ("Clorpirifos 48%", "agroquimico", "lt", 5500, 1200),
        ("Urea Granulada 46%", "fertilizante", "tn", 520000, 200),
        ("MAP Monoamonio Fosfato", "fertilizante", "tn", 680000, 150),
        ("UAN Solucion 32%", "fertilizante", "lt", 280, 50000),
        ("Superfosfato Triple", "fertilizante", "tn", 590000, 120),
        ("Soja RR1 Intacta BMX Power", "semilla", "kg", 5200, 8000),
        ("Soja DM 50i20", "semilla", "kg", 4800, 6000),
        ("Maiz DK 7010 VT3P", "semilla", "bolsa", 48000, 300),
        ("Maiz P1564 MGRR2", "semilla", "bolsa", 52000, 250),
        ("Trigo Klein Liebre", "semilla", "kg", 1850, 10000),
        ("Trigo Buck Huyen", "semilla", "kg", 1950, 8000),
        ("Girasol Paraiso 20", "semilla", "bolsa", 36000, 200),
        ("Sorgo EM Pampa Hib.", "semilla", "bolsa", 22000, 150),
        ("Gas Oil S10", "combustible", "lt", 980, 80000),
        ("Gas Oil S500", "combustible", "lt", 920, 50000),
        ("Aceite Motor 15W40", "combustible", "lt", 4500, 2000),
    ]
    insumos_v2 = []
    for nombre, tipo, unidad, precio, stock_act in insumos_v2_data:
        insumos_v2.append(InsumoV2(
            nombre=nombre,
            tipo=tipo,
            unidad=unidad,
            precio_actual_ars=precio,
            stock_actual=stock_act,
        ))
    db.add_all(insumos_v2)
    await db.flush()

    # ------------------------------------------------------------------ #
    # 4. MAQUINARIA V2 (40+ equipos)
    # ------------------------------------------------------------------ #
    maquinas_v2_data = [
        # Empresa 1 - El Progreso SA
        ("tractor", "John Deere", "8R 310", 2020, "JD8R310-001", "operativa", 4500000, 3200),
        ("cosechadora", "John Deere", "S780", 2021, "JDS780-001", "operativa", 12000000, 1850),
        ("sembradora", "Bertini", "Air Max 6200", 2019, "BER6200-001", "operativa", 2800000, 4100),
        ("pulverizadora", "Metalfor", "Araus 4150", 2022, "MET4150-001", "operativa", 5500000, 980),
        ("tractor", "New Holland", "T8.380", 2018, "NH8380-001", "operativa", 3800000, 5800),
        ("cosechadora", "Case IH", "Axial Flow 8250", 2020, "CIHAF8250-001", "operativa", 11000000, 2400),
        ("sembradora", "Agrometal", "TX Mega 36", 2021, "AGR36-001", "operativa", 3200000, 2850),
        ("pulverizadora", "Jacto", "Uniport 4030", 2019, "JAC4030-001", "mantenimiento", 4200000, 1680),
        ("tractor", "Deutz-Fahr", "9290 TTV", 2017, "DT9290-001", "operativa", 3200000, 7200),
        ("cosechadora", "New Holland", "CR 9090", 2019, "NHCR9090-001", "operativa", 10500000, 3150),
        ("tractor", "John Deere", "6195M", 2021, "JD6195-001", "operativa", 3500000, 2100),
        ("sembradora", "Crucianelli", "Altina 5800", 2020, "CRU5800-001", "operativa", 2600000, 3400),
        ("tolva", "Mainero", "2028 SD", 2021, "MAIN2028-001", "operativa", 1800000, 0),
        ("tractor", "Massey Ferguson", "7720S", 2022, "MF7720-001", "operativa", 4200000, 1100),
        ("secadora", "Bühler", "LAD-2000", 2020, "BUH2000-001", "operativa", 8500000, 2200),
        ("tanque", "Metalfor", "TQC 10000", 2021, "METTQC-001", "operativa", 850000, 0),
        ("tractor", "Case IH", "Optum 300 CVX", 2023, "CIHOPT300-001", "operativa", 5800000, 350),
        ("pulverizadora", "Metalfor", "4550 NG", 2023, "MET4550-001", "operativa", 6200000, 280),
        # Empresa 2 - Agropecuaria Del Sur SRL
        ("tractor", "Case IH", "Puma 185 CVX", 2019, "CIHPUMA-001", "operativa", 3600000, 4500),
        ("cosechadora", "CLAAS", "LEXION 760", 2022, "CLLEX760-001", "operativa", 13000000, 1200),
        ("sembradora", "Agrometal", "MX Exacta 32", 2020, "AGRMX32-001", "operativa", 3100000, 3800),
        ("pulverizadora", "Metalfor", "2400 TF", 2021, "MET2400-001", "operativa", 4800000, 1450),
        ("tractor", "Massey Ferguson", "8737S", 2018, "MF8737-001", "operativa", 3500000, 6100),
        ("cosechadora", "John Deere", "T670i", 2020, "JDT670-001", "operativa", 9800000, 2750),
        ("tractor", "New Holland", "T7.245", 2016, "NHT7245-001", "baja", 1200000, 9200),
        ("cosechadora", "Case IH", "Axial Flow 7250", 2019, "CIHAF7250-001", "operativa", 9500000, 3600),
        ("sembradora", "Bertini", "Air Max 5200", 2022, "BER5200-001", "operativa", 2900000, 1950),
        ("tractor", "John Deere", "6130M", 2020, "JD6130-001", "operativa", 2900000, 2800),
        ("tractor", "Deutz-Fahr", "6180 Agrotron", 2019, "DT6180-001", "operativa", 2700000, 4800),
        ("pulverizadora", "Jacto", "Condor Air Master 3030", 2021, "JACCAM-001", "mantenimiento", 3900000, 1100),
        ("tolva", "Mainero", "2039 SD", 2020, "MAIN2039-001", "operativa", 1600000, 0),
        ("sembradora", "Crucianelli", "Elite 5600", 2021, "CRUELITE-001", "operativa", 2800000, 2200),
        ("tractor", "New Holland", "T6.175", 2022, "NHT6175-001", "operativa", 3200000, 890),
        ("cosechadora", "John Deere", "S760", 2023, "JDS760-001", "operativa", 13500000, 320),
        ("tractor", "John Deere", "7230R", 2021, "JD7230-001", "operativa", 4100000, 1850),
        ("pulverizadora", "Pla", "2025 HC", 2022, "PLA2025-001", "operativa", 4500000, 620),
        ("secadora", "Bühler", "LAD-1500", 2019, "BUH1500-001", "operativa", 6500000, 3100),
        ("tanque", "Metalfor", "TQC 8000", 2020, "METTQC8-001", "operativa", 720000, 0),
        ("tractor", "Massey Ferguson", "6718S", 2023, "MF6718-001", "operativa", 3100000, 250),
        ("sembradora", "Agrometal", "TX 46", 2023, "AGRTX46-001", "operativa", 3800000, 180),
    ]

    emp_ests_e1 = [e for e in ests if e.empresa_id == emp1.id] if emp1 else []
    emp_ests_e2 = [e for e in ests if e.empresa_id == emp2.id] if emp2 else []

    maquinas_v2 = []
    for i, (tipo, marca, modelo, anio, serie, estado, valor, horas) in enumerate(maquinas_v2_data):
        # Asignar a empresa 1 los primeros 18, empresa 2 el resto
        if i < 18:
            emp = emp1
            est_list = emp_ests_e1
        else:
            emp = emp2
            est_list = emp_ests_e2
        if not emp or not est_list:
            continue
        m = MaquinariaV2(
            empresa_id=emp.id,
            tipo=tipo,
            marca=marca,
            modelo=modelo,
            anio=anio,
            patente_o_serie=serie,
            estado=estado,
            valor_libro_ars=float(valor),
            horas_motor=float(horas),
        )
        maquinas_v2.append(m)
    db.add_all(maquinas_v2)
    await db.flush()

    # ------------------------------------------------------------------ #
    # 5. SIEMBRAS V2 (200+ siembras)
    # ------------------------------------------------------------------ #
    lotes = (await db.execute(select(Lote))).scalars().all()
    # Filtrar lotes que tengan campaña y cultivo
    lotes_validos = [l for l in lotes if l.campania_id and l.cultivo_id and l.fecha_siembra]

    hibridos = {
        "Soja": ["BMX Power RR", "DM 50i20 IPRO", "NS 5258 IPRO", "SY 3x1 IPRO", "A 8000 RG"],
        "Maiz": ["DK 7010 VT3P", "P1564 MGRR2", "AX 882 MG RR2", "NK Plateau VT3P", "30F53 YR"],
        "Trigo": ["Klein Liebre", "Buck Huyen", "ACA 303", "Bio INTA Prelat", "SY 200"],
        "Girasol": ["Paraiso 20", "Conti 201 CL", "DK 4045 CL", "SY 3840 HO", "Heliasol CL"],
        "Sorgo": ["EM Pampa", "Nutriplus 82", "Agri H250", "Advanta 9807", "Pioneer 82G80"],
    }
    densidades = {
        "Soja": (20, 28),
        "Maiz": (75000, 95000),
        "Trigo": (200, 300),
        "Girasol": (55000, 70000),
        "Sorgo": (150000, 200000),
    }

    siembras = []
    siembras_by_lote_camp = {}
    for lote in lotes_validos:
        # Solo crear siembra si no hay duplicado lote+campaña
        key = (lote.id, lote.campania_id)
        if key in siembras_by_lote_camp:
            continue
        cult_nombre = next((c.nombre for c in cultivos if c.id == lote.cultivo_id), None)
        if not cult_nombre:
            continue
        hibs = hibridos.get(cult_nombre, ["Variedad estándar"])
        dens_lo, dens_hi = densidades.get(cult_nombre, (20, 30))
        siembra = Siembra(
            lote_id=lote.id,
            campania_id=lote.campania_id,
            cultivo_id=lote.cultivo_id,
            fecha=lote.fecha_siembra,
            ha_sembradas=lote.hectareas,
            densidad=rv(dens_lo, dens_hi, 0),
            hibrido=rc(hibs),
            observaciones=f"Siembra campaña - condición suelo {rc(['buena', 'regular', 'muy buena'])}",
        )
        siembras.append(siembra)
        siembras_by_lote_camp[key] = siembra

    db.add_all(siembras)
    await db.flush()

    # ------------------------------------------------------------------ #
    # 6. COSECHAS V2 (150+ cosechas)
    # ------------------------------------------------------------------ #
    cosechas_v2 = []
    for siembra in siembras:
        lote = next((l for l in lotes if l.id == siembra.lote_id), None)
        if not lote or lote.estado != "cosechado" or not lote.fecha_cosecha:
            continue
        cult_nombre = next((c.nombre for c in cultivos if c.id == siembra.cultivo_id), None)
        if not cult_nombre:
            continue
        camp_nombre_tpl = camp_map_inv.get(siembra.campania_id, "2023/2024")
        rend = rendimiento(cult_nombre)
        p_usd = precio_usd(cult_nombre, camp_nombre_tpl)
        t_c = tc(camp_nombre_tpl)
        valor_tot = round(siembra.ha_sembradas * rend * p_usd * t_c, 2)
        cosecha = CosechaV2(
            siembra_id=siembra.id,
            fecha=lote.fecha_cosecha,
            ha_cosechadas=siembra.ha_sembradas,
            rendimiento_tn_ha=rend,
            humedad=rv(12.5, 16.5, 1),
            calidad=rc(["buena", "buena", "buena", "regular"]),
            precio_mercado=p_usd,
            valor_total=valor_tot,
        )
        cosechas_v2.append(cosecha)
    db.add_all(cosechas_v2)
    await db.flush()

    # ------------------------------------------------------------------ #
    # 7. APLICACIONES (herbicidas, fungicidas, etc.)
    # ------------------------------------------------------------------ #
    aplicaciones = []
    tipos_aplic = [
        ("herbicida", "Roundup Max", 3.0, "lt/ha"),
        ("herbicida", "2,4-D Amina 72%", 1.5, "lt/ha"),
        ("fungicida", "Carbendazim + Tebuconazol", 0.6, "lt/ha"),
        ("fungicida", "Azoxistrobina + Ciproconazol", 0.5, "lt/ha"),
        ("insecticida", "Clorpirifos 48%", 0.8, "lt/ha"),
        ("fertilizante", "Urea Granulada", 120, "kg/ha"),
        ("fertilizante", "MAP Monoamonio Fosfato", 80, "kg/ha"),
    ]
    for siembra in siembras:
        lote = next((l for l in lotes if l.id == siembra.lote_id), None)
        if not lote:
            continue
        # 2-3 aplicaciones por siembra
        n_aplic = ri(2, 3)
        for j in range(n_aplic):
            tipo_aplic, prod_aplic, dosis_base, unidad_aplic = rc(tipos_aplic)
            fecha_aplic = siembra.fecha + timedelta(days=ri(10, 80))
            tc_val = tc(camp_map_inv.get(siembra.campania_id, "2023/2024"))
            costo = round(siembra.ha_sembradas * dosis_base * rv(0.8, 1.2, 2) * rv(1000, 3000, 0) / 1000, 2)
            aplicaciones.append(Aplicacion(
                lote_id=siembra.lote_id,
                campania_id=siembra.campania_id,
                tipo=tipo_aplic,
                fecha=fecha_aplic,
                producto=prod_aplic,
                dosis=round(dosis_base * rv(0.9, 1.1, 2), 2),
                unidad=unidad_aplic,
                ha_aplicadas=siembra.ha_sembradas,
                costo_total=costo,
            ))
    db.add_all(aplicaciones)
    await db.flush()

    # ------------------------------------------------------------------ #
    # 8. CONTRATOS V2 (60+ contratos)
    # ------------------------------------------------------------------ #
    contratos_v2 = []
    tipos_contrato = ["forward", "disponible", "disponible", "canje"]
    estados_contrato = ["pendiente", "parcial", "cumplido", "cumplido", "cumplido"]

    for emp in [emp1, emp2]:
        if not emp:
            continue
        for camp in camp_objs:
            camp_tpl = camp_map_inv.get(camp.id, "2023/2024")
            # 10 contratos por empresa por campaña
            for _ in range(10):
                cult_nombre = rc(list(cult_objs.keys()))
                cult = cult_objs[cult_nombre]
                cli = rc(cli_list)
                cantidad = rv(200, 2000, 0)
                p_usd = precio_usd(cult_nombre, camp_tpl)
                t_c = tc(camp_tpl)
                estado = rc(estados_contrato)
                if camp_tpl == "2024/2025":
                    estado = rc(["pendiente", "pendiente", "parcial"])
                elif camp_tpl == "2022/2023":
                    estado = "cumplido"
                tipo_c = rc(tipos_contrato)
                dias_firma = ri(0, 180)
                fecha_firma = camp.fecha_inicio + timedelta(days=dias_firma)
                fecha_entrega = fecha_firma + timedelta(days=ri(30, 180))
                contratos_v2.append(ContratoV2(
                    empresa_id=emp.id,
                    campania_id=camp.id,
                    cultivo_id=cult.id,
                    cliente_id=cli.id,
                    tipo=tipo_c,
                    cantidad_tn=cantidad,
                    precio_usd=p_usd,
                    precio_ars=round(p_usd * t_c, 2),
                    fecha_firma=shift_date_years(fecha_firma, year_delta),
                    fecha_entrega=shift_date_years(fecha_entrega, year_delta),
                    estado=estado,
                ))
    db.add_all(contratos_v2)
    await db.flush()

    # ------------------------------------------------------------------ #
    # 9. VENTAS V2 (400+ ventas)
    # ------------------------------------------------------------------ #
    ventas_v2 = []
    remitos = []
    condiciones_pago = ["contado", "contado", "credito", "canje"]

    for emp in [emp1, emp2]:
        if not emp:
            continue
        for camp in camp_objs:
            camp_tpl = camp_map_inv.get(camp.id, "2023/2024")
            n_ventas = 65 if emp.nombre == "El Progreso SA" else 50
            for vi in range(n_ventas):
                cult_nombre = rc(list(cult_objs.keys()))
                cult = cult_objs[cult_nombre]
                cli = rc(cli_list)
                p_usd = precio_usd(cult_nombre, camp_tpl)
                t_c = tc(camp_tpl)
                p_ars = round(p_usd * t_c, 2)
                cantidad = rv(50, 600, 0)
                importe = round(cantidad * p_ars, 2)
                # Fecha dentro de campaña
                dias_desde_inicio = ri(30, 340)
                fecha_venta = camp.fecha_inicio + timedelta(days=dias_desde_inicio)
                fecha_venta_real = shift_date_years(fecha_venta, year_delta)
                # Elegir contrato relacionado (optional)
                contrato_rel = None
                contratos_camp = [c for c in contratos_v2 if
                                   c.empresa_id == emp.id and c.campania_id == camp.id and
                                   c.cultivo_id == cult.id]
                if contratos_camp and rng.random() < 0.5:
                    contrato_rel = rc(contratos_camp)

                venta = VentaV2(
                    empresa_id=emp.id,
                    campania_id=camp.id,
                    cultivo_id=cult.id,
                    cliente_id=cli.id,
                    contrato_id=contrato_rel.id if contrato_rel else None,
                    fecha=fecha_venta_real,
                    cantidad_tn=cantidad,
                    precio_ars_tn=p_ars,
                    precio_usd_tn=p_usd,
                    importe_total_ars=importe,
                    tipo_cambio=t_c,
                    condicion_pago=rc(condiciones_pago),
                )
                ventas_v2.append(venta)
    db.add_all(ventas_v2)
    await db.flush()

    # Remitos para ~40% de las ventas
    for venta in ventas_v2:
        if rng.random() < 0.4:
            remitos.append(RemitoCampo(
                venta_id=venta.id,
                fecha=venta.fecha,
                cantidad_tn=venta.cantidad_tn,
                chofer=f"Juan {rc(['Martinez', 'Gonzalez', 'Lopez', 'Perez', 'Rodriguez'])}",
                patente=f"{rc(['AB', 'CD', 'EF', 'GH'])}{ri(100, 999)}{rc(['AB', 'CD', 'EF'])}",
                destino=rc(["Puerto Rosario", "Acopio Venado Tuerto", "Planta Junin", "Puerto Quequen"]),
            ))
    db.add_all(remitos)
    await db.flush()

    # ------------------------------------------------------------------ #
    # 10. STOCK ACTUAL V2
    # ------------------------------------------------------------------ #
    stock_v2 = []
    mov_stock = []
    silos_by_est = {}
    for s in silos:
        silos_by_est.setdefault(s.establecimiento_id, []).append(s)

    for est in ests:
        est_silos = silos_by_est.get(est.id, [])
        for cult_nombre, cult in cult_objs.items():
            if rng.random() < 0.4:
                continue  # No todas las combinaciones tienen stock
            silo = rc(est_silos) if est_silos else None
            camp = rc(camp_objs)
            tn_disp = rv(50, 500, 0)
            tn_comp = rv(20, min(300, tn_disp * 0.6), 0)
            stock_v2.append(StockActualV2(
                establecimiento_id=est.id,
                cultivo_id=cult.id,
                silo_id=silo.id if silo else None,
                campania_id=camp.id,
                tn_disponibles=tn_disp,
                tn_comprometidas=tn_comp,
                calidad=rc(["buena", "buena", "regular"]),
                humedad=rv(12, 15, 1),
            ))

    db.add_all(stock_v2)
    await db.flush()

    # Movimientos de stock (150+ registros)
    for emp in [emp1, emp2]:
        if not emp:
            continue
        emp_ests = [e for e in ests if e.empresa_id == emp.id]
        for camp in camp_objs:
            camp_tpl = camp_map_inv.get(camp.id, "2023/2024")
            for ci in range(25):
                est = rc(emp_ests)
                cult = rc(list(cult_objs.values()))
                tipo_mov = rc(["ingreso", "ingreso", "egreso", "transferencia"])
                fecha_mov = camp.fecha_inicio + timedelta(days=ri(30, 300))
                mov_stock.append(MovimientoStockV2(
                    establecimiento_id=est.id,
                    cultivo_id=cult.id,
                    tipo=tipo_mov,
                    fecha=shift_date_years(fecha_mov, year_delta),
                    cantidad_tn=rv(30, 400, 0),
                    origen="Cosecha campo" if tipo_mov == "ingreso" else None,
                    destino="Puerto Rosario" if tipo_mov == "egreso" else None,
                    observaciones=f"Mov. {tipo_mov} campaña {camp.nombre}",
                ))
    db.add_all(mov_stock)
    await db.flush()

    # ------------------------------------------------------------------ #
    # 11. FLUJO DE CAJA V2 (500+ movimientos)
    # ------------------------------------------------------------------ #
    flujos_v2 = []
    categorias_ing = ["venta", "venta", "venta", "credito", "otro"]
    categorias_eg = ["insumos", "insumos", "labores", "salarios", "alquiler", "impuesto", "maquinaria"]
    subcats_ing = {
        "venta": ["soja", "maiz", "trigo", "girasol", "sorgo"],
        "credito": ["BNA", "Galicia", "Santander"],
        "otro": ["anticipo", "recupero"],
    }
    subcats_eg = {
        "insumos": ["semillas", "herbicidas", "fertilizantes", "fungicidas", "combustible"],
        "labores": ["siembra", "fumigacion", "cosecha", "labranza"],
        "salarios": ["sueldos", "aguinaldo", "cargas_sociales"],
        "alquiler": ["campo", "maquinaria"],
        "impuesto": ["iibb", "ganancias", "iva", "bienes_personales"],
        "maquinaria": ["mantenimiento", "repuestos", "servicio"],
    }

    for emp in [emp1, emp2]:
        if not emp:
            continue
        cuenta = cuenta_map.get(emp.id)
        emp_ests = [e for e in ests if e.empresa_id == emp.id]
        scale = 1.0 if emp.nombre == "El Progreso SA" else 0.65

        for camp in camp_objs:
            camp_tpl = camp_map_inv.get(camp.id, "2023/2024")
            t_c_avg = rv(*TC_CAMP.get(camp_tpl, (800, 1000)), 0)
            # Egresos mensuales (12 meses por campaña)
            for mes_offset in range(12):
                fecha_mes = camp.fecha_inicio + timedelta(days=mes_offset * 30 + ri(1, 20))
                fecha_real = shift_date_years(fecha_mes, year_delta)
                # 2-4 egresos por mes
                for _ in range(ri(2, 4)):
                    cat_eg = rc(categorias_eg)
                    subcat_eg = rc(subcats_eg.get(cat_eg, ["general"]))
                    monto_base = {
                        "insumos": rv(15000000, 80000000, 0),
                        "labores": rv(10000000, 60000000, 0),
                        "salarios": rv(12000000, 28000000, 0),
                        "alquiler": rv(8000000, 20000000, 0),
                        "impuesto": rv(5000000, 25000000, 0),
                        "maquinaria": rv(2000000, 15000000, 0),
                    }.get(cat_eg, rv(5000000, 20000000, 0))
                    monto = round(monto_base * scale, 2)
                    flujos_v2.append(FlujoCajaV2(
                        empresa_id=emp.id,
                        fecha=fecha_real,
                        tipo="egreso",
                        categoria=cat_eg,
                        subcategoria=subcat_eg,
                        importe_ars=monto,
                        importe_usd=round(monto / t_c_avg, 2),
                        tipo_cambio=t_c_avg,
                        descripcion=f"{cat_eg.title()} - {subcat_eg} campaña {camp.nombre}",
                        referencia_tipo="labor" if cat_eg == "labores" else "compra",
                        cuenta_id=cuenta.id if cuenta else None,
                        campania_id=camp.id,
                    ))
                # 1-2 ingresos por mes (concentrados en cosecha)
                if mes_offset in [4, 5, 6, 9, 10, 11]:  # meses de cosecha/venta
                    n_ing = ri(1, 3)
                else:
                    n_ing = ri(0, 1)
                for _ in range(n_ing):
                    cat_ing = rc(categorias_ing)
                    subcat_ing = rc(subcats_ing.get(cat_ing, ["general"]))
                    if cat_ing == "venta":
                        cult_nombre = rc(list(cult_objs.keys()))
                        p_usd = precio_usd(cult_nombre, camp_tpl)
                        tn_vendidas = rv(200, 800, 0)
                        monto = round(tn_vendidas * p_usd * t_c_avg * scale, 2)
                        desc = f"Venta {cult_nombre} - {rc(['Bunge', 'Cargill', 'LDC', 'Vicentin', 'AGD'])}"
                    else:
                        monto = round(rv(30000000, 120000000, 0) * scale, 2)
                        desc = f"{cat_ing.title()} - {subcat_ing}"
                    flujos_v2.append(FlujoCajaV2(
                        empresa_id=emp.id,
                        fecha=fecha_real,
                        tipo="ingreso",
                        categoria=cat_ing,
                        subcategoria=subcat_ing,
                        importe_ars=monto,
                        importe_usd=round(monto / t_c_avg, 2),
                        tipo_cambio=t_c_avg,
                        descripcion=desc,
                        referencia_tipo="venta" if cat_ing == "venta" else None,
                        cuenta_id=cuenta.id if cuenta else None,
                        campania_id=camp.id,
                    ))
    db.add_all(flujos_v2)
    await db.flush()

    # ------------------------------------------------------------------ #
    # 12. PRESUPUESTOS
    # ------------------------------------------------------------------ #
    presupuestos = []
    cats_pres = ["insumos", "labores", "salarios", "alquiler", "maquinaria", "impuesto"]
    for emp in [emp1, emp2]:
        if not emp:
            continue
        scale = 1.0 if emp.nombre == "El Progreso SA" else 0.65
        for camp in camp_objs:
            for cat in cats_pres:
                presup_base = {
                    "insumos": rv(150000000, 300000000, 0),
                    "labores": rv(100000000, 200000000, 0),
                    "salarios": rv(80000000, 150000000, 0),
                    "alquiler": rv(40000000, 90000000, 0),
                    "maquinaria": rv(20000000, 60000000, 0),
                    "impuesto": rv(30000000, 80000000, 0),
                }.get(cat, rv(20000000, 50000000, 0))
                presupuestos.append(Presupuesto(
                    empresa_id=emp.id,
                    campania_id=camp.id,
                    categoria=cat,
                    importe_presupuestado=round(presup_base * scale, 2),
                    importe_ejecutado=round(presup_base * scale * rv(0.7, 1.15, 2), 2),
                    fecha_creacion=camp.fecha_inicio,
                ))
    db.add_all(presupuestos)
    await db.flush()

    # ------------------------------------------------------------------ #
    # 13. ORDENES DE TRABAJO DE MAQUINARIA (200+ ordenes)
    # ------------------------------------------------------------------ #
    ordenes_trabajo = []
    tipos_labor_maq = ["siembra", "fumigacion", "cosecha", "labranza", "fertilizacion", "transporte"]

    for maq in maquinas_v2:
        if maq.estado == "baja":
            continue
        # 4-7 ordenes por maquina
        n_ordenes = ri(4, 7)
        # Establecimiento de la maquina (buscado por empresa)
        emp_ests_maq = [e for e in ests if e.empresa_id == maq.empresa_id]
        if not emp_ests_maq:
            continue
        for camp in camp_objs:
            camp_tpl = camp_map_inv.get(camp.id, "2023/2024")
            t_c = tc(camp_tpl)
            for _ in range(ri(2, 4)):
                lote_ref = rc(lotes) if lotes else None
                tipo_labor = rc(tipos_labor_maq)
                dias_ini = ri(10, 320)
                fecha_ini = camp.fecha_inicio + timedelta(days=dias_ini)
                fecha_fin = fecha_ini + timedelta(days=ri(1, 5))
                hs = rv(4, 12, 1)
                comb = round(hs * rv(15, 25, 1), 1)
                costo = round(hs * rv(8000, 15000, 0), 2)
                ordenes_trabajo.append(OrdenTrabajo(
                    maquinaria_id=maq.id,
                    lote_id=lote_ref.id if lote_ref else None,
                    campania_id=camp.id,
                    tipo_labor=tipo_labor,
                    fecha_inicio=shift_date_years(fecha_ini, year_delta),
                    fecha_fin=shift_date_years(fecha_fin, year_delta),
                    hs_trabajadas=hs,
                    combustible_litros=comb,
                    costo_total=costo,
                    operador=rc(["Pedro Gomez", "Luis Silva", "Miguel Torres", "Juan Diaz", "Carlos Ruiz"]),
                ))
    db.add_all(ordenes_trabajo)
    await db.flush()

    # ------------------------------------------------------------------ #
    # 14. MANTENIMIENTOS V2
    # ------------------------------------------------------------------ #
    mantenimientos_v2 = []
    tipos_mant = ["preventivo", "preventivo", "correctivo", "revision"]
    descs_prev = [
        "Service 500 hs - cambio aceite motor y filtros",
        "Service 1000 hs - filtros, correas, liquido frenos",
        "Pre-siembra - calibracion dosificadores",
        "Pre-cosecha - revision general sistema trilladero",
        "Service anual - revision completa",
        "Cambio filtros hidraulicos y aceite transmision",
    ]
    descs_cor = [
        "Rotura sistema hidraulico - reemplazo bomba",
        "Falla turbo - reemplazo turbocompresor",
        "Reparacion caja de cambios",
        "Cambio rodamientos eje principal",
        "Reparacion sistema electrico",
    ]

    for maq in maquinas_v2:
        if maq.estado == "baja":
            continue
        prov = rc(prov_list) if prov_list else None
        n_mant = ri(2, 5)
        for i in range(n_mant):
            tipo_m = rc(tipos_mant)
            desc = rc(descs_prev) if tipo_m in ["preventivo", "revision"] else rc(descs_cor)
            dias_mant = ri(30, 900)
            fecha_mant = date(2022, 7, 1) + timedelta(days=dias_mant)
            hs_motor = maq.horas_motor - ri(100, 600) * (n_mant - i)
            costo_mant = rv(80000, 2500000, 0) if tipo_m == "correctivo" else rv(80000, 800000, 0)
            mantenimientos_v2.append(MantenimientoV2(
                maquinaria_id=maq.id,
                tipo=tipo_m,
                fecha=shift_date_years(fecha_mant, year_delta),
                descripcion=desc,
                costo=costo_mant,
                proveedor_id=prov.id if prov else None,
                hs_motor_al_momento=max(hs_motor, 0),
                proxima_revision_hs=max(hs_motor + 500, 500) if tipo_m != "correctivo" else None,
            ))
    db.add_all(mantenimientos_v2)
    await db.flush()

    # ------------------------------------------------------------------ #
    # 15. ORDENES DE COMPRA DE INSUMOS
    # ------------------------------------------------------------------ #
    ordenes_compra = []
    items_oc = []

    for emp in [emp1, emp2]:
        if not emp:
            continue
        for camp in camp_objs:
            prov = rc(prov_list) if prov_list else None
            if not prov:
                continue
            # 5 ordenes por empresa por campaña
            for _ in range(5):
                fecha_oc = camp.fecha_inicio + timedelta(days=ri(0, 90))
                oc = OrdenCompraInsumo(
                    empresa_id=emp.id,
                    proveedor_id=prov.id,
                    campania_id=camp.id,
                    fecha=shift_date_years(fecha_oc, year_delta),
                    estado=rc(["recibido", "recibido", "pendiente"]),
                    total_ars=0,  # calculado después
                )
                ordenes_compra.append(oc)
    db.add_all(ordenes_compra)
    await db.flush()

    # Items para cada OC
    total_oc_map = {}
    for oc in ordenes_compra:
        n_items = ri(2, 5)
        total = 0
        for _ in range(n_items):
            ins = rc(insumos_v2)
            qty = rv(10, 500, 1)
            precio_u = ins.precio_actual_ars * rv(0.9, 1.1, 2)
            importe_item = round(qty * precio_u, 2)
            total += importe_item
            items_oc.append(ItemOrdenCompraInsumo(
                orden_id=oc.id,
                insumo_id=ins.id,
                cantidad=qty,
                precio_unitario=round(precio_u, 2),
                importe=importe_item,
            ))
        total_oc_map[oc.id] = round(total, 2)
    db.add_all(items_oc)
    await db.flush()

    # Actualizar totales de OC
    for oc in ordenes_compra:
        oc.total_ars = total_oc_map.get(oc.id, 0)
    await db.flush()

    # Movimientos de insumos v2
    movimientos_ins_v2 = []
    for emp in [emp1, emp2]:
        if not emp:
            continue
        emp_ests = [e for e in ests if e.empresa_id == emp.id]
        for camp in camp_objs:
            for _ in range(20):
                ins = rc(insumos_v2)
                est = rc(emp_ests)
                tipo_mov = rc(["compra", "uso", "ajuste"])
                dias_mov = ri(0, 320)
                fecha_mov = camp.fecha_inicio + timedelta(days=dias_mov)
                movimientos_ins_v2.append(MovimientoInsumoV2(
                    insumo_id=ins.id,
                    establecimiento_id=est.id,
                    tipo=tipo_mov,
                    fecha=shift_date_years(fecha_mov, year_delta),
                    cantidad=rv(10, 500, 1),
                    referencia=f"Campaña {camp.nombre} - {tipo_mov}",
                ))
    db.add_all(movimientos_ins_v2)
    await db.flush()

    logger.info(
        f"ERP v2 seeded: {len(silos)} silos, {len(siembras)} siembras, {len(cosechas_v2)} cosechas_v2, "
        f"{len(aplicaciones)} aplicaciones, {len(contratos_v2)} contratos_v2, {len(ventas_v2)} ventas_v2, "
        f"{len(flujos_v2)} flujos_v2, {len(maquinas_v2)} maquinas_v2, {len(ordenes_trabajo)} ordenes_trabajo, "
        f"{len(mantenimientos_v2)} mantenimientos_v2, {len(ordenes_compra)} ordenes_compra"
    )
