from __future__ import annotations

import hashlib
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lemon_commercial import (
    CobranzasFact,
    ContratoVentaFact,
    CostosDirectosFact,
    CostosIndirectosFact,
    CuentasCobrarFact,
    EmbarqueFact,
    LiquidacionFact,
    PrecioVentaFact,
    PresupuestoLoteFact,
    StockFinalFact,
)
from app.models.lemon_dimensions import (
    CalibreDim,
    CampaniaDim,
    CanalDim,
    CampoDim,
    ClienteDim,
    DefectoDim,
    DepositoDim,
    DestinoFrutaDim,
    EmpresaDim,
    EnfermedadDim,
    EstablecimientoDim,
    FechaDim,
    LineaEmpaqueDim,
    LoteDim,
    MercadoDim,
    PlagaDim,
    TurnoDim,
    VariedadDim,
)
from app.models.lemon_external import (
    ClimaDiarioFact,
    CostoEnergiaFact,
    CostoFleteFact,
    MacroSeriesFact,
    PrecioExportacionFact,
    TipoCambioFact,
)
from app.models.lemon_field import (
    AplicacionFitosanitariaFact,
    CosechaFact,
    Et0Fact,
    FertirriegoFact,
    LoteCampaniaFact,
    RequerimientoHidricoFact,
    RendimientoAmbienteFact,
    RendimientoLoteFact,
    RiegoFact,
    ScoutingFact,
)
from app.models.lemon_packhouse import (
    ConsumoPackhouseFact,
    DowntimePackhouseFact,
    MantenimientoPackhouseFact,
    ManoObraPackhouseFact,
    PackhouseTurnoFact,
)
from app.models.lemon_quality import (
    ClasificacionCalidadFact,
    PackoutFact,
    RecepcionFrutaFact,
    RechazoFact,
)
from app.models.usuario import Usuario


SEED_START = date(2022, 1, 1)
SEED_END = date(2026, 12, 31)
CURRENT_DATE = date(2026, 3, 22)
QUALITY_ALERT_START = date(2026, 3, 10)
QUALITY_ALERT_END = date(2026, 3, 16)
PACKHOUSE_INCIDENT_START = date(2026, 3, 11)
PACKHOUSE_INCIDENT_END = date(2026, 3, 18)


SPANISH_MONTHS = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}

ESTABLISHMENT_PROFILES = [
    {
        "codigo": "EC",
        "nombre": "El Carmen",
        "provincia": "Tucumán",
        "localidad": "Burruyacú",
        "superficie_total_ha": 640,
        "packhouse_activo": True,
        "lat": -26.58,
        "lon": -64.96,
    },
    {
        "codigo": "LQ",
        "nombre": "La Quebrada",
        "provincia": "Tucumán",
        "localidad": "Famaillá",
        "superficie_total_ha": 515,
        "packhouse_activo": False,
        "lat": -27.03,
        "lon": -65.38,
    },
]

FIELD_TEMPLATES = {
    "EC": [("Las Tipas", 206), ("Santa Rosa", 188), ("El Bordo", 194)],
    "LQ": [("Río Seco", 162), ("San Javier", 154), ("El Alto", 149)],
}

LOT_SCENARIOS = {
    "EC-C1-L1": {"yield_bias": 0.08, "quality_bias": 0.05, "hydric": "normal", "sanitary": "low"},
    "EC-C1-L2": {"yield_bias": -0.10, "quality_bias": -0.06, "hydric": "déficit", "sanitary": "medium"},
    "EC-C2-L1": {"yield_bias": 0.05, "quality_bias": 0.02, "hydric": "normal", "sanitary": "low"},
    "EC-C2-L2": {"yield_bias": 0.02, "quality_bias": -0.01, "hydric": "normal", "sanitary": "medium"},
    "EC-C3-L1": {"yield_bias": 0.00, "quality_bias": 0.01, "hydric": "normal", "sanitary": "low"},
    "EC-C3-L2": {"yield_bias": 0.06, "quality_bias": 0.03, "hydric": "normal", "sanitary": "low"},
    "LQ-C1-L1": {"yield_bias": -0.06, "quality_bias": -0.08, "hydric": "déficit", "sanitary": "medium"},
    "LQ-C1-L2": {"yield_bias": -0.03, "quality_bias": -0.03, "hydric": "normal", "sanitary": "medium"},
    "LQ-C2-L1": {"yield_bias": -0.16, "quality_bias": -0.11, "hydric": "déficit", "sanitary": "high"},
    "LQ-C2-L2": {"yield_bias": -0.20, "quality_bias": -0.13, "hydric": "exceso", "sanitary": "high"},
    "LQ-C3-L1": {"yield_bias": -0.12, "quality_bias": -0.14, "hydric": "déficit", "sanitary": "high"},
    "LQ-C3-L2": {"yield_bias": 0.01, "quality_bias": -0.05, "hydric": "normal", "sanitary": "medium"},
}

VARIETY_BY_LOT_CODE = {
    "EC-C1-L1": "Frost Eureka",
    "EC-C1-L2": "Lisbon",
    "EC-C2-L1": "Frost Eureka",
    "EC-C2-L2": "Genova",
    "EC-C3-L1": "Lisbon",
    "EC-C3-L2": "Fino 49",
    "LQ-C1-L1": "Genova",
    "LQ-C1-L2": "Lisbon",
    "LQ-C2-L1": "Fino 49",
    "LQ-C2-L2": "Genova",
    "LQ-C3-L1": "Lisbon",
    "LQ-C3-L2": "Frost Eureka",
}

CLIENT_PAYMENT_RISK = {
    "AR_MAYOR": "high",
    "RU_MARKET": "medium",
}


@dataclass
class LemonSeedState:
    rng: random.Random = field(default_factory=lambda: random.Random(42))
    fecha_ids: dict[date, int] = field(default_factory=dict)
    campanias: dict[str, CampaniaDim] = field(default_factory=dict)
    establecimientos: list[EstablecimientoDim] = field(default_factory=list)
    campos: list[CampoDim] = field(default_factory=list)
    lotes: list[LoteDim] = field(default_factory=list)
    lotes_por_establecimiento: dict[int, list[LoteDim]] = field(default_factory=lambda: defaultdict(list))
    variedad_por_lote: dict[int, int] = field(default_factory=dict)
    lotes_campania: list[LoteCampaniaFact] = field(default_factory=list)
    presupuestos: list[PresupuestoLoteFact] = field(default_factory=list)
    variedades: list[VariedadDim] = field(default_factory=list)
    lineas: list[LineaEmpaqueDim] = field(default_factory=list)
    turnos: list[TurnoDim] = field(default_factory=list)
    clientes: list[ClienteDim] = field(default_factory=list)
    mercados: list[MercadoDim] = field(default_factory=list)
    canales: list[CanalDim] = field(default_factory=list)
    destinos: list[DestinoFrutaDim] = field(default_factory=list)
    calibres: list[CalibreDim] = field(default_factory=list)
    defectos: list[DefectoDim] = field(default_factory=list)
    depositos: list[DepositoDim] = field(default_factory=list)
    plagas: list[PlagaDim] = field(default_factory=list)
    enfermedades: list[EnfermedadDim] = field(default_factory=list)
    contratos: list[ContratoVentaFact] = field(default_factory=list)
    packhouse_por_establecimiento: dict[int, int] = field(default_factory=dict)
    deposito_fresco_por_est: dict[int, int] = field(default_factory=dict)
    deposito_industria_por_est: dict[int, int] = field(default_factory=dict)
    latest_tipo_cambio: dict[date, float] = field(default_factory=dict)


def _daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _chunked_days(start: date, end: date, step_days: int):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=step_days)


def _safe_pct(*values: float) -> list[float]:
    total = sum(values)
    if total <= 0:
        return [0 for _ in values]
    return [value / total for value in values]


def _hash_password(password: str) -> str:
    try:
        import bcrypt

        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except Exception:
        salt = "lemon_bi_fixed_salt_2026"
        digest = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
        return f"$2b$12${digest[:22]}{digest[22:75]}"


def _campaign_second_year(campania: CampaniaDim) -> int:
    return campania.fecha_fin.year


def _campaign_factor(codigo: str) -> float:
    return {
        "2022_23": 0.93,
        "2023_24": 1.05,
        "2024_25": 1.01,
        "2025_26": 0.98,
    }[codigo]


def _campaign_status(codigo: str) -> str:
    return "activa" if codigo == "2025_26" else "cerrada"


def _harvest_window(year_two: int, epoca_principal: str, rng: random.Random) -> tuple[date, date]:
    if epoca_principal == "temprana":
        start = date(year_two, 1, rng.randint(20, 31)) if rng.random() < 0.6 else date(year_two, 2, rng.randint(1, 10))
        end = date(year_two, 5, rng.randint(12, 28))
        return start, end
    if epoca_principal == "tardia":
        start = date(year_two, 3, rng.randint(1, 18))
        end = date(year_two, 6, rng.randint(18, 30))
        return start, end
    start = date(year_two, 2, rng.randint(8, 26))
    end = date(year_two, 6, rng.randint(8, 24))
    return start, end


def _processing_establishment(state: LemonSeedState, establecimiento_id: int) -> int:
    return state.packhouse_por_establecimiento[establecimiento_id]


def _nearest_week_price(reference_prices: dict[tuple[date, int, int], float], value_date: date, mercado_id: int, canal_id: int) -> float:
    for offset in range(0, 7):
        probe = value_date - timedelta(days=offset)
        key = (probe, mercado_id, canal_id)
        if key in reference_prices:
            return reference_prices[key]
    candidates = [price for (probe_date, mid, cid), price in reference_prices.items() if mid == mercado_id and cid == canal_id and probe_date <= value_date]
    return candidates[-1] if candidates else 0


def _line_performance_bias(linea: LineaEmpaqueDim) -> float:
    if linea.codigo == "EC-L1":
        return 1.18
    if linea.codigo == "EC-L2":
        return 0.78
    if linea.codigo.endswith("L1"):
        return 1.06
    return 0.84


def _choose_processing_line(
    state: LemonSeedState,
    lineas_por_est: dict[int, list[LineaEmpaqueDim]],
    lineas_por_codigo: dict[str, LineaEmpaqueDim],
    processing_est: int,
    process_date: date,
) -> LineaEmpaqueDim:
    lines = lineas_por_est[processing_est]
    if len(lines) == 1:
        return lines[0]

    # El Carmen concentra el packhouse y opera con dos perfiles claros:
    # una línea más estable y una línea más sensible a paradas.
    if processing_est == state.establecimientos[0].establecimiento_id:
        line_1 = lineas_por_codigo["EC-L1"]
        line_2 = lineas_por_codigo["EC-L2"]
        if PACKHOUSE_INCIDENT_START <= process_date <= PACKHOUSE_INCIDENT_END:
            return line_2 if state.rng.random() < 0.42 else line_1
        return line_1 if state.rng.random() < 0.64 else line_2

    ordered = sorted(lines, key=lambda item: item.codigo)
    return ordered[0] if state.rng.random() < 0.58 else ordered[-1]


def _line_packout_efficiency(
    state: LemonSeedState,
    linea: LineaEmpaqueDim,
    destination_code: str,
    process_date: date,
    *,
    quality_window: bool,
    line_incident: bool,
) -> float:
    if linea.codigo == "EC-L1":
        base_by_destination = {
            "EXP": (89.0, 95.0),
            "LOC": (86.0, 92.0),
            "IND": (83.0, 89.0),
        }
    elif linea.codigo == "EC-L2":
        base_by_destination = {
            "EXP": (80.0, 88.0),
            "LOC": (77.0, 85.0),
            "IND": (74.0, 82.0),
        }
    else:
        base_by_destination = {
            "EXP": (84.0, 90.0),
            "LOC": (81.0, 88.0),
            "IND": (79.0, 86.0),
        }

    lower, upper = base_by_destination[destination_code]
    efficiency = state.rng.uniform(lower, upper)
    if quality_window:
        efficiency -= state.rng.uniform(1.8, 3.8)
    if line_incident:
        efficiency -= state.rng.uniform(8.5, 14.0)
    return round(max(52.0, min(96.0, efficiency)), 2)


def _packhouse_shift_metrics(
    state: LemonSeedState,
    linea: LineaEmpaqueDim,
    process_date: date,
    kg: float,
) -> tuple[float, float, float, float]:
    tons = max(0.0, kg / 1000.0)
    if tons >= 18:
        scheduled_hours = state.rng.uniform(7.8, 8.6)
    elif tons >= 12:
        scheduled_hours = state.rng.uniform(7.1, 8.0)
    elif tons >= 8:
        scheduled_hours = state.rng.uniform(6.3, 7.3)
    else:
        scheduled_hours = state.rng.uniform(5.6, 6.8)

    if linea.codigo == "EC-L1":
        efficiency = state.rng.uniform(0.84, 0.91)
    elif linea.codigo == "EC-L2":
        efficiency = state.rng.uniform(0.76, 0.84)
    else:
        efficiency = state.rng.uniform(0.79, 0.87)

    if QUALITY_ALERT_START <= process_date <= QUALITY_ALERT_END:
        efficiency -= state.rng.uniform(0.015, 0.03)
    if linea.codigo == "EC-L2" and PACKHOUSE_INCIDENT_START <= process_date <= PACKHOUSE_INCIDENT_END:
        efficiency -= state.rng.uniform(0.12, 0.2)

    # Shifts livianos no deberían parecer "línea parada" si hubo poco volumen.
    if tons < 7:
        efficiency += state.rng.uniform(0.01, 0.03)
    elif tons > 16:
        efficiency -= state.rng.uniform(0.0, 0.025)

    efficiency = max(0.46, min(0.93, efficiency))
    productive_hours = round(scheduled_hours * efficiency, 2)
    downtime_hours = round(max(0.18, scheduled_hours - productive_hours), 2)
    return round(scheduled_hours, 2), productive_hours, downtime_hours, round(efficiency * 100, 2)


async def _clear_existing_limon_data(db: AsyncSession):
    for model in [
        Usuario,
        CobranzasFact,
        CuentasCobrarFact,
        LiquidacionFact,
        EmbarqueFact,
        ContratoVentaFact,
        PrecioVentaFact,
        StockFinalFact,
        CostosIndirectosFact,
        CostosDirectosFact,
        PresupuestoLoteFact,
        MantenimientoPackhouseFact,
        ConsumoPackhouseFact,
        ManoObraPackhouseFact,
        DowntimePackhouseFact,
        PackhouseTurnoFact,
        RechazoFact,
        PackoutFact,
        ClasificacionCalidadFact,
        RecepcionFrutaFact,
        RendimientoAmbienteFact,
        RendimientoLoteFact,
        CosechaFact,
        AplicacionFitosanitariaFact,
        ScoutingFact,
        FertirriegoFact,
        RiegoFact,
        RequerimientoHidricoFact,
        Et0Fact,
        CostoFleteFact,
        CostoEnergiaFact,
        PrecioExportacionFact,
        TipoCambioFact,
        MacroSeriesFact,
        ClimaDiarioFact,
        LoteCampaniaFact,
        DepositoDim,
        LineaEmpaqueDim,
        PlagaDim,
        EnfermedadDim,
        TurnoDim,
        DefectoDim,
        CalibreDim,
        DestinoFrutaDim,
        CanalDim,
        MercadoDim,
        ClienteDim,
        LoteDim,
        CampoDim,
        EstablecimientoDim,
        VariedadDim,
        CampaniaDim,
        FechaDim,
        EmpresaDim,
    ]:
        await db.execute(delete(model))


async def _seed_dimensions(db: AsyncSession, state: LemonSeedState):
    empresa = EmpresaDim(
        codigo="LIMONNOA",
        nombre="Lemon Intelligence",
        razon_social="Lemon Intelligence SA",
        provincia_base="Tucumán",
        pais="Argentina",
        activa=True,
    )
    db.add(empresa)
    await db.flush()

    usuarios = [
        Usuario(
            empresa_id=empresa.empresa_id,
            nombre="Admin Lemon BI",
            email="admin@demoagro.com",
            hashed_password=_hash_password("admin123"),
            rol="admin",
            activo=True,
        ),
        Usuario(
            empresa_id=empresa.empresa_id,
            nombre="Gerencia Lemon BI",
            email="gerencia@lemonbi.com",
            hashed_password=_hash_password("gerencia123"),
            rol="gerente",
            activo=True,
        ),
        Usuario(
            empresa_id=empresa.empresa_id,
            nombre="Operaciones Lemon BI",
            email="operaciones@lemonbi.com",
            hashed_password=_hash_password("operaciones123"),
            rol="operativo",
            activo=True,
        ),
    ]
    db.add_all(usuarios)

    campanias = [
        CampaniaDim(codigo="2022_23", nombre="2022/2023", fecha_inicio=date(2022, 7, 1), fecha_fin=date(2023, 6, 30), estado="cerrada", activa=False),
        CampaniaDim(codigo="2023_24", nombre="2023/2024", fecha_inicio=date(2023, 7, 1), fecha_fin=date(2024, 6, 30), estado="cerrada", activa=False),
        CampaniaDim(codigo="2024_25", nombre="2024/2025", fecha_inicio=date(2024, 7, 1), fecha_fin=date(2025, 6, 30), estado="cerrada", activa=False),
        CampaniaDim(codigo="2025_26", nombre="2025/2026", fecha_inicio=date(2025, 7, 1), fecha_fin=date(2026, 6, 30), estado="activa", activa=True),
    ]
    db.add_all(campanias)

    variedades = [
        VariedadDim(codigo="FROST_EUREKA", nombre="Frost Eureka", grupo="limon", epoca_principal="temprana", destino_preferido="fresco_exportacion", activa=True),
        VariedadDim(codigo="LISBON", nombre="Lisbon", grupo="limon", epoca_principal="media", destino_preferido="fresco_exportacion", activa=True),
        VariedadDim(codigo="GENOVA", nombre="Genova", grupo="limon", epoca_principal="media", destino_preferido="industria", activa=True),
        VariedadDim(codigo="FINO_49", nombre="Fino 49", grupo="limon", epoca_principal="tardia", destino_preferido="fresco_local", activa=True),
    ]
    db.add_all(variedades)

    establecimientos = [
        EstablecimientoDim(
            empresa_id=empresa.empresa_id,
            codigo=profile["codigo"],
            nombre=profile["nombre"],
            provincia=profile["provincia"],
            localidad=profile["localidad"],
            superficie_total_ha=profile["superficie_total_ha"],
            packhouse_activo=profile["packhouse_activo"],
            lat=profile["lat"],
            lon=profile["lon"],
        )
        for profile in ESTABLISHMENT_PROFILES
    ]
    db.add_all(establecimientos)
    await db.flush()

    campos: list[CampoDim] = []
    lotes: list[LoteDim] = []
    for establecimiento in establecimientos:
        for field_index, (field_name, surface_ha) in enumerate(FIELD_TEMPLATES[establecimiento.codigo], start=1):
            campo = CampoDim(
                establecimiento_id=establecimiento.establecimiento_id,
                codigo=f"{establecimiento.codigo}-C{field_index}",
                nombre=field_name,
                superficie_ha=round(surface_ha, 2),
                altitud_msnm=round(state.rng.uniform(280, 460), 1),
                tipo_suelo=state.rng.choice(["franco limoso", "franco", "franco arenoso"]),
            )
            campos.append(campo)
    db.add_all(campos)
    await db.flush()

    for campo in campos:
        for lot_index in range(1, 3):
            lote = LoteDim(
                campo_id=campo.campo_id,
                codigo=f"{campo.codigo}-L{lot_index}",
                nombre=f"Lote {lot_index}",
                superficie_ha=round(state.rng.uniform(18, 31), 2),
                anio_plantacion=state.rng.randint(2012, 2018),
                densidad_plantas_ha=state.rng.choice([370, 400, 416]),
                marco_plantacion=state.rng.choice(["6x4", "6x3.5"]),
                orientacion=state.rng.choice(["N-S", "E-O"]),
            )
            lotes.append(lote)
    db.add_all(lotes)

    clientes = [
        ClienteDim(codigo="EU_CITRUS", nombre="Euro Citrus BV", tipo="exportador", pais="Países Bajos", region="Europa", activo=True),
        ClienteDim(codigo="US_FRESH", nombre="SunFresh Imports", tipo="exportador", pais="Estados Unidos", region="Norteamérica", activo=True),
        ClienteDim(codigo="ME_CITRUS", nombre="Gulf Produce Trading", tipo="exportador", pais="Emiratos Árabes Unidos", region="Medio Oriente", activo=True),
        ClienteDim(codigo="RU_MARKET", nombre="Volga Fruit Group", tipo="exportador", pais="Rusia", region="Europa del Este", activo=True),
        ClienteDim(codigo="AR_MAYOR", nombre="Mercado Central Citrus", tipo="distribuidor", pais="Argentina", region="Mercado interno", activo=True),
        ClienteDim(codigo="IND_JUGOS", nombre="Industrial Citrus SRL", tipo="industria", pais="Argentina", region="Tucumán", activo=True),
    ]
    db.add_all(clientes)

    mercados = [
        MercadoDim(codigo="EU", nombre="Unión Europea", region="Europa", moneda="USD", activo=True),
        MercadoDim(codigo="USA", nombre="Estados Unidos", region="Norteamérica", moneda="USD", activo=True),
        MercadoDim(codigo="MEA", nombre="Medio Oriente", region="Medio Oriente", moneda="USD", activo=True),
        MercadoDim(codigo="RUS", nombre="Europa del Este", region="Europa del Este", moneda="USD", activo=True),
        MercadoDim(codigo="ARG", nombre="Mercado interno", region="Argentina", moneda="ARS", activo=True),
        MercadoDim(codigo="IND", nombre="Industria Tucumán", region="Argentina", moneda="ARS", activo=True),
    ]
    db.add_all(mercados)

    canales = [
        CanalDim(codigo="FRESCO_EXP", nombre="Fresco exportación", descripcion="Canal premium para fruta fresca exportable", activo=True),
        CanalDim(codigo="FRESCO_LOC", nombre="Fresco local", descripcion="Mercado interno fresco", activo=True),
        CanalDim(codigo="INDUSTRIA", nombre="Industria", descripcion="Jugo, aceite y subproductos", activo=True),
    ]
    db.add_all(canales)

    destinos = [
        DestinoFrutaDim(codigo="EXP", nombre="Fresco exportación", orden=1, es_comercial=True),
        DestinoFrutaDim(codigo="LOC", nombre="Fresco local", orden=2, es_comercial=True),
        DestinoFrutaDim(codigo="IND", nombre="Industria", orden=3, es_comercial=True),
        DestinoFrutaDim(codigo="DSC", nombre="Descarte", orden=4, es_comercial=False),
    ]
    db.add_all(destinos)

    calibres = [
        CalibreDim(codigo="95", nombre="Calibre 95", diametro_min_mm=72, diametro_max_mm=80, apto_exportacion=True),
        CalibreDim(codigo="115", nombre="Calibre 115", diametro_min_mm=68, diametro_max_mm=72, apto_exportacion=True),
        CalibreDim(codigo="138", nombre="Calibre 138", diametro_min_mm=63, diametro_max_mm=68, apto_exportacion=True),
        CalibreDim(codigo="165", nombre="Calibre 165", diametro_min_mm=58, diametro_max_mm=63, apto_exportacion=False),
        CalibreDim(codigo="200", nombre="Calibre 200", diametro_min_mm=52, diametro_max_mm=58, apto_exportacion=False),
    ]
    db.add_all(calibres)

    defectos = [
        DefectoDim(codigo="OLEO", nombre="Oleocelosis", categoria="cosmético", severidad_base="media"),
        DefectoDim(codigo="MEC", nombre="Daño mecánico", categoria="manejo", severidad_base="alta"),
        DefectoDim(codigo="CAN", nombre="Cancrosis", categoria="sanitario", severidad_base="alta"),
        DefectoDim(codigo="VER", nombre="Color verde", categoria="madurez", severidad_base="media"),
        DefectoDim(codigo="POD", nombre="Podredumbre", categoria="sanitario", severidad_base="alta"),
        DefectoDim(codigo="RUS", nombre="Russet", categoria="cosmético", severidad_base="media"),
    ]
    db.add_all(defectos)

    turnos = [
        TurnoDim(codigo="T1", nombre="Turno mañana", hora_inicio="06:00", hora_fin="14:00", activo=True),
        TurnoDim(codigo="T2", nombre="Turno tarde", hora_inicio="14:00", hora_fin="22:00", activo=True),
        TurnoDim(codigo="T3", nombre="Turno noche", hora_inicio="22:00", hora_fin="06:00", activo=True),
    ]
    db.add_all(turnos)

    plagas = [
        PlagaDim(codigo="ACARO", nombre="Ácaro de la yema", categoria="ácaro", monitoreo_semanal=True),
        PlagaDim(codigo="MINADOR", nombre="Minador de la hoja", categoria="insecto", monitoreo_semanal=True),
        PlagaDim(codigo="PULGON", nombre="Pulgón", categoria="insecto", monitoreo_semanal=True),
        PlagaDim(codigo="COCHIN", nombre="Cochinilla", categoria="insecto", monitoreo_semanal=True),
    ]
    enfermedades = [
        EnfermedadDim(codigo="PHYT", nombre="Phytophthora", categoria="raíz", monitoreo_semanal=True),
        EnfermedadDim(codigo="MELA", nombre="Melanosis", categoria="fruta", monitoreo_semanal=True),
        EnfermedadDim(codigo="CANC", nombre="Cancrosis", categoria="fruta", monitoreo_semanal=True),
        EnfermedadDim(codigo="ANTR", nombre="Antracnosis", categoria="fruta", monitoreo_semanal=True),
    ]
    db.add_all(plagas + enfermedades)

    lineas: list[LineaEmpaqueDim] = []
    depositos: list[DepositoDim] = []
    for establecimiento in establecimientos:
        if establecimiento.packhouse_activo:
            lineas.append(LineaEmpaqueDim(establecimiento_id=establecimiento.establecimiento_id, codigo=f"{establecimiento.codigo}-L1", nombre=f"Línea 1 {establecimiento.nombre}", capacidad_tn_hora=10.5, activa=True))
            lineas.append(LineaEmpaqueDim(establecimiento_id=establecimiento.establecimiento_id, codigo=f"{establecimiento.codigo}-L2", nombre=f"Línea 2 {establecimiento.nombre}", capacidad_tn_hora=8.8, activa=True))
            depositos.append(DepositoDim(establecimiento_id=establecimiento.establecimiento_id, codigo=f"{establecimiento.codigo}-FR", nombre=f"Cámara frío {establecimiento.nombre}", tipo="fresco", capacidad_kg=680000, activo=True))
            depositos.append(DepositoDim(establecimiento_id=establecimiento.establecimiento_id, codigo=f"{establecimiento.codigo}-IN", nombre=f"Pulmón industria {establecimiento.nombre}", tipo="industria", capacidad_kg=420000, activo=True))
    db.add_all(lineas + depositos)

    fechas: list[FechaDim] = []
    fecha_id = 1
    for current in _daterange(SEED_START, SEED_END):
        fechas.append(
            FechaDim(
                fecha_id=fecha_id,
                fecha=current,
                anio=current.year,
                mes=current.month,
                dia=current.day,
                semana=current.isocalendar().week,
                trimestre=((current.month - 1) // 3) + 1,
                nombre_mes=SPANISH_MONTHS[current.month],
                es_fin_de_semana=current.weekday() >= 5,
            )
        )
        state.fecha_ids[current] = fecha_id
        fecha_id += 1
    db.add_all(fechas)
    await db.flush()

    state.campanias = {campania.codigo: campania for campania in campanias}
    state.establecimientos = establecimientos
    state.campos = campos
    state.lotes = lotes
    state.variedades = variedades
    state.lineas = lineas
    state.turnos = turnos
    state.clientes = clientes
    state.mercados = mercados
    state.canales = canales
    state.destinos = destinos
    state.calibres = calibres
    state.defectos = defectos
    state.depositos = depositos
    state.plagas = plagas
    state.enfermedades = enfermedades

    for lote in lotes:
        establecimiento_id = next(campo.establecimiento_id for campo in campos if campo.campo_id == lote.campo_id)
        state.lotes_por_establecimiento[establecimiento_id].append(lote)
        target_variety_name = VARIETY_BY_LOT_CODE.get(lote.codigo)
        variedad = next((item for item in variedades if item.nombre == target_variety_name), None) or state.rng.choice(variedades)
        state.variedad_por_lote[lote.lote_id] = variedad.variedad_id

    fallback_map = {
        establecimientos[0].establecimiento_id: establecimientos[0].establecimiento_id,
        establecimientos[1].establecimiento_id: establecimientos[0].establecimiento_id,
    }
    state.packhouse_por_establecimiento = fallback_map
    for deposito in depositos:
        if deposito.tipo == "fresco":
            state.deposito_fresco_por_est[deposito.establecimiento_id] = deposito.deposito_id
        else:
            state.deposito_industria_por_est[deposito.establecimiento_id] = deposito.deposito_id


async def _seed_external(db: AsyncSession, state: LemonSeedState):
    clima_rows: list[ClimaDiarioFact] = []
    et0_rows: list[Et0Fact] = []
    macro_rows: list[MacroSeriesFact] = []
    tc_rows: list[TipoCambioFact] = []
    export_price_rows: list[PrecioExportacionFact] = []
    energia_rows: list[CostoEnergiaFact] = []
    flete_rows: list[CostoFleteFact] = []

    export_markets = [mercado for mercado in state.mercados if mercado.codigo in {"EU", "USA", "MEA", "RUS"}]

    for establecimiento in state.establecimientos:
        altitude_effect = next(campo.altitud_msnm for campo in state.campos if campo.establecimiento_id == establecimiento.establecimiento_id)
        for current in _daterange(date(2023, 1, 1), CURRENT_DATE):
            day_angle = (2 * math.pi * current.timetuple().tm_yday) / 365.0
            temp_media = 20.5 + 5.8 * math.sin(day_angle - 0.7) + state.rng.uniform(-1.2, 1.2) - (altitude_effect / 1200.0)
            temp_min = temp_media - state.rng.uniform(5.5, 8.5)
            temp_max = temp_media + state.rng.uniform(6.0, 9.0)
            summer = current.month in {12, 1, 2, 3}
            dry_season = current.month in {6, 7, 8, 9}
            base_rain = state.rng.uniform(0, 6 if summer else 2.5)
            if dry_season:
                base_rain *= 0.35
            if state.rng.random() < (0.22 if summer else 0.08):
                base_rain += state.rng.uniform(8, 32)
            humidity = max(38, min(92, 64 + 12 * math.sin(day_angle + 0.4) + state.rng.uniform(-8, 8)))
            hours_cold = max(0, round((10 - temp_min) * 0.8, 2)) if temp_min < 10 else 0
            clima_rows.append(
                ClimaDiarioFact(
                    establecimiento_id=establecimiento.establecimiento_id,
                    fecha_id=state.fecha_ids[current],
                    fecha=current,
                    temperatura_min_c=round(temp_min, 2),
                    temperatura_max_c=round(temp_max, 2),
                    temperatura_media_c=round((temp_min + temp_max) / 2, 2),
                    precipitacion_mm=round(base_rain, 2),
                    humedad_relativa_pct=round(humidity, 2),
                    horas_frio=hours_cold,
                )
            )
            et0 = max(1.6, min(7.2, 3.4 + (temp_max - temp_min) * 0.16 + (1 - humidity / 100) * 2.1 + state.rng.uniform(-0.35, 0.35)))
            et0_rows.append(
                Et0Fact(
                    establecimiento_id=establecimiento.establecimiento_id,
                    fecha_id=state.fecha_ids[current],
                    fecha=current,
                    et0_mm=round(et0, 2),
                    kc=round(state.rng.uniform(0.7, 0.92), 2),
                    eto_ajustada_mm=round(et0 * state.rng.uniform(0.76, 0.95), 2),
                )
            )

    current_month = date(2023, 1, 1)
    while current_month <= date(2026, 3, 1):
        months_from_start = (current_month.year - 2023) * 12 + current_month.month - 1
        inflacion = max(1.8, 8.2 - months_from_start * 0.08 + state.rng.uniform(-0.35, 0.35))
        inflacion_interanual = max(32, 110 - months_from_start * 1.4 + state.rng.uniform(-2.0, 2.0))
        tasa = max(24, 74 - months_from_start * 0.65 + state.rng.uniform(-1.8, 1.8))
        for variable, value, unit in [
            ("inflacion_mensual", inflacion, "%"),
            ("inflacion_interanual", inflacion_interanual, "%"),
            ("tasa_referencia", tasa, "%"),
        ]:
            macro_rows.append(
                MacroSeriesFact(
                    fecha_id=state.fecha_ids[current_month],
                    fecha=current_month,
                    variable=variable,
                    valor=round(value, 2),
                    unidad=unit,
                    fuente="Serie macro simulada",
                )
            )
        energia_rows.append(
            CostoEnergiaFact(
                fecha_id=state.fecha_ids[current_month],
                fecha=current_month,
                ars_kwh=round(32 + months_from_start * 2.8 + state.rng.uniform(-1.5, 1.5), 2),
                indice=round(100 + months_from_start * 3.1 + state.rng.uniform(-2, 2), 2),
            )
        )
        current_month = date(current_month.year + (current_month.month // 12), (current_month.month % 12) + 1, 1)

    for current in _daterange(date(2023, 1, 1), CURRENT_DATE):
        days_from_start = (current - date(2023, 1, 1)).days
        official = 188 + days_from_start * 0.92 + math.sin(days_from_start / 29) * 5
        wholesale = official * 0.985
        export = wholesale * 1.08
        tc_rows.append(
            TipoCambioFact(
                fecha_id=state.fecha_ids[current],
                fecha=current,
                oficial=round(official, 2),
                mayorista=round(wholesale, 2),
                exportacion=round(export, 2),
            )
        )
        state.latest_tipo_cambio[current] = round(export, 2)

    monday = date(2023, 1, 2)
    while monday <= CURRENT_DATE:
        weeks_from_start = (monday - date(2023, 1, 2)).days / 7
        for mercado in export_markets:
            base_price = {
                "EU": 1110,
                "USA": 1260,
                "MEA": 980,
                "RUS": 930,
            }[mercado.codigo]
            seasonal = 60 * math.sin(weeks_from_start / 6.0)
            trend = weeks_from_start * 0.85
            noise = state.rng.uniform(-28, 28)
            price = max(780, base_price + seasonal + trend + noise)
            export_price_rows.append(
                PrecioExportacionFact(
                    fecha_id=state.fecha_ids[monday],
                    fecha=monday,
                    mercado_id=mercado.mercado_id,
                    precio_promedio_usd_tn=round(price, 2),
                    volumen_kg=round(state.rng.uniform(220000, 540000), 2),
                )
            )
            flete_rows.append(
                CostoFleteFact(
                    fecha_id=state.fecha_ids[monday],
                    fecha=monday,
                    mercado_id=mercado.mercado_id,
                    usd_tn=round(max(62, 90 + {"EU": 0, "USA": 18, "MEA": 10, "RUS": 6}[mercado.codigo] + weeks_from_start * 0.14 + state.rng.uniform(-4, 4)), 2),
                    combustible_pct=round(max(18, min(52, 28 + weeks_from_start * 0.06 + state.rng.uniform(-2, 2))), 2),
                )
            )
        monday += timedelta(days=7)

    db.add_all(clima_rows + et0_rows + macro_rows + tc_rows + export_price_rows + energia_rows + flete_rows)
    await db.flush()


async def _seed_field_operations(db: AsyncSession, state: LemonSeedState):
    lot_campaign_rows: list[LoteCampaniaFact] = []
    budget_rows: list[PresupuestoLoteFact] = []
    scouting_rows: list[ScoutingFact] = []
    application_rows: list[AplicacionFitosanitariaFact] = []
    riego_rows: list[RiegoFact] = []
    fertirriego_rows: list[FertirriegoFact] = []
    requerimiento_rows: list[RequerimientoHidricoFact] = []
    cosecha_rows: list[CosechaFact] = []
    rendimiento_rows: list[RendimientoLoteFact] = []
    rendimiento_amb_rows: list[RendimientoAmbienteFact] = []
    cost_rows: list[CostosDirectosFact] = []

    clima_lookup: dict[tuple[int, date], tuple[float, float]] = {}
    result = await db.execute(select(ClimaDiarioFact.establecimiento_id, ClimaDiarioFact.fecha, ClimaDiarioFact.precipitacion_mm, ClimaDiarioFact.humedad_relativa_pct))
    for establecimiento_id, fecha_clima, precipitacion_mm, humedad in result.all():
        clima_lookup[(establecimiento_id, fecha_clima)] = (precipitacion_mm or 0, humedad or 0)

    et0_lookup: dict[tuple[int, date], float] = {}
    result = await db.execute(select(Et0Fact.establecimiento_id, Et0Fact.fecha, Et0Fact.eto_ajustada_mm))
    for establecimiento_id, fecha_et0, eto_ajustada in result.all():
        et0_lookup[(establecimiento_id, fecha_et0)] = eto_ajustada or 0

    quality_batches: list[dict] = []

    establishment_factor = {
        "EC": 1.04,
        "LQ": 0.94,
    }
    variety_base_kg = {
        "Frost Eureka": 34200,
        "Lisbon": 32600,
        "Genova": 30100,
        "Fino 49": 31500,
    }

    for lot in state.lotes:
        campo = next(campo for campo in state.campos if campo.campo_id == lot.campo_id)
        establecimiento = next(est for est in state.establecimientos if est.establecimiento_id == campo.establecimiento_id)
        variedad_id = state.variedad_por_lote[lot.lote_id]
        variedad = next(var for var in state.variedades if var.variedad_id == variedad_id)
        scenario = LOT_SCENARIOS.get(
            lot.codigo,
            {"yield_bias": 0.0, "quality_bias": 0.0, "hydric": "normal", "sanitary": "medium"},
        )
        lot_quality_bias = scenario["quality_bias"] + state.rng.uniform(-0.015, 0.015)
        lot_yield_bias = scenario["yield_bias"] + state.rng.uniform(-0.025, 0.025)
        for campania in state.campanias.values():
            year_two = _campaign_second_year(campania)
            harvest_start_est, harvest_end_est = _harvest_window(year_two, variedad.epoca_principal or "media", state.rng)
            objective_yield = (
                variety_base_kg[variedad.nombre]
                * establishment_factor[establecimiento.codigo]
                * (1 + scenario["yield_bias"] * 0.35)
                * state.rng.uniform(0.97, 1.04)
            )
            objective_packout = max(
                47,
                min(
                    74,
                    61
                    + (1.5 if establecimiento.codigo == "EC" else -1.0)
                    + lot_quality_bias * 92
                    + state.rng.uniform(-2.5, 2.5),
                ),
            )
            objective_margin_ha = round(objective_yield * 0.18, 2)
            lc = LoteCampaniaFact(
                lote_id=lot.lote_id,
                campania_id=campania.campania_id,
                variedad_id=variedad.variedad_id,
                establecimiento_id=establecimiento.establecimiento_id,
                superficie_ha=lot.superficie_ha,
                arboles_productivos=int(lot.superficie_ha * lot.densidad_plantas_ha * state.rng.uniform(0.82, 0.95)),
                fecha_inicio_cosecha_estimada=harvest_start_est,
                fecha_fin_cosecha_estimada=harvest_end_est,
                objetivo_kg_ha=round(objective_yield, 2),
                objetivo_packout_pct=round(objective_packout, 2),
                objetivo_margen_ha=objective_margin_ha,
                estado=_campaign_status(campania.codigo),
                condicion_hidrica=scenario["hydric"],
            )
            lot_campaign_rows.append(lc)
            budget_price_ars_kg = 480 + (year_two - 2023) * 95 + state.rng.uniform(-18, 18)
            kg_plan = lot.superficie_ha * objective_yield
            ingreso_plan = kg_plan * budget_price_ars_kg
            costo_directo_plan = ingreso_plan * state.rng.uniform(0.34, 0.42)
            costo_indirecto_plan = ingreso_plan * state.rng.uniform(0.08, 0.12)
            budget_rows.append(
                PresupuestoLoteFact(
                    lote_campania_id=0,
                    kg_plan=round(kg_plan, 2),
                    packout_plan_pct=round(objective_packout, 2),
                    ingreso_plan_ars=round(ingreso_plan, 2),
                    costo_directo_plan_ars=round(costo_directo_plan, 2),
                    costo_indirecto_plan_ars=round(costo_indirecto_plan, 2),
                    margen_plan_ars=round(ingreso_plan - costo_directo_plan - costo_indirecto_plan, 2),
                )
            )
    db.add_all(lot_campaign_rows)
    await db.flush()

    for lc, presupuesto in zip(lot_campaign_rows, budget_rows):
        presupuesto.lote_campania_id = lc.lote_campania_id
    db.add_all(budget_rows)
    state.lotes_campania = lot_campaign_rows
    state.presupuestos = budget_rows

    for lc in lot_campaign_rows:
        lot = next(item for item in state.lotes if item.lote_id == lc.lote_id)
        campania = next(item for item in state.campanias.values() if item.campania_id == lc.campania_id)
        establecimiento = next(est for est in state.establecimientos if est.establecimiento_id == lc.establecimiento_id)
        variety = next(var for var in state.variedades if var.variedad_id == lc.variedad_id)
        scenario = LOT_SCENARIOS.get(
            lot.codigo,
            {"yield_bias": 0.0, "quality_bias": 0.0, "hydric": "normal", "sanitary": "medium"},
        )

        harvest_start = lc.fecha_inicio_cosecha_estimada
        harvest_end = min(lc.fecha_fin_cosecha_estimada, CURRENT_DATE if campania.activa else lc.fecha_fin_cosecha_estimada)
        if harvest_end < harvest_start:
            harvest_end = harvest_start
        progress_ratio = 1.0
        scenario_result_factor = max(0.72, 0.99 + scenario["yield_bias"] * 1.05)
        actual_yield_kg_ha = (
            lc.objetivo_kg_ha
            * _campaign_factor(campania.codigo)
            * scenario_result_factor
            * state.rng.uniform(0.95, 1.04)
        )
        if campania.activa:
            expected_window_days = max(1, (lc.fecha_fin_cosecha_estimada - lc.fecha_inicio_cosecha_estimada).days + 1)
            elapsed_window_days = max(1, (harvest_end - harvest_start).days + 1)
            progress_ratio = min(1.0, elapsed_window_days / expected_window_days)
            actual_yield_kg_ha *= max(0.18, progress_ratio * state.rng.uniform(0.94, 1.06))
        total_harvest_kg = lot.superficie_ha * actual_yield_kg_ha

        scouting_start = max(campania.fecha_inicio, date(campania.fecha_inicio.year, 9, 1))
        scouting_end = CURRENT_DATE if campania.activa else campania.fecha_fin
        for event_date in _chunked_days(scouting_start, scouting_end, 14):
            pest = state.rng.choice(state.plagas + state.enfermedades)
            warm_humid = clima_lookup.get((lc.establecimiento_id, event_date), (0, 65))[1] > 70
            sanitary_factor = {"low": 0.82, "medium": 1.0, "high": 1.34}[scenario["sanitary"]]
            issue_window_factor = 1.0
            if QUALITY_ALERT_START <= event_date <= QUALITY_ALERT_END:
                issue_window_factor = 1.22 if establecimiento.codigo == "EC" else 1.46
                if scenario["sanitary"] == "high":
                    issue_window_factor += 0.18
            incidence = max(
                0.5,
                min(
                    28,
                    state.rng.uniform(1.2, 10.8)
                    * (1.35 if warm_humid else 0.92)
                    * sanitary_factor
                    * issue_window_factor,
                ),
            )
            severity = "alta" if incidence > 12 else "media" if incidence > 5 else "baja"
            alert = incidence > 9
            scouting_rows.append(
                ScoutingFact(
                    lote_campania_id=lc.lote_campania_id,
                    fecha_id=state.fecha_ids[event_date],
                    fecha_evento=event_date,
                    plaga_id=pest.plaga_id if isinstance(pest, PlagaDim) else None,
                    enfermedad_id=pest.enfermedad_id if isinstance(pest, EnfermedadDim) else None,
                    severidad=severity,
                    incidencia_pct=round(incidence, 2),
                    lotes_afectados_pct=round(min(100, incidence * state.rng.uniform(2.8, 5.0)), 2),
                    alerta=alert,
                    recomendacion="Aplicar corrección en próxima ventana" if alert else "Continuar monitoreo",
                )
            )
            if alert or (event_date.month in {11, 12, 1, 2} and state.rng.random() < (0.28 if scenario["sanitary"] == "low" else 0.42)):
                app_date = min(event_date + timedelta(days=state.rng.randint(2, 6)), CURRENT_DATE if campania.activa else campania.fecha_fin)
                app_cost = round(lot.superficie_ha * state.rng.uniform(38000, 92000), 2)
                application_rows.append(
                    AplicacionFitosanitariaFact(
                        lote_campania_id=lc.lote_campania_id,
                        fecha_id=state.fecha_ids[app_date],
                        fecha_aplicacion=app_date,
                        objetivo="Control preventivo" if not alert else "Corrección sanitaria",
                        producto=state.rng.choice(["Cobre tribásico", "Aceite mineral", "Abamectina", "Azoxystrobin"]),
                        ingrediente_activo=state.rng.choice(["Cobre", "Aceite", "Abamectina", "Azoxystrobin"]),
                        dosis_l_ha=round(state.rng.uniform(0.8, 2.1), 2),
                        volumen_caldo_l_ha=round(state.rng.uniform(900, 1800), 2),
                        costo_ars_ha=round(app_cost / lot.superficie_ha, 2),
                        estado="ejecutada",
                    )
                )
                cost_rows.append(
                    CostosDirectosFact(
                        lote_campania_id=lc.lote_campania_id,
                        fecha_id=state.fecha_ids[app_date],
                        fecha=app_date,
                        categoria="sanidad",
                        subcategoria="fitosanitarios",
                        monto_ars=app_cost,
                    )
                )

        water_start = max(campania.fecha_inicio, date(campania.fecha_inicio.year, 9, 1))
        water_end = CURRENT_DATE if campania.activa else date(_campaign_second_year(campania), 3, 31)
        for week_date in _chunked_days(water_start, water_end, 7):
            week_precip = sum(clima_lookup.get((lc.establecimiento_id, probe), (0, 65))[0] for probe in _daterange(week_date - timedelta(days=6), week_date))
            week_et0 = sum(et0_lookup.get((lc.establecimiento_id, probe), 0) for probe in _daterange(week_date - timedelta(days=6), week_date))
            required_m3 = max(0, week_et0 * lot.superficie_ha * 8.8)
            bias = {"normal": 1.0, "déficit": 0.82, "exceso": 1.2}[lc.condicion_hidrica]
            rain_credit = min(required_m3 * 0.65, week_precip * lot.superficie_ha * 6.2)
            baseline_need = required_m3 * (0.72 if week_date.month in {9, 10, 11} else 0.62 if week_date.month in {12, 1, 2, 3} else 0.55)
            net_need = max(required_m3 * 0.18, baseline_need - rain_credit)
            applied_total = max(required_m3 * 0.1, net_need * bias)
            applied_total *= state.rng.uniform(0.92, 1.08)
            balance = applied_total - required_m3
            estado = "déficit" if balance < -required_m3 * 0.12 else "exceso" if balance > required_m3 * 0.14 else "normal"
            requerimiento_rows.append(
                RequerimientoHidricoFact(
                    lote_campania_id=lc.lote_campania_id,
                    fecha_id=state.fecha_ids[week_date],
                    fecha=week_date,
                    m3_requeridos=round(required_m3, 2),
                    m3_aportados=round(applied_total, 2),
                    balance_hidrico_m3=round(balance, 2),
                    estado=estado,
                )
            )
            for event_offset in (1, 4):
                irrigation_date = week_date - timedelta(days=7 - event_offset)
                if irrigation_date < water_start or irrigation_date > water_end:
                    continue
                portion = applied_total * (0.56 if event_offset == 1 else 0.44)
                if portion <= 0:
                    continue
                kwh = portion * state.rng.uniform(0.18, 0.25)
                cost = kwh * (70 + irrigation_date.month * 3.2)
                riego_rows.append(
                    RiegoFact(
                        lote_campania_id=lc.lote_campania_id,
                        fecha_id=state.fecha_ids[irrigation_date],
                        fecha_riego=irrigation_date,
                        m3_aplicados=round(portion, 2),
                        m3_ha=round(portion / lot.superficie_ha, 2),
                        horas_riego=round(max(2.8, portion / 120), 2),
                        energia_kwh=round(kwh, 2),
                        costo_ars=round(cost, 2),
                    )
                )
                cost_rows.append(
                    CostosDirectosFact(
                        lote_campania_id=lc.lote_campania_id,
                        fecha_id=state.fecha_ids[irrigation_date],
                        fecha=irrigation_date,
                        categoria="riego",
                        subcategoria="bombeo",
                        monto_ars=round(cost, 2),
                    )
                )
            if week_date.isocalendar().week % 2 == 0:
                fert_date = week_date
                fert_cost = round(lot.superficie_ha * state.rng.uniform(28000, 52000), 2)
                fertirriego_rows.append(
                    FertirriegoFact(
                        lote_campania_id=lc.lote_campania_id,
                        fecha_id=state.fecha_ids[fert_date],
                        fecha_fertirriego=fert_date,
                        nutriente=state.rng.choice(["Nitrógeno", "Potasio", "Calcio"]),
                        kg_aplicados=round(lot.superficie_ha * state.rng.uniform(8, 22), 2),
                        m3_aplicados=round(applied_total * state.rng.uniform(0.35, 0.6), 2),
                        costo_ars=fert_cost,
                    )
                )
                cost_rows.append(
                    CostosDirectosFact(
                        lote_campania_id=lc.lote_campania_id,
                        fecha_id=state.fecha_ids[fert_date],
                        fecha=fert_date,
                        categoria="fertirriego",
                        subcategoria="nutrición",
                        monto_ars=fert_cost,
                    )
                )

        harvest_step_days = 1 if campania.activa else 2
        harvest_days = list(_chunked_days(harvest_start, harvest_end, harvest_step_days))
        if not harvest_days:
            harvest_days = [harvest_start]
        weights = []
        center = len(harvest_days) / 2
        for idx in range(len(harvest_days)):
            distance = (idx - center) / max(1, len(harvest_days) / 3.4)
            weights.append(math.exp(-(distance ** 2)))
        weight_sum = sum(weights)
        cumulative_harvest = 0.0
        cumulative_received = 0.0
        exportable_acc = 0.0
        industry_acc = 0.0
        discard_acc = 0.0

        for harvest_date, weight in zip(harvest_days, weights):
            harvested = total_harvest_kg * (weight / weight_sum) * state.rng.uniform(0.92, 1.08)
            field_damage = state.rng.uniform(0.012, 0.038)
            received = harvested * (1 - field_damage)
            labor_cost = harvested * state.rng.uniform(26, 39)
            batches = max(14, int(harvested / 1200))
            cosecha_rows.append(
                CosechaFact(
                    lote_campania_id=lc.lote_campania_id,
                    fecha_id=state.fecha_ids[harvest_date],
                    fecha_cosecha=harvest_date,
                    kg_cosechados=round(harvested, 2),
                    jornales=round(harvested / 1750, 2),
                    cuadrillas=state.rng.randint(2, 5),
                    bins_cosechados=batches,
                    costo_cosecha_ars=round(labor_cost, 2),
                    fruta_danada_pct=round(field_damage * 100, 2),
                )
            )
            cost_rows.append(
                CostosDirectosFact(
                    lote_campania_id=lc.lote_campania_id,
                    fecha_id=state.fecha_ids[harvest_date],
                    fecha=harvest_date,
                    categoria="cosecha",
                    subcategoria="jornales",
                    monto_ars=round(labor_cost, 2),
                )
            )
            cumulative_harvest += harvested
            cumulative_received += received
            rain_mm, humidity_pct = clima_lookup.get((lc.establecimiento_id, harvest_date), (0, 65))
            weather_penalty = 0.0
            if rain_mm > 8:
                weather_penalty -= 0.026
            if rain_mm > 18:
                weather_penalty -= 0.032
            if humidity_pct > 76:
                weather_penalty -= 0.02
            if humidity_pct < 54:
                weather_penalty += 0.012
            if QUALITY_ALERT_START <= harvest_date <= QUALITY_ALERT_END:
                weather_penalty -= 0.03 if establecimiento.codigo == "EC" else 0.055
                if scenario["sanitary"] == "high":
                    weather_penalty -= 0.025
            seasonal_adjustment = 0.03 * math.sin((harvest_date.timetuple().tm_yday / 365) * 2 * math.pi + lot_quality_bias * 4)
            quality_score = max(
                0.32,
                min(
                    0.81,
                    (lc.objetivo_packout_pct / 100)
                    + lot_quality_bias
                    + seasonal_adjustment
                    + weather_penalty
                    + state.rng.uniform(-0.08, 0.08),
                ),
            )
            local_score = max(0.08, min(0.22, 0.14 + state.rng.uniform(-0.035, 0.035) - weather_penalty * 0.4))
            industry_score = max(0.12, min(0.36, 0.2 + state.rng.uniform(-0.06, 0.06) - weather_penalty * 0.9))
            discard_score = max(0.03, min(0.12, 1 - quality_score - local_score - industry_score))
            parts = _safe_pct(quality_score, local_score, industry_score, discard_score)
            exportable_acc += received * parts[0]
            industry_acc += received * parts[2]
            discard_acc += received * parts[3]
            split_count = 1
            if received > 7000:
                split_count += 1
            if received > 14500:
                split_count += 1
            weights = _safe_pct(*[state.rng.uniform(0.85, 1.2) for _ in range(split_count)])
            received_base_date = min(harvest_date + timedelta(days=1), CURRENT_DATE if campania.activa else harvest_date + timedelta(days=1))
            for idx, split_weight in enumerate(weights):
                split_received = received * split_weight
                received_date = min(
                    received_base_date + timedelta(days=min(idx, 1)),
                    CURRENT_DATE if campania.activa else received_base_date + timedelta(days=min(idx, 1)),
                )
                quality_batches.append(
                    {
                        "lote_campania_id": lc.lote_campania_id,
                        "establecimiento_id": lc.establecimiento_id,
                        "harvest_date": harvest_date,
                        "received_date": received_date,
                        "received_kg": round(split_received, 2),
                        "packout_export_pct": round(parts[0] * 100, 2),
                        "local_pct": round(parts[1] * 100, 2),
                        "industry_pct": round(parts[2] * 100, 2),
                        "discard_pct": round(parts[3] * 100, 2),
                        "variedad_id": lc.variedad_id,
                        "processing_est": _processing_establishment(state, lc.establecimiento_id),
                        "lot_code": lot.codigo,
                        "sanitary_level": scenario["sanitary"],
                    }
                )

        deviation_target_kg_ha = lc.objetivo_kg_ha * (progress_ratio if campania.activa else 1.0)
        rendimiento_rows.append(
            RendimientoLoteFact(
                lote_campania_id=lc.lote_campania_id,
                kg_totales=round(cumulative_harvest, 2),
                kg_ha=round(cumulative_harvest / lot.superficie_ha, 2),
                fruta_exportable_pct=round((exportable_acc / cumulative_received) * 100, 2) if cumulative_received else 0,
                fruta_industria_pct=round((industry_acc / cumulative_received) * 100, 2) if cumulative_received else 0,
                fruta_descarte_pct=round((discard_acc / cumulative_received) * 100, 2) if cumulative_received else 0,
                semana_pico=harvest_days[len(harvest_days) // 2].isocalendar().week,
                desvio_vs_objetivo_pct=round(
                    ((cumulative_harvest / lot.superficie_ha) - deviation_target_kg_ha) / deviation_target_kg_ha * 100,
                    2,
                )
                if deviation_target_kg_ha
                else 0,
            )
        )

        ambience_shares = _safe_pct(state.rng.uniform(0.22, 0.34), state.rng.uniform(0.28, 0.4), state.rng.uniform(0.22, 0.38))
        ambience_names = ["Bajo", "Medio", "Loma"]
        ambience_yield_factors = [0.9 + lot_yield_bias, 1 + lot_yield_bias * 0.4, 1.08 + lot_yield_bias]
        for name, share, factor in zip(ambience_names, ambience_shares, ambience_yield_factors):
            rendimiento_amb_rows.append(
                RendimientoAmbienteFact(
                    lote_campania_id=lc.lote_campania_id,
                    ambiente=name,
                    superficie_ha=round(lot.superficie_ha * share, 2),
                    kg_ha=round((cumulative_harvest / lot.superficie_ha) * factor, 2) if lot.superficie_ha else 0,
                    packout_pct=round(max(35, min(78, lc.objetivo_packout_pct + factor * 4 + state.rng.uniform(-4, 4))), 2),
                    observacion=f"Ambiente {name.lower()} del lote",
                )
            )

    db.add_all(
        scouting_rows
        + application_rows
        + riego_rows
        + fertirriego_rows
        + requerimiento_rows
        + cosecha_rows
        + rendimiento_rows
        + rendimiento_amb_rows
        + cost_rows
    )
    await db.flush()
    return quality_batches


async def _seed_quality_packhouse_and_commercial(db: AsyncSession, state: LemonSeedState, quality_batches: list[dict]):
    recepcion_rows: list[RecepcionFrutaFact] = []
    clasificacion_rows: list[ClasificacionCalidadFact] = []
    packout_rows: list[PackoutFact] = []
    rechazo_rows: list[RechazoFact] = []
    packhouse_rows: list[PackhouseTurnoFact] = []
    downtime_rows: list[DowntimePackhouseFact] = []
    labor_rows: list[ManoObraPackhouseFact] = []
    consumo_rows: list[ConsumoPackhouseFact] = []
    maintenance_rows: list[MantenimientoPackhouseFact] = []
    indirect_rows: list[CostosIndirectosFact] = []
    precio_rows: list[PrecioVentaFact] = []
    contratos: list[ContratoVentaFact] = []
    embarques: list[EmbarqueFact] = []
    liquidaciones: list[LiquidacionFact] = []
    cuentas: list[CuentasCobrarFact] = []
    cobranzas: list[CobranzasFact] = []
    stock_rows: list[StockFinalFact] = []
    packhouse_cost_rows: list[CostosDirectosFact] = []

    destinos = {destino.codigo: destino for destino in state.destinos}
    calibres_export = [calibre for calibre in state.calibres if calibre.codigo in {"95", "115", "138"}]
    calibres_local = [calibre for calibre in state.calibres if calibre.codigo in {"138", "165", "200"}]
    defect_pool = state.defectos
    turnos_cycle = state.turnos
    lineas_por_est: dict[int, list[LineaEmpaqueDim]] = defaultdict(list)
    for linea in state.lineas:
        lineas_por_est[linea.establecimiento_id].append(linea)
    lineas_por_codigo = {linea.codigo: linea for linea in state.lineas}

    reference_prices: dict[tuple[date, int, int], float] = {}
    local_market = next(mercado for mercado in state.mercados if mercado.codigo == "ARG")
    industry_market = next(mercado for mercado in state.mercados if mercado.codigo == "IND")
    export_channel = next(canal for canal in state.canales if canal.codigo == "FRESCO_EXP")
    local_channel = next(canal for canal in state.canales if canal.codigo == "FRESCO_LOC")
    industry_channel = next(canal for canal in state.canales if canal.codigo == "INDUSTRIA")

    for monday in _chunked_days(date(2023, 1, 2), CURRENT_DATE, 7):
        weeks = (monday - date(2023, 1, 2)).days / 7
        export_market_prices = {
            "EU": 1090 + weeks * 1.1 + 45 * math.sin(weeks / 7.2) + state.rng.uniform(-24, 24),
            "USA": 1240 + weeks * 1.4 + 62 * math.sin(weeks / 8.6) + state.rng.uniform(-28, 28),
            "MEA": 975 + weeks * 0.95 + 38 * math.sin(weeks / 6.8) + state.rng.uniform(-24, 24),
            "RUS": 920 + weeks * 0.82 + 32 * math.sin(weeks / 6.4) + state.rng.uniform(-22, 22),
        }
        for mercado in state.mercados:
            if mercado.codigo in export_market_prices:
                price = max(780, export_market_prices[mercado.codigo])
                precio_rows.append(
                    PrecioVentaFact(
                        fecha_id=state.fecha_ids[monday],
                        fecha=monday,
                        mercado_id=mercado.mercado_id,
                        canal_id=export_channel.canal_id,
                        precio_promedio_usd_tn=round(price, 2),
                        volumen_kg=round(state.rng.uniform(180000, 420000), 2),
                    )
                )
                reference_prices[(monday, mercado.mercado_id, export_channel.canal_id)] = round(price, 2)
        local_price = max(320, 420 + weeks * 0.6 + 15 * math.sin(weeks / 5.2) + state.rng.uniform(-10, 10))
        precio_rows.append(
            PrecioVentaFact(
                fecha_id=state.fecha_ids[monday],
                fecha=monday,
                mercado_id=local_market.mercado_id,
                canal_id=local_channel.canal_id,
                precio_promedio_usd_tn=round(local_price, 2),
                volumen_kg=round(state.rng.uniform(75000, 140000), 2),
            )
        )
        reference_prices[(monday, local_market.mercado_id, local_channel.canal_id)] = round(local_price, 2)
        industry_price = max(180, 255 + weeks * 0.45 + 12 * math.sin(weeks / 4.8) + state.rng.uniform(-8, 8))
        precio_rows.append(
            PrecioVentaFact(
                fecha_id=state.fecha_ids[monday],
                fecha=monday,
                mercado_id=industry_market.mercado_id,
                canal_id=industry_channel.canal_id,
                precio_promedio_usd_tn=round(industry_price, 2),
                volumen_kg=round(state.rng.uniform(120000, 260000), 2),
            )
        )
        reference_prices[(monday, industry_market.mercado_id, industry_channel.canal_id)] = round(industry_price, 2)

    db.add_all(precio_rows)
    await db.flush()

    inbound_by_day: dict[tuple[date, int, int], float] = defaultdict(float)
    processing_totals: dict[tuple[date, int, int], dict[str, float]] = defaultdict(lambda: {"kg": 0.0, "receptions": 0.0})

    for batch in quality_batches:
        recepcion = RecepcionFrutaFact(
            lote_campania_id=batch["lote_campania_id"],
            fecha_id=state.fecha_ids[batch["received_date"]],
            fecha_recepcion=batch["received_date"],
            kg_recibidos=batch["received_kg"],
            bins_recibidos=max(8, int(batch["received_kg"] / 1200)),
            temperatura_fruta_c=round(state.rng.uniform(8.5, 16.5), 2),
            brix=round(state.rng.uniform(6.2, 8.1), 2),
            acidez=round(state.rng.uniform(5.1, 7.0), 2),
            observaciones="Recepción conforme",
        )
        recepcion_rows.append(recepcion)
    db.add_all(recepcion_rows)
    await db.flush()

    fresh_cost_per_kg = 52.0
    processing_by_date_line_turn: dict[tuple[date, int, int], float] = defaultdict(float)

    for batch, recepcion in zip(quality_batches, recepcion_rows):
        processing_est = batch["processing_est"]
        line = _choose_processing_line(
            state,
            lineas_por_est,
            lineas_por_codigo,
            processing_est,
            batch["received_date"],
        )
        turno = turnos_cycle[(batch["received_date"].toordinal() + recepcion.recepcion_id) % len(turnos_cycle)]
        received = batch["received_kg"]
        export_kg = received * batch["packout_export_pct"] / 100
        local_kg = received * batch["local_pct"] / 100
        industry_kg = received * batch["industry_pct"] / 100
        discard_kg = received * batch["discard_pct"] / 100
        quality_window = QUALITY_ALERT_START <= batch["received_date"] <= QUALITY_ALERT_END
        line_incident = line.codigo == "EC-L2" and PACKHOUSE_INCIDENT_START <= batch["received_date"] <= PACKHOUSE_INCIDENT_END
        packout_pct_display = batch["packout_export_pct"]
        if quality_window:
            packout_pct_display -= state.rng.uniform(2.5, 5.5)
        if line_incident:
            packout_pct_display -= state.rng.uniform(4.0, 8.5)
        packout_pct_display = round(max(34, min(82, packout_pct_display)), 2)

        export_cal_shares = _safe_pct(state.rng.uniform(0.24, 0.38), state.rng.uniform(0.28, 0.4), state.rng.uniform(0.22, 0.34))
        local_cal_shares = _safe_pct(state.rng.uniform(0.34, 0.45), state.rng.uniform(0.28, 0.36), state.rng.uniform(0.18, 0.28))

        for calibre, share in zip(calibres_export, export_cal_shares):
            kg = round(export_kg * share, 2)
            clasificacion_rows.append(
                ClasificacionCalidadFact(
                    recepcion_id=recepcion.recepcion_id,
                    fecha_id=state.fecha_ids[batch["received_date"]],
                    fecha_clasificacion=batch["received_date"],
                    destino_id=destinos["EXP"].destino_id,
                    calibre_id=calibre.calibre_id,
                    kg_clasificados=kg,
                    porcentaje=round((kg / received) * 100, 2),
                    color_indice=round(state.rng.uniform(4.8, 6.4), 2),
                    firmeza=round(state.rng.uniform(6.6, 8.3), 2),
                )
            )
            packout_rows.append(
                PackoutFact(
                    recepcion_id=recepcion.recepcion_id,
                    fecha_id=state.fecha_ids[batch["received_date"]],
                    fecha_proceso=batch["received_date"],
                    linea_id=line.linea_id,
                    turno_id=turno.turno_id,
                    destino_id=destinos["EXP"].destino_id,
                    calibre_id=calibre.calibre_id,
                    kg_entrada=kg,
                    kg_salida=kg,
                    cajas=max(1, int(kg / 18)),
                    packout_pct=packout_pct_display,
                    eficiencia_pct=_line_packout_efficiency(
                        state,
                        line,
                        "EXP",
                        batch["received_date"],
                        quality_window=quality_window,
                        line_incident=line_incident,
                    ),
                )
            )
            inbound_by_day[(batch["received_date"], state.deposito_fresco_por_est[processing_est], destinos["EXP"].destino_id)] += kg
            processing_by_date_line_turn[(batch["received_date"], line.linea_id, turno.turno_id)] += kg

        for calibre, share in zip(calibres_local, local_cal_shares):
            kg = round(local_kg * share, 2)
            clasificacion_rows.append(
                ClasificacionCalidadFact(
                    recepcion_id=recepcion.recepcion_id,
                    fecha_id=state.fecha_ids[batch["received_date"]],
                    fecha_clasificacion=batch["received_date"],
                    destino_id=destinos["LOC"].destino_id,
                    calibre_id=calibre.calibre_id,
                    kg_clasificados=kg,
                    porcentaje=round((kg / received) * 100, 2),
                    color_indice=round(state.rng.uniform(4.1, 5.8), 2),
                    firmeza=round(state.rng.uniform(5.8, 7.4), 2),
                )
            )
            packout_rows.append(
                PackoutFact(
                    recepcion_id=recepcion.recepcion_id,
                    fecha_id=state.fecha_ids[batch["received_date"]],
                    fecha_proceso=batch["received_date"],
                    linea_id=line.linea_id,
                    turno_id=turno.turno_id,
                    destino_id=destinos["LOC"].destino_id,
                    calibre_id=calibre.calibre_id,
                    kg_entrada=kg,
                    kg_salida=kg,
                    cajas=max(1, int(kg / 18)),
                    packout_pct=packout_pct_display,
                    eficiencia_pct=_line_packout_efficiency(
                        state,
                        line,
                        "LOC",
                        batch["received_date"],
                        quality_window=quality_window,
                        line_incident=line_incident,
                    ),
                )
            )
            inbound_by_day[(batch["received_date"], state.deposito_fresco_por_est[processing_est], destinos["LOC"].destino_id)] += kg
            processing_by_date_line_turn[(batch["received_date"], line.linea_id, turno.turno_id)] += kg

        clasificacion_rows.append(
            ClasificacionCalidadFact(
                recepcion_id=recepcion.recepcion_id,
                fecha_id=state.fecha_ids[batch["received_date"]],
                fecha_clasificacion=batch["received_date"],
                destino_id=destinos["IND"].destino_id,
                calibre_id=None,
                kg_clasificados=round(industry_kg, 2),
                porcentaje=round((industry_kg / received) * 100, 2),
                color_indice=round(state.rng.uniform(3.2, 4.6), 2),
                firmeza=round(state.rng.uniform(4.2, 6.0), 2),
            )
        )
        packout_rows.append(
            PackoutFact(
                recepcion_id=recepcion.recepcion_id,
                fecha_id=state.fecha_ids[batch["received_date"]],
                fecha_proceso=batch["received_date"],
                linea_id=line.linea_id,
                turno_id=turno.turno_id,
                destino_id=destinos["IND"].destino_id,
                calibre_id=None,
                kg_entrada=round(industry_kg, 2),
                kg_salida=round(industry_kg, 2),
                cajas=0,
                packout_pct=packout_pct_display,
                eficiencia_pct=_line_packout_efficiency(
                    state,
                    line,
                    "IND",
                    batch["received_date"],
                    quality_window=quality_window,
                    line_incident=line_incident,
                ),
            )
        )
        inbound_by_day[(batch["received_date"], state.deposito_industria_por_est[processing_est], destinos["IND"].destino_id)] += industry_kg
        processing_by_date_line_turn[(batch["received_date"], line.linea_id, turno.turno_id)] += industry_kg

        clasificacion_rows.append(
            ClasificacionCalidadFact(
                recepcion_id=recepcion.recepcion_id,
                fecha_id=state.fecha_ids[batch["received_date"]],
                fecha_clasificacion=batch["received_date"],
                destino_id=destinos["DSC"].destino_id,
                calibre_id=None,
                kg_clasificados=round(discard_kg, 2),
                porcentaje=round((discard_kg / received) * 100, 2),
                color_indice=round(state.rng.uniform(2.4, 3.8), 2),
                firmeza=round(state.rng.uniform(3.4, 5.1), 2),
            )
        )
        if quality_window and batch["sanitary_level"] == "high":
            defective_split = _safe_pct(0.18, 0.22, 0.34, 0.26)
        else:
            defective_split = _safe_pct(
                state.rng.uniform(0.18, 0.32),
                state.rng.uniform(0.14, 0.24),
                state.rng.uniform(0.12, 0.22),
                state.rng.uniform(0.12, 0.22),
            )
        for defect, share in zip(defect_pool[:4], defective_split):
            kg_def = round(discard_kg * share, 2)
            rechazo_rows.append(
                RechazoFact(
                    recepcion_id=recepcion.recepcion_id,
                    fecha_id=state.fecha_ids[batch["received_date"]],
                    fecha_rechazo=batch["received_date"],
                    defecto_id=defect.defecto_id,
                    kg_rechazo=kg_def,
                    porcentaje_rechazo=round((kg_def / received) * 100, 2),
                )
            )

        packhouse_cost_rows.append(
            CostosDirectosFact(
                lote_campania_id=batch["lote_campania_id"],
                fecha_id=state.fecha_ids[batch["received_date"]],
                fecha=batch["received_date"],
                categoria="packhouse",
                subcategoria="proceso y empaque",
                monto_ars=round(received * fresh_cost_per_kg, 2),
            )
        )

    db.add_all(clasificacion_rows + packout_rows + rechazo_rows + packhouse_cost_rows)
    await db.flush()

    for (process_date, linea_id, turno_id), kg in processing_by_date_line_turn.items():
        linea = next(item for item in state.lineas if item.linea_id == linea_id)
        hours_programmed, productive, downtime, efficiency = _packhouse_shift_metrics(state, linea, process_date, kg)
        line_incident = linea.codigo == "EC-L2" and PACKHOUSE_INCIDENT_START <= process_date <= PACKHOUSE_INCIDENT_END
        line_bias = _line_performance_bias(linea)
        operarios = state.rng.randint(17, 24) if line_bias >= 1.0 else state.rng.randint(19, 28)
        packhouse_rows.append(
            PackhouseTurnoFact(
                fecha_id=state.fecha_ids[process_date],
                fecha=process_date,
                establecimiento_id=linea.establecimiento_id,
                linea_id=linea.linea_id,
                turno_id=turno_id,
                kg_procesados=round(kg, 2),
                horas_programadas=hours_programmed,
                horas_productivas=round(productive, 2),
                horas_downtime=round(downtime, 2),
                eficiencia_pct=round(efficiency, 2),
                toneladas_hora=round((kg / 1000) / productive if productive else 0, 2),
                operarios=operarios,
            )
        )
        labor_rows.append(
            ManoObraPackhouseFact(
                fecha_id=state.fecha_ids[process_date],
                fecha=process_date,
                linea_id=linea_id,
                turno_id=turno_id,
                operarios=operarios,
                horas_hombre=round(operarios * productive, 2),
                costo_ars=round(operarios * productive * state.rng.uniform(6500, 8400), 2),
            )
        )
        consumo_rows.extend(
            [
                ConsumoPackhouseFact(fecha_id=state.fecha_ids[process_date], fecha=process_date, linea_id=linea_id, rubro="energía", unidad="kWh", cantidad=round(kg * state.rng.uniform(0.12, 0.18), 2), costo_ars=round(kg * state.rng.uniform(3.5, 5.3), 2)),
                ConsumoPackhouseFact(fecha_id=state.fecha_ids[process_date], fecha=process_date, linea_id=linea_id, rubro="cartón", unidad="cajas", cantidad=max(1, int(kg / 18)), costo_ars=round(kg * state.rng.uniform(6.2, 8.4), 2)),
                ConsumoPackhouseFact(fecha_id=state.fecha_ids[process_date], fecha=process_date, linea_id=linea_id, rubro="cera", unidad="kg", cantidad=round(kg * state.rng.uniform(0.003, 0.006), 2), costo_ars=round(kg * state.rng.uniform(1.2, 2.2), 2)),
            ]
        )
        if downtime > 0.45:
            downtime_rows.append(
                DowntimePackhouseFact(
                    fecha_id=state.fecha_ids[process_date],
                    fecha=process_date,
                    linea_id=linea_id,
                    turno_id=turno_id,
                    motivo=(
                        state.rng.choice(["falla calibrador", "atasco en cepillado", "mantenimiento correctivo", "desalineación de cinta"])
                        if line_incident
                        else state.rng.choice(["falla eléctrica", "cambio de formato", "mantenimiento correctivo", "falta de fruta"])
                    ),
                    minutos=round(downtime * 60, 2),
                    criticidad="alta" if line_incident or downtime > 1.2 else "media",
                )
            )
        if line_incident or state.rng.random() < 0.18:
            maintenance_rows.append(
                MantenimientoPackhouseFact(
                    fecha_id=state.fecha_ids[process_date],
                    fecha=process_date,
                    linea_id=linea_id,
                    tipo=state.rng.choice(["lubricación", "rodillos", "sensor óptico", "cinta", "tolva alimentación"]),
                    preventivo=False if line_incident else state.rng.random() < 0.65,
                    minutos_intervencion=round(state.rng.uniform(55, 145) if line_incident else state.rng.uniform(25, 110), 2),
                    costo_ars=round(state.rng.uniform(420000, 880000) if line_incident else state.rng.uniform(180000, 640000), 2),
                )
            )

    current_month = date(2022, 7, 1)
    while current_month <= date(2026, 3, 1):
        campaign = next(c for c in state.campanias.values() if c.fecha_inicio <= current_month <= c.fecha_fin)
        for establecimiento in state.establecimientos:
            indirect_rows.extend(
                [
                    CostosIndirectosFact(campania_id=campaign.campania_id, establecimiento_id=establecimiento.establecimiento_id, fecha_id=state.fecha_ids[current_month], fecha=current_month, categoria="administración", monto_ars=round(state.rng.uniform(4200000, 7600000), 2)),
                    CostosIndirectosFact(campania_id=campaign.campania_id, establecimiento_id=establecimiento.establecimiento_id, fecha_id=state.fecha_ids[current_month], fecha=current_month, categoria="energía packhouse", monto_ars=round(state.rng.uniform(1800000, 4600000), 2) if establecimiento.packhouse_activo else round(state.rng.uniform(450000, 1200000), 2)),
                    CostosIndirectosFact(campania_id=campaign.campania_id, establecimiento_id=establecimiento.establecimiento_id, fecha_id=state.fecha_ids[current_month], fecha=current_month, categoria="infraestructura", monto_ars=round(state.rng.uniform(1250000, 2500000), 2)),
                ]
            )
        current_month = date(current_month.year + (current_month.month // 12), (current_month.month % 12) + 1, 1)

    db.add_all(packhouse_rows + downtime_rows + labor_rows + consumo_rows + maintenance_rows + indirect_rows)
    await db.flush()

    fresh_clients = {
        "EU": next(cliente for cliente in state.clientes if cliente.codigo == "EU_CITRUS"),
        "USA": next(cliente for cliente in state.clientes if cliente.codigo == "US_FRESH"),
        "MEA": next(cliente for cliente in state.clientes if cliente.codigo == "ME_CITRUS"),
        "RUS": next(cliente for cliente in state.clientes if cliente.codigo == "RU_MARKET"),
    }
    local_client = next(cliente for cliente in state.clientes if cliente.codigo == "AR_MAYOR")
    industry_client = next(cliente for cliente in state.clientes if cliente.codigo == "IND_JUGOS")
    market_by_code = {mercado.codigo: mercado for mercado in state.mercados}

    stock_balances: dict[tuple[int, int], float] = defaultdict(float)
    open_contracts: list[ContratoVentaFact] = []

    operation_start = min(batch["received_date"] for batch in quality_batches)
    for current in _daterange(operation_start, CURRENT_DATE):
        for (movement_date, deposito_id, destino_id), incoming in list(inbound_by_day.items()):
            if movement_date == current:
                stock_balances[(deposito_id, destino_id)] += incoming

        weekday = current.weekday()
        shipments_today: list[tuple[int, int, float, ClienteDim, MercadoDim, CanalDim]] = []
        for processing_est in state.deposito_fresco_por_est:
            fresh_depot = state.deposito_fresco_por_est[processing_est]
            industry_depot = state.deposito_industria_por_est[processing_est]
            export_available = stock_balances[(fresh_depot, destinos["EXP"].destino_id)]
            local_available = stock_balances[(fresh_depot, destinos["LOC"].destino_id)]
            industry_available = stock_balances[(industry_depot, destinos["IND"].destino_id)]

            if weekday in {0, 1, 3, 4} and export_available > 12000:
                for market_code, share in [("EU", 0.45), ("USA", 0.22), ("MEA", 0.18), ("RUS", 0.15)]:
                    volume = export_available * share * state.rng.uniform(0.14, 0.24)
                    if volume > 3000:
                        dispatches = 2 if market_code in {"EU", "USA"} and volume > 7000 else 1
                        for _ in range(dispatches):
                            part = volume / dispatches * state.rng.uniform(0.94, 1.06)
                            if part > 2500:
                                shipments_today.append((fresh_depot, destinos["EXP"].destino_id, part, fresh_clients[market_code], market_by_code[market_code], export_channel))
                                export_available -= part
            if weekday in {1, 2, 4} and local_available > 6000:
                volume = local_available * state.rng.uniform(0.18, 0.3)
                dispatches = 2 if volume > 9000 else 1
                for _ in range(dispatches):
                    part = volume / dispatches * state.rng.uniform(0.95, 1.05)
                    shipments_today.append((fresh_depot, destinos["LOC"].destino_id, part, local_client, local_market, local_channel))
            if weekday in {1, 2, 3, 5} and industry_available > 18000:
                volume = industry_available * state.rng.uniform(0.22, 0.4)
                dispatches = 2 if volume > 22000 else 1
                for _ in range(dispatches):
                    part = volume / dispatches * state.rng.uniform(0.94, 1.06)
                    shipments_today.append((industry_depot, destinos["IND"].destino_id, part, industry_client, industry_market, industry_channel))

        for deposito_id, destino_id, proposed_volume, cliente, mercado, canal in shipments_today:
            available = stock_balances[(deposito_id, destino_id)]
            volume = min(available, round(proposed_volume, 2))
            if volume < 3500:
                continue
            stock_balances[(deposito_id, destino_id)] -= volume
            campaign = next(c for c in state.campanias.values() if c.fecha_inicio <= current <= c.fecha_fin)
            contract = next(
                (
                    item for item in open_contracts
                    if item.campania_id == campaign.campania_id
                    and item.cliente_id == cliente.cliente_id
                    and item.mercado_id == mercado.mercado_id
                    and item.canal_id == canal.canal_id
                    and item.kg_pendientes >= volume
                ),
                None,
            )
            if contract is None:
                objective_price = _nearest_week_price(reference_prices, current, mercado.mercado_id, canal.canal_id)
                contract = ContratoVentaFact(
                    campania_id=campaign.campania_id,
                    cliente_id=cliente.cliente_id,
                    mercado_id=mercado.mercado_id,
                    canal_id=canal.canal_id,
                    fecha_contrato=max(campaign.fecha_inicio, current - timedelta(days=state.rng.randint(10, 28))),
                    estado="pendiente",
                    kg_contratados=round(volume * state.rng.uniform(1.6, 2.7), 2),
                    kg_entregados=0,
                    kg_pendientes=0,
                    precio_objetivo_usd_tn=round(objective_price * state.rng.uniform(0.98, 1.04), 2),
                    moneda="USD",
                    condicion_pago_dias=state.rng.choice([15, 21, 30, 45]),
                )
                contract.kg_pendientes = contract.kg_contratados
                contratos.append(contract)
                open_contracts.append(contract)
                db.add(contract)
                await db.flush()
            contract.kg_entregados = round(contract.kg_entregados + volume, 2)
            contract.kg_pendientes = round(max(0, contract.kg_contratados - contract.kg_entregados), 2)
            contract.estado = "entregado" if contract.kg_pendientes <= 0 else "pendiente"
            realized_price = _nearest_week_price(reference_prices, current, mercado.mercado_id, canal.canal_id) * state.rng.uniform(0.97, 1.03)
            boxes = max(1, int(volume / 18))
            embarque = EmbarqueFact(
                contrato_venta_id=contract.contrato_venta_id,
                fecha_id=state.fecha_ids[current],
                fecha_embarque=current,
                cliente_id=cliente.cliente_id,
                mercado_id=mercado.mercado_id,
                canal_id=canal.canal_id,
                kg_embarcados=round(volume, 2),
                cajas=boxes,
                precio_realizado_usd_tn=round(realized_price, 2),
                estado_logistico="embarcado",
                estado_cobro="pendiente",
            )
            embarques.append(embarque)
            db.add(embarque)
            await db.flush()

            liquidation_date = min(current + timedelta(days=7 if canal.canal_id != export_channel.canal_id else state.rng.randint(12, 22)), CURRENT_DATE)
            fx = state.latest_tipo_cambio.get(liquidation_date, state.latest_tipo_cambio[max(state.latest_tipo_cambio)])
            gross_usd = volume / 1000 * realized_price
            discounts = gross_usd * state.rng.uniform(0.045, 0.085)
            net_usd = gross_usd - discounts
            liquidation = LiquidacionFact(
                embarque_id=embarque.embarque_id,
                fecha_id=state.fecha_ids[liquidation_date],
                fecha_liquidacion=liquidation_date,
                importe_bruto_usd=round(gross_usd, 2),
                descuentos_usd=round(discounts, 2),
                importe_neto_usd=round(net_usd, 2),
                tipo_cambio_aplicado=fx,
                importe_neto_ars=round(net_usd * fx, 2),
                estado="emitida",
            )
            liquidaciones.append(liquidation)
            db.add(liquidation)
            await db.flush()

            due_date = liquidation_date + timedelta(days=contract.condicion_pago_dias)
            account = CuentasCobrarFact(
                contrato_venta_id=contract.contrato_venta_id,
                cliente_id=cliente.cliente_id,
                fecha_emision=liquidation_date,
                fecha_vencimiento=due_date,
                monto_original_ars=liquidation.importe_neto_ars,
                saldo_abierto_ars=liquidation.importe_neto_ars,
                estado="pendiente",
            )
            cuentas.append(account)
            db.add(account)
            await db.flush()

            collection_events: list[tuple[date, float]] = []
            payment_risk = CLIENT_PAYMENT_RISK.get(cliente.codigo, "normal")
            if campaign.activa and liquidation_date <= CURRENT_DATE - timedelta(days=7):
                if payment_risk == "high":
                    advance_ratio = state.rng.uniform(0.04, 0.14)
                elif payment_risk == "medium":
                    advance_ratio = state.rng.uniform(0.18, 0.34)
                else:
                    advance_ratio = state.rng.uniform(0.34, 0.58) if canal.canal_id == export_channel.canal_id else state.rng.uniform(0.6, 0.84)
                advance_date = min(liquidation_date + timedelta(days=state.rng.randint(5, 12)), CURRENT_DATE)
                if advance_date >= liquidation_date:
                    collection_events.append((advance_date, round(account.monto_original_ars * advance_ratio, 2)))

            if due_date <= CURRENT_DATE:
                residual = account.monto_original_ars - sum(amount for _, amount in collection_events)
                if residual > 0:
                    if payment_risk == "high" and campaign.activa:
                        due_collection_ratio = state.rng.uniform(0.0, 0.18)
                    elif payment_risk == "medium" and campaign.activa:
                        due_collection_ratio = state.rng.uniform(0.38, 0.68)
                    else:
                        due_collection_ratio = state.rng.uniform(0.8, 1.0) if campaign.activa else state.rng.uniform(0.95, 1.0)
                    due_collection_amount = round(residual * due_collection_ratio, 2)
                    due_collection_date = min(due_date + timedelta(days=state.rng.randint(0, 5)), CURRENT_DATE)
                    if due_collection_amount > 0:
                        collection_events.append((due_collection_date, due_collection_amount))

            if campaign.activa and not collection_events and liquidation_date <= CURRENT_DATE - timedelta(days=18):
                fallback_amount = round(
                    account.monto_original_ars
                    * (
                        state.rng.uniform(0.03, 0.1)
                        if payment_risk == "high"
                        else state.rng.uniform(0.1, 0.18)
                        if payment_risk == "medium"
                        else state.rng.uniform(0.25, 0.45)
                    ),
                    2,
                )
                fallback_date = min(liquidation_date + timedelta(days=state.rng.randint(10, 18)), CURRENT_DATE)
                collection_events.append((fallback_date, fallback_amount))

            if collection_events:
                paid_total = 0.0
                for idx, (collection_date, raw_amount) in enumerate(sorted(collection_events, key=lambda item: item[0])):
                    remaining = max(0.0, account.monto_original_ars - paid_total)
                    if remaining <= 0:
                        break
                    collected_amount = round(min(remaining, raw_amount), 2)
                    if collected_amount <= 0:
                        continue
                    paid_total += collected_amount
                    saldo_restante = round(max(0.0, account.monto_original_ars - paid_total), 2)
                    cobranzas.append(
                        CobranzasFact(
                            cuenta_cobrar_id=account.cuenta_cobrar_id,
                            liquidacion_id=liquidation.liquidacion_id,
                            fecha_id=state.fecha_ids[collection_date],
                            fecha_cobranza=collection_date,
                            monto_cobrado_ars=collected_amount,
                            medio=state.rng.choice(["transferencia", "cobranza bancaria", "canje"]),
                            cobro_completo=saldo_restante == 0 and idx == len(collection_events) - 1,
                        )
                    )
                account.saldo_abierto_ars = round(max(0.0, account.monto_original_ars - paid_total), 2)
                if (
                    account.saldo_abierto_ars > 0
                    and account.fecha_vencimiento < CURRENT_DATE - timedelta(days=18)
                ):
                    extra_ratio = (
                        state.rng.uniform(0.0, 0.08)
                        if payment_risk == "high"
                        else state.rng.uniform(0.08, 0.18)
                        if payment_risk == "medium"
                        else state.rng.uniform(0.18, 0.35)
                    )
                    extra_amount = round(account.saldo_abierto_ars * extra_ratio, 2)
                    if extra_amount > 0:
                        extra_date = min(account.fecha_vencimiento + timedelta(days=state.rng.randint(20, 35)), CURRENT_DATE)
                        cobranzas.append(
                            CobranzasFact(
                                cuenta_cobrar_id=account.cuenta_cobrar_id,
                                liquidacion_id=liquidation.liquidacion_id,
                                fecha_id=state.fecha_ids[extra_date],
                                fecha_cobranza=extra_date,
                                monto_cobrado_ars=extra_amount,
                                medio=state.rng.choice(["transferencia", "cobranza bancaria", "canje"]),
                                cobro_completo=extra_amount >= account.saldo_abierto_ars,
                            )
                        )
                        account.saldo_abierto_ars = round(max(0.0, account.saldo_abierto_ars - extra_amount), 2)
                account.estado = "cobrada" if account.saldo_abierto_ars == 0 else "parcial"
            embarque.estado_cobro = "cobrado" if account.saldo_abierto_ars == 0 else "parcial" if account.saldo_abierto_ars < account.monto_original_ars else "pendiente"
            liquidation.estado = embarque.estado_cobro

        for establecimiento_id, deposito_id in state.deposito_fresco_por_est.items():
            for destino_code in ["EXP", "LOC"]:
                destino = destinos[destino_code]
                balance = stock_balances[(deposito_id, destino.destino_id)]
                price = _nearest_week_price(reference_prices, current, local_market.mercado_id if destino_code == "LOC" else market_by_code["EU"].mercado_id, local_channel.canal_id if destino_code == "LOC" else export_channel.canal_id)
                fx = state.latest_tipo_cambio.get(current, state.latest_tipo_cambio[max(state.latest_tipo_cambio)])
                stock_rows.append(
                    StockFinalFact(
                        fecha_id=state.fecha_ids[current],
                        fecha=current,
                        deposito_id=deposito_id,
                        destino_id=destino.destino_id,
                        kg_stock=round(balance, 2),
                        cajas_stock=max(0, int(balance / 18)),
                        valor_ars=round((balance / 1000) * price * fx, 2),
                    )
                )
        for establecimiento_id, deposito_id in state.deposito_industria_por_est.items():
            destino = destinos["IND"]
            balance = stock_balances[(deposito_id, destino.destino_id)]
            price = _nearest_week_price(reference_prices, current, industry_market.mercado_id, industry_channel.canal_id)
            fx = state.latest_tipo_cambio.get(current, state.latest_tipo_cambio[max(state.latest_tipo_cambio)])
            stock_rows.append(
                StockFinalFact(
                    fecha_id=state.fecha_ids[current],
                    fecha=current,
                    deposito_id=deposito_id,
                    destino_id=destino.destino_id,
                    kg_stock=round(balance, 2),
                    cajas_stock=0,
                    valor_ars=round((balance / 1000) * price * fx, 2),
                )
            )

    db.add_all(contratos + embarques + liquidaciones + cuentas + cobranzas + stock_rows)


async def seed_limon_data(db: AsyncSession, force: bool = False):
    existing = await db.execute(select(EmpresaDim).limit(1))
    if existing.scalar_one_or_none() and not force:
        return

    state = LemonSeedState()
    await _clear_existing_limon_data(db)
    await _seed_dimensions(db, state)
    await _seed_external(db, state)
    quality_batches = await _seed_field_operations(db, state)
    await _seed_quality_packhouse_and_commercial(db, state, quality_batches)
