import math
import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campania import Campania
from app.models.cliente import Cliente
from app.models.contrato import Contrato
from app.models.cosecha import Cosecha
from app.models.cultivo import Cultivo
from app.models.decision_support import (
    ConsumoCombustible,
    DowntimeMaquinaria,
    EjecucionLabor,
    EntregaComercial,
    ObservacionCampo,
    PlanLabor,
    PosicionComercial,
    PresupuestoLote,
    ServiceSchedule,
    StockProyectado,
)
from app.models.empresa import Empresa
from app.models.erp_catalog import (
    Ambiente,
    Campo,
    CategoriaProducto,
    CentroCosto,
    Contratista,
    Deposito,
    Empleado,
    Implemento,
    LaborTipo,
    Moneda,
    UnidadMedida,
    UnidadNegocio,
    Variedad,
)
from app.models.erp_context import AlertaContexto, ClimaDiario, CommoditiesPrecio, MacroSerie
from app.models.erp_operational import (
    AsignacionCosto,
    Cobranza,
    ConsumoInsumo,
    ContratoCompra,
    ContratoVenta,
    CostoDirecto,
    CostoIndirecto,
    CuentaCobrar,
    CuentaPagar,
    DisponibilidadEquipo,
    EjecucionFertilizacion,
    EjecucionPulverizacion,
    EjecucionSiembra,
    Entrega,
    Fijacion,
    HorasMaquina,
    IngresoInsumo,
    Liquidacion,
    LoteCampania,
    MantenimientoCorrectivo,
    MantenimientoPreventivo,
    MonitoreoPlaga,
    MovimientoStock,
    OrdenCompra,
    Pago,
    ParteMaquinaria,
    ParteTrabajo,
    PedidoCompra,
    PlanFertilizacion,
    PlanPulverizacion,
    PlanSiembra,
    PosicionComercialERP,
    PresupuestoCampania,
    Remito,
    RendimientoLote,
    SalidaInsumo,
    StockActual,
    TransferenciaDeposito,
)
from app.models.establecimiento import Establecimiento
from app.models.flujo_financiero import FlujoCaja
from app.models.insumo import Insumo, MovimientoInsumo
from app.models.labor import Labor
from app.models.lote import Lote
from app.models.mantenimiento import Mantenimiento
from app.models.maquinaria import Maquinaria
from app.models.producto import Producto
from app.models.proveedor import Proveedor
from app.models.stock import Stock
from app.models.venta import Venta


VARIETIES_BY_CROP = {
    "Soja": [("DM 46R18 STS", "Don Mario", "IV corto"), ("NS 4823 STS", "Nidera", "IV medio"), ("CZ 4320", "Credenz", "IV corto")],
    "Maiz": [("DK 7210 VT3P", "Dekalb", "Completo"), ("AX 7822 VT3P", "Advanta", "Completo"), ("SYN 126 VIP3", "Syngenta", "Intermedio")],
    "Trigo": [("Klein Proteo", "Klein", "Largo"), ("Baguette 620", "Nidera", "Intermedio"), ("ACA 360", "ACA", "Corto")],
    "Girasol": [("Paraiso 1800 CL", "Paraiso", "Intermedio"), ("NK 3969 CL", "Syngenta", "Intermedio"), ("Advanta 9235", "Advanta", "Intermedio")],
    "Sorgo": [("ADV 2450", "Advanta", "Intermedio"), ("TOB 82 T", "Tobin", "Intermedio"), ("Sugargraze 70", "Pannar", "Largo")],
}

EMPLOYEE_ROLES = [
    "gerente_establecimiento",
    "encargado_campo",
    "ingeniero_agronomo",
    "operador_siembra",
    "operador_pulverizacion",
    "administracion",
    "deposito",
]

FIRST_NAMES = [
    "Juan", "Maria", "Luciano", "Ana", "Martin", "Camila", "Nicolas", "Agustin", "Carla",
    "Diego", "Paula", "Marcos", "Belen", "Ignacio", "Rocio", "Pablo", "Sofia", "Facundo",
]
LAST_NAMES = [
    "Fernandez", "Lopez", "Bianchi", "Rojas", "Mendez", "Suarez", "Gimenez", "Pereyra", "Lescano",
    "Rodriguez", "Martinez", "Cisneros", "Funes", "Sosa", "Moreno", "Gonzalez", "Arias", "Torres",
]


def _code(prefix: str, *parts: object) -> str:
    normalized = "".join(ch for ch in "_".join(str(part) for part in parts) if ch.isalnum())
    return f"{prefix}{normalized[:20].upper()}"


def _label_hash(value: str) -> int:
    return sum(ord(char) for char in value)


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0


def _campaign_for_date(campanias: list[Campania], current_date: date) -> Campania | None:
    for campania in campanias:
        if campania.fecha_inicio <= current_date <= campania.fecha_fin:
            return campania
    return campanias[-1] if campanias else None


def _series_variation(current_value: float, previous_value: float | None) -> float | None:
    if previous_value in (None, 0):
        return None
    return round(((current_value - previous_value) / previous_value) * 100, 2)


def _supplier_for_insumo(proveedores: list[Proveedor], insumo: Insumo) -> Proveedor:
    if not proveedores:
        raise ValueError("Se requiere al menos un proveedor para seed ERP")

    preferred_names = {
        "combustible": "YPF Agro",
        "semilla": "Monsanto Argentina",
        "fertilizante": "Agro Norte SA",
        "herbicida": "Syngenta Argentina",
        "fungicida": "Syngenta Argentina",
    }
    preferred_name = preferred_names.get(insumo.tipo)
    if preferred_name:
        candidate = next((item for item in proveedores if item.nombre == preferred_name), None)
        if candidate:
            return candidate

    insumo_suppliers = [item for item in proveedores if item.tipo == "insumos"]
    if insumo_suppliers:
        return insumo_suppliers[_label_hash(insumo.nombre) % len(insumo_suppliers)]
    return proveedores[_label_hash(insumo.nombre) % len(proveedores)]


def _month_start_shift(current_date: date, delta_months: int) -> date:
    month_index = (current_date.year * 12 + (current_date.month - 1)) + delta_months
    year = month_index // 12
    month = (month_index % 12) + 1
    return date(year, month, 1)


async def seed_erp_data(db: AsyncSession):
    existing = (await db.execute(select(LoteCampania.id).limit(1))).scalar_one_or_none()
    if existing:
        return

    rng = random.Random(20260320)
    today = date.today()

    empresas = (await db.execute(select(Empresa).order_by(Empresa.id))).scalars().all()
    establecimientos = (await db.execute(select(Establecimiento).order_by(Establecimiento.id))).scalars().all()
    campanias = (await db.execute(select(Campania).order_by(Campania.fecha_inicio))).scalars().all()
    cultivos = (await db.execute(select(Cultivo).order_by(Cultivo.id))).scalars().all()
    clientes = (await db.execute(select(Cliente).order_by(Cliente.id))).scalars().all()
    proveedores = (await db.execute(select(Proveedor).order_by(Proveedor.id))).scalars().all()
    productos = (await db.execute(select(Producto).order_by(Producto.id))).scalars().all()
    insumos = (await db.execute(select(Insumo).order_by(Insumo.id))).scalars().all()
    lotes = (await db.execute(select(Lote).order_by(Lote.id))).scalars().all()
    labores = (await db.execute(select(Labor).order_by(Labor.id))).scalars().all()
    cosechas = (await db.execute(select(Cosecha).order_by(Cosecha.id))).scalars().all()
    movimientos_insumo = (await db.execute(select(MovimientoInsumo).order_by(MovimientoInsumo.id))).scalars().all()
    ventas = (await db.execute(select(Venta).order_by(Venta.id))).scalars().all()
    contratos = (await db.execute(select(Contrato).order_by(Contrato.id))).scalars().all()
    stocks = (await db.execute(select(Stock).order_by(Stock.id))).scalars().all()
    flujos = (await db.execute(select(FlujoCaja).order_by(FlujoCaja.id))).scalars().all()
    maquinarias = (await db.execute(select(Maquinaria).order_by(Maquinaria.id))).scalars().all()
    mantenimientos = (await db.execute(select(Mantenimiento).order_by(Mantenimiento.id))).scalars().all()
    presupuestos_lote = (await db.execute(select(PresupuestoLote).order_by(PresupuestoLote.id))).scalars().all()
    plan_labores = (await db.execute(select(PlanLabor).order_by(PlanLabor.id))).scalars().all()
    ejecuciones_labores = (await db.execute(select(EjecucionLabor).order_by(EjecucionLabor.id))).scalars().all()
    observaciones = (await db.execute(select(ObservacionCampo).order_by(ObservacionCampo.id))).scalars().all()
    posiciones = (await db.execute(select(PosicionComercial).order_by(PosicionComercial.id))).scalars().all()
    entregas_comerciales = (await db.execute(select(EntregaComercial).order_by(EntregaComercial.id))).scalars().all()
    stock_proyectado = (await db.execute(select(StockProyectado).order_by(StockProyectado.id))).scalars().all()
    service_schedule = (await db.execute(select(ServiceSchedule).order_by(ServiceSchedule.id))).scalars().all()
    downtime_rows = (await db.execute(select(DowntimeMaquinaria).order_by(DowntimeMaquinaria.id))).scalars().all()
    consumo_combustible = (await db.execute(select(ConsumoCombustible).order_by(ConsumoCombustible.id))).scalars().all()

    establecimientos_by_id = {item.id: item for item in establecimientos}
    campanias_by_id = {item.id: item for item in campanias}
    cultivos_by_id = {item.id: item for item in cultivos}
    productos_by_id = {item.id: item for item in productos}
    productos_by_cultivo = {item.cultivo_id: item for item in productos if item.cultivo_id}
    insumos_by_id = {item.id: item for item in insumos}
    lotes_by_id = {item.id: item for item in lotes}
    presupuesto_by_lote = {item.lote_id: item for item in presupuestos_lote}
    current_campaign = _campaign_for_date(campanias, today)

    monedas = [
        Moneda(codigo="ARS", nombre="Peso Argentino", simbolo="$", es_base=True),
        Moneda(codigo="USD", nombre="Dolar Estadounidense", simbolo="USD", es_base=False),
    ]
    unidades = [
        UnidadMedida(codigo="ha", nombre="Hectarea", categoria="superficie", factor_base=1),
        UnidadMedida(codigo="tn", nombre="Tonelada", categoria="peso", factor_base=1),
        UnidadMedida(codigo="kg", nombre="Kilogramo", categoria="peso", factor_base=0.001),
        UnidadMedida(codigo="lt", nombre="Litro", categoria="volumen", factor_base=1),
        UnidadMedida(codigo="bolsa", nombre="Bolsa", categoria="cantidad", factor_base=1),
        UnidadMedida(codigo="hr", nombre="Hora", categoria="tiempo", factor_base=1),
        UnidadMedida(codigo="mm", nombre="Milimetro", categoria="clima", factor_base=1),
        UnidadMedida(codigo="pct", nombre="Porcentaje", categoria="ratio", factor_base=1),
    ]
    categorias_producto = [
        CategoriaProducto(codigo="GRANOS", nombre="Granos", tipo="producto"),
        CategoriaProducto(codigo="SEMILLAS", nombre="Semillas", tipo="insumo"),
        CategoriaProducto(codigo="FERTILIZANTES", nombre="Fertilizantes", tipo="insumo"),
        CategoriaProducto(codigo="FITOSANITARIOS", nombre="Fitosanitarios", tipo="insumo"),
        CategoriaProducto(codigo="COMBUSTIBLES", nombre="Combustibles", tipo="insumo"),
    ]
    labor_tipos = [
        LaborTipo(codigo="SIEMBRA", nombre="Siembra", categoria="implantacion", requiere_equipo=True, requiere_producto=True, requiere_dosis=True),
        LaborTipo(codigo="FERTILIZACION", nombre="Fertilizacion", categoria="nutricion", requiere_equipo=True, requiere_producto=True, requiere_dosis=True),
        LaborTipo(codigo="PULVERIZACION", nombre="Pulverizacion", categoria="proteccion", requiere_equipo=True, requiere_producto=True, requiere_dosis=True),
        LaborTipo(codigo="COSECHA", nombre="Cosecha", categoria="recoleccion", requiere_equipo=True, requiere_producto=False, requiere_dosis=False),
        LaborTipo(codigo="BARBECHO", nombre="Barbecho", categoria="preparacion", requiere_equipo=True, requiere_producto=False, requiere_dosis=False),
        LaborTipo(codigo="LOGISTICA", nombre="Logistica", categoria="movimiento", requiere_equipo=True, requiere_producto=False, requiere_dosis=False),
    ]

    db.add_all(monedas + unidades + categorias_producto + labor_tipos)
    await db.flush()

    moneda_by_code = {item.codigo: item for item in monedas}
    unidad_by_code = {item.codigo: item for item in unidades}
    labor_tipo_by_code = {item.codigo: item for item in labor_tipos}

    unidades_negocio = []
    for empresa in empresas:
        unidades_negocio.extend(
            [
                UnidadNegocio(empresa_id=empresa.id, codigo="AGR", nombre="Agricultura Extensiva", descripcion="Produccion de granos", activa=True),
                UnidadNegocio(empresa_id=empresa.id, codigo="COM", nombre="Comercializacion", descripcion="Gestion comercial y logistica", activa=True),
            ]
        )
    db.add_all(unidades_negocio)
    await db.flush()

    unidad_negocio_agr = {
        empresa.id: next(item for item in unidades_negocio if item.empresa_id == empresa.id and item.codigo == "AGR")
        for empresa in empresas
    }

    campos = []
    for establecimiento in establecimientos:
        count = 2 if (establecimiento.hectareas_totales or 0) >= 800 else 1
        weights = [0.58, 0.42] if count == 2 else [1.0]
        names = ["Sector Norte", "Sector Sur"] if count == 2 else ["Campo Base"]
        for idx in range(count):
            campos.append(
                Campo(
                    empresa_id=establecimiento.empresa_id,
                    unidad_negocio_id=unidad_negocio_agr[establecimiento.empresa_id].id,
                    establecimiento_id=establecimiento.id,
                    codigo=_code("CAM", establecimiento.id, idx + 1),
                    nombre=f"{establecimiento.nombre} - {names[idx]}",
                    superficie_total_ha=round((establecimiento.hectareas_totales or 0) * weights[idx], 2),
                    arrendado=(establecimiento.id + idx) % 4 == 0,
                    observaciones="Campo operativo incorporado a la capa ERP",
                )
            )
    db.add_all(campos)
    await db.flush()
    campos_by_establecimiento: dict[int, list[Campo]] = defaultdict(list)
    for campo in campos:
        campos_by_establecimiento[campo.establecimiento_id].append(campo)

    depositos = []
    for establecimiento in establecimientos:
        depositos.extend(
            [
                Deposito(
                    empresa_id=establecimiento.empresa_id,
                    establecimiento_id=establecimiento.id,
                    codigo=_code("DEPINS", establecimiento.id),
                    nombre=f"{establecimiento.nombre} - Insumos",
                    tipo="insumos",
                    capacidad=round((establecimiento.hectareas_totales or 0) * 1.25, 2),
                    unidad_capacidad="tn",
                    activo=True,
                ),
                Deposito(
                    empresa_id=establecimiento.empresa_id,
                    establecimiento_id=establecimiento.id,
                    codigo=_code("DEPGRA", establecimiento.id),
                    nombre=f"{establecimiento.nombre} - Granos",
                    tipo="granos",
                    capacidad=round((establecimiento.hectareas_totales or 0) * 4.8, 2),
                    unidad_capacidad="tn",
                    activo=True,
                ),
            ]
        )
    db.add_all(depositos)
    await db.flush()
    deposito_by_est_tipo = {(item.establecimiento_id, item.tipo): item for item in depositos}

    centros_costos = []
    for empresa in empresas:
        centros_costos.extend(
            [
                CentroCosto(
                    empresa_id=empresa.id,
                    unidad_negocio_id=unidad_negocio_agr[empresa.id].id,
                    establecimiento_id=None,
                    codigo=f"ADM-{empresa.id}",
                    nombre="Administracion General",
                    tipo="corporativo",
                    activo=True,
                ),
                CentroCosto(
                    empresa_id=empresa.id,
                    unidad_negocio_id=unidad_negocio_agr[empresa.id].id,
                    establecimiento_id=None,
                    codigo=f"COM-{empresa.id}",
                    nombre="Comercial y Logistica",
                    tipo="comercial",
                    activo=True,
                ),
            ]
        )
    for establecimiento in establecimientos:
        centros_costos.extend(
            [
                CentroCosto(
                    empresa_id=establecimiento.empresa_id,
                    unidad_negocio_id=unidad_negocio_agr[establecimiento.empresa_id].id,
                    establecimiento_id=establecimiento.id,
                    codigo=f"OP-{establecimiento.id}",
                    nombre=f"Operaciones {establecimiento.nombre}",
                    tipo="operativo",
                    activo=True,
                ),
                CentroCosto(
                    empresa_id=establecimiento.empresa_id,
                    unidad_negocio_id=unidad_negocio_agr[establecimiento.empresa_id].id,
                    establecimiento_id=establecimiento.id,
                    codigo=f"MNT-{establecimiento.id}",
                    nombre=f"Mantenimiento {establecimiento.nombre}",
                    tipo="mantenimiento",
                    activo=True,
                ),
            ]
        )
    db.add_all(centros_costos)
    await db.flush()
    centro_costo_operativo = {
        item.establecimiento_id: item
        for item in centros_costos
        if item.establecimiento_id is not None and item.tipo == "operativo"
    }
    centro_costo_mantenimiento = {
        item.establecimiento_id: item
        for item in centros_costos
        if item.establecimiento_id is not None and item.tipo == "mantenimiento"
    }
    centro_costo_admin = {
        item.empresa_id: item
        for item in centros_costos
        if item.tipo == "corporativo"
    }

    empleados = []
    employee_sequences = defaultdict(int)
    for establecimiento in establecimientos:
        for role_index, role in enumerate(EMPLOYEE_ROLES):
            seed_index = establecimiento.id * 10 + role_index
            first = FIRST_NAMES[seed_index % len(FIRST_NAMES)]
            last = LAST_NAMES[(seed_index * 3) % len(LAST_NAMES)]
            employee_sequences[establecimiento.empresa_id] += 1
            empleados.append(
                Empleado(
                    empresa_id=establecimiento.empresa_id,
                    centro_costo_id=centro_costo_operativo[establecimiento.id].id,
                    establecimiento_id=establecimiento.id,
                    legajo=f"{establecimiento.empresa_id:02d}{employee_sequences[establecimiento.empresa_id]:04d}",
                    nombre=f"{first} {last}",
                    rol=role,
                    tipo="propio",
                    activo=True,
                    telefono=f"+54 9 341 {20000000 + seed_index:08d}",
                )
            )
    db.add_all(empleados)
    await db.flush()
    empleados_by_est_role = {(item.establecimiento_id, item.rol): item for item in empleados}
    empleados_by_est = defaultdict(list)
    for item in empleados:
        empleados_by_est[item.establecimiento_id].append(item)

    contratistas = []
    service_providers = [item for item in proveedores if item.tipo == "servicios"]
    specialties = ["siembra", "cosecha", "pulverizacion", "transporte"]
    for empresa in empresas:
        for idx, speciality in enumerate(specialties):
            provider = service_providers[idx % len(service_providers)] if service_providers else None
            contratistas.append(
                Contratista(
                    empresa_id=empresa.id,
                    proveedor_id=provider.id if provider else None,
                    nombre=f"{speciality.capitalize()} {empresa.nombre.split()[0]}",
                    especialidad=speciality,
                    cuit=f"30-{empresa.id}{idx + 1:08d}-{idx}",
                    telefono=f"+54 9 11 4{empresa.id}{idx:07d}",
                    activo=True,
                )
            )
    db.add_all(contratistas)
    await db.flush()
    contratistas_by_empresa_especialidad = {(item.empresa_id, item.especialidad): item for item in contratistas}

    variedades = []
    for cultivo in cultivos:
        for nombre, marca, ciclo in VARIETIES_BY_CROP.get(cultivo.nombre, [(f"{cultivo.nombre} Base", cultivo.nombre, "medio")]):
            variedades.append(
                Variedad(
                    cultivo_id=cultivo.id,
                    nombre=nombre,
                    marca=marca,
                    ciclo=ciclo,
                    tecnologia="Convencional" if cultivo.nombre in {"Trigo", "Girasol"} else "Evento apilado",
                    activo=True,
                )
            )
    db.add_all(variedades)
    await db.flush()
    variedades_by_cultivo = defaultdict(list)
    for item in variedades:
        variedades_by_cultivo[item.cultivo_id].append(item)

    implementos = []
    for maquina in maquinarias:
        implemento_tipo = {
            "tractor": "tolva",
            "sembradora": "carro_tolva",
            "pulverizadora": "botalon",
            "cosechadora": "cabezal",
        }.get(maquina.tipo, "implemento")
        implementos.append(
            Implemento(
                empresa_id=establecimientos_by_id[maquina.establecimiento_id].empresa_id,
                establecimiento_id=maquina.establecimiento_id,
                maquinaria_id=maquina.id,
                tipo=implemento_tipo,
                marca=maquina.marca,
                modelo=f"{maquina.modelo} / {implemento_tipo}",
                ancho_trabajo_m=round(10 + (maquina.id % 7) * 1.8, 1),
                activo=maquina.estado != "baja",
            )
        )
    db.add_all(implementos)
    await db.flush()
    implemento_by_maquinaria = {item.maquinaria_id: item for item in implementos if item.maquinaria_id}
    maquinarias_by_est_tipo = defaultdict(list)
    for maquina in maquinarias:
        maquinarias_by_est_tipo[(maquina.establecimiento_id, maquina.tipo)].append(maquina)

    ambientes = []
    ambiente_names = [("LOM", "Loma", 0.28, "alto"), ("MLM", "Media loma", 0.44, "medio"), ("BAJ", "Bajo", 0.28, "medio")]
    for lote in lotes:
        for idx, (codigo, nombre, share, potencial) in enumerate(ambiente_names):
            ambientes.append(
                Ambiente(
                    lote_id=lote.id,
                    codigo=f"{codigo}-{idx + 1}",
                    nombre=nombre,
                    superficie_ha=round((lote.hectareas or 0) * share, 2),
                    potencial_productivo=potencial,
                    textura_suelo="franco" if idx != 2 else "franco limoso",
                    materia_organica_pct=round(2.4 + (lote.id % 5) * 0.25 - idx * 0.1, 2),
                    ph=round(6.2 + (idx * 0.15), 2),
                )
            )
    db.add_all(ambientes)
    await db.flush()
    ambientes_by_lote = defaultdict(list)
    for item in ambientes:
        ambientes_by_lote[item.lote_id].append(item)

    lotes_campania = []
    for lote in lotes:
        establecimiento = establecimientos_by_id[lote.establecimiento_id]
        campania = campanias_by_id.get(lote.campania_id) or current_campaign
        if not campania or not lote.cultivo_id:
            continue
        campos_est = campos_by_establecimiento[establecimiento.id]
        campo = campos_est[_label_hash(lote.nombre) % len(campos_est)]
        variedades_cultivo = variedades_by_cultivo.get(lote.cultivo_id, [])
        presupuesto = presupuesto_by_lote.get(lote.id)
        responsable = empleados_by_est_role.get((establecimiento.id, "ingeniero_agronomo")) or empleados_by_est[establecimiento.id][0]
        fecha_siembra_plan = lote.fecha_siembra or (campania.fecha_inicio + timedelta(days=110))
        fecha_cosecha_plan = lote.fecha_cosecha or (campania.fecha_fin - timedelta(days=55))
        fecha_inicio_operativa = min(campania.fecha_inicio, fecha_siembra_plan - timedelta(days=20))
        fecha_fin_operativa = max(campania.fecha_fin, fecha_cosecha_plan + timedelta(days=20))
        lotes_campania.append(
            LoteCampania(
                empresa_id=establecimiento.empresa_id,
                establecimiento_id=establecimiento.id,
                campo_id=campo.id,
                lote_id=lote.id,
                campania_id=campania.id,
                cultivo_id=lote.cultivo_id,
                variedad_id=variedades_cultivo[_label_hash(lote.nombre + campania.nombre) % len(variedades_cultivo)].id if variedades_cultivo else None,
                centro_costo_id=centro_costo_operativo[establecimiento.id].id,
                superficie_ha=lote.hectareas,
                modalidad="arrendado" if campo.arrendado else "propio",
                estado=lote.estado,
                fecha_inicio=fecha_inicio_operativa,
                fecha_fin=fecha_fin_operativa,
                fecha_siembra_plan=fecha_siembra_plan,
                fecha_siembra_real=lote.fecha_siembra,
                fecha_cosecha_plan=fecha_cosecha_plan,
                fecha_cosecha_real=lote.fecha_cosecha,
                objetivo_rinde_tn_ha=(presupuesto.rendimiento_objetivo_tn_ha if presupuesto else lote.rendimiento_historico),
                objetivo_margen_ha=(presupuesto.margen_objetivo_ha if presupuesto else None),
                responsable_id=responsable.id,
                observaciones=f"Registro ERP generado desde lote legacy {lote.id}",
            )
        )
    db.add_all(lotes_campania)
    await db.flush()
    lote_campania_by_lote = {item.lote_id: item for item in lotes_campania}

    plan_siembra_rows = []
    plan_fertilizacion_rows = []
    plan_pulverizacion_rows = []
    legacy_plan_map: dict[int, tuple[str, object]] = {}
    semilla_by_crop = {
        "Soja": next((item for item in insumos if "Soja" in item.nombre and item.tipo == "semilla"), None),
        "Maiz": next((item for item in insumos if "Maiz" in item.nombre and item.tipo == "semilla"), None),
        "Trigo": next((item for item in insumos if "Trigo" in item.nombre and item.tipo == "semilla"), None),
        "Girasol": next((item for item in insumos if "Girasol" in item.nombre and item.tipo == "semilla"), None),
        "Sorgo": next((item for item in insumos if "Sorgo" in item.nombre and item.tipo == "semilla"), None),
    }
    fertilizante_default = next((item for item in insumos if item.tipo == "fertilizante"), None)
    herbicida_default = next((item for item in insumos if item.tipo == "herbicida"), None)

    for plan in plan_labores:
        lot_campaign = lote_campania_by_lote.get(plan.lote_id)
        lote = lotes_by_id.get(plan.lote_id)
        if not lot_campaign or not lote or not lot_campaign.cultivo_id:
            continue
        cultivo = cultivos_by_id[lot_campaign.cultivo_id]
        establecimiento_id = lot_campaign.establecimiento_id
        empresa_id = lot_campaign.empresa_id
        if plan.tipo_labor == "siembra":
            maquinaria = (maquinarias_by_est_tipo.get((establecimiento_id, "sembradora")) or maquinarias_by_est_tipo.get((establecimiento_id, "tractor")) or [None])[0]
            operador = empleados_by_est_role.get((establecimiento_id, "operador_siembra")) or empleados_by_est[establecimiento_id][0]
            row = PlanSiembra(
                lote_campania_id=lot_campaign.id,
                labor_tipo_id=labor_tipo_by_code["SIEMBRA"].id,
                fecha_planificada=plan.ventana_inicio,
                ventana_inicio=plan.ventana_inicio,
                ventana_fin=plan.ventana_fin,
                superficie_objetivo_ha=plan.hectareas_planificadas,
                densidad_semillas_ha=round(4.5 + (lote.id % 4) * 0.5, 2),
                semilla_insumo_id=semilla_by_crop.get(cultivo.nombre).id if semilla_by_crop.get(cultivo.nombre) else None,
                dosis_semilla=plan.dosis_objetivo,
                unidad_medida_id=(unidad_by_code["kg"].id if cultivo.nombre != "Maiz" else unidad_by_code["bolsa"].id),
                maquinaria_id=maquinaria.id if maquinaria else None,
                implemento_id=implemento_by_maquinaria.get(maquinaria.id).id if maquinaria and implemento_by_maquinaria.get(maquinaria.id) else None,
                operador_id=operador.id,
                contratista_id=contratistas_by_empresa_especialidad.get((empresa_id, "siembra")).id if lote.hectareas > 260 else None,
                costo_estimado_ha=round(17000 + (lote.id % 7) * 1500, 2),
                prioridad=plan.prioridad,
                estado="planificado",
            )
            plan_siembra_rows.append(row)
            legacy_plan_map[plan.id] = ("siembra", row)
        elif plan.tipo_labor == "fertilizacion":
            maquinaria = (maquinarias_by_est_tipo.get((establecimiento_id, "tractor")) or [None])[0]
            operador = empleados_by_est_role.get((establecimiento_id, "encargado_campo")) or empleados_by_est[establecimiento_id][0]
            row = PlanFertilizacion(
                lote_campania_id=lot_campaign.id,
                fecha_planificada=plan.ventana_inicio,
                ventana_inicio=plan.ventana_inicio,
                ventana_fin=plan.ventana_fin,
                superficie_objetivo_ha=plan.hectareas_planificadas,
                insumo_id=fertilizante_default.id if fertilizante_default else insumos[0].id,
                nutriente_objetivo=plan.nutriente_objetivo or "Nitrogeno",
                dosis_objetivo=plan.dosis_objetivo or 110,
                unidad_medida_id=unidad_by_code["kg"].id,
                maquinaria_id=maquinaria.id if maquinaria else None,
                implemento_id=implemento_by_maquinaria.get(maquinaria.id).id if maquinaria and implemento_by_maquinaria.get(maquinaria.id) else None,
                operador_id=operador.id,
                contratista_id=contratistas_by_empresa_especialidad.get((empresa_id, "siembra")).id if lote.hectareas > 300 else None,
                costo_estimado_ha=round(13500 + (lote.id % 6) * 1200, 2),
                estado="planificado",
            )
            plan_fertilizacion_rows.append(row)
            legacy_plan_map[plan.id] = ("fertilizacion", row)
        elif plan.tipo_labor in {"aplicacion", "fumigacion", "pulverizacion"}:
            maquinaria = (maquinarias_by_est_tipo.get((establecimiento_id, "pulverizadora")) or [None])[0]
            operador = empleados_by_est_role.get((establecimiento_id, "operador_pulverizacion")) or empleados_by_est[establecimiento_id][0]
            row = PlanPulverizacion(
                lote_campania_id=lot_campaign.id,
                fecha_planificada=plan.ventana_inicio,
                ventana_inicio=plan.ventana_inicio,
                ventana_fin=plan.ventana_fin,
                superficie_objetivo_ha=plan.hectareas_planificadas,
                objetivo="Control de malezas y sanitizacion",
                ingrediente_activo=plan.ingrediente_activo or "Glifosato",
                producto_id=herbicida_default.id if herbicida_default else insumos[0].id,
                dosis_objetivo=plan.dosis_objetivo or 2.5,
                unidad_medida_id=unidad_by_code["lt"].id,
                maquinaria_id=maquinaria.id if maquinaria else None,
                implemento_id=implemento_by_maquinaria.get(maquinaria.id).id if maquinaria and implemento_by_maquinaria.get(maquinaria.id) else None,
                operador_id=operador.id,
                contratista_id=contratistas_by_empresa_especialidad.get((empresa_id, "pulverizacion")).id if lote.hectareas > 240 else None,
                costo_estimado_ha=round(9000 + (lote.id % 4) * 950, 2),
                estado="planificado",
            )
            plan_pulverizacion_rows.append(row)
            legacy_plan_map[plan.id] = ("pulverizacion", row)

    db.add_all(plan_siembra_rows + plan_fertilizacion_rows + plan_pulverizacion_rows)
    await db.flush()

    new_plan_by_legacy = {legacy_id: (kind, row.id) for legacy_id, (kind, row) in legacy_plan_map.items()}
    ejec_siembra = []
    ejec_fertilizacion = []
    ejec_pulverizacion = []
    for ejecucion in ejecuciones_labores:
        if ejecucion.plan_labor_id not in new_plan_by_legacy:
            continue
        kind, new_plan_id = new_plan_by_legacy[ejecucion.plan_labor_id]
        legacy_plan = next((item for item in plan_labores if item.id == ejecucion.plan_labor_id), None)
        if not legacy_plan:
            continue
        lot_campaign = lote_campania_by_lote.get(legacy_plan.lote_id)
        establecimiento_id = lot_campaign.establecimiento_id if lot_campaign else None
        if not establecimiento_id:
            continue
        if kind == "siembra":
            maquinaria = (maquinarias_by_est_tipo.get((establecimiento_id, "sembradora")) or maquinarias_by_est_tipo.get((establecimiento_id, "tractor")) or [None])[0]
            operador = empleados_by_est_role.get((establecimiento_id, "operador_siembra")) or empleados_by_est[establecimiento_id][0]
            ejec_siembra.append(
                EjecucionSiembra(
                    plan_siembra_id=new_plan_id,
                    fecha_labor=ejecucion.fecha,
                    superficie_ejecutada_ha=ejecucion.hectareas_ejecutadas,
                    semillas_consumidas=round((ejecucion.hectareas_ejecutadas or 0) * 72, 2),
                    dosis_real=ejecucion.dosis_aplicada,
                    horas_operativas=ejecucion.horas_trabajadas,
                    horas_improductivas=round((ejecucion.horas_trabajadas or 0) * 0.08, 2),
                    velocidad_promedio_kmh=round(7.2 + (ejecucion.id % 3) * 0.6, 2),
                    humedad_suelo=round(18 + (ejecucion.id % 4) * 2.5, 1),
                    maquinaria_id=maquinaria.id if maquinaria else None,
                    implemento_id=implemento_by_maquinaria.get(maquinaria.id).id if maquinaria and implemento_by_maquinaria.get(maquinaria.id) else None,
                    operador_id=operador.id,
                    contratista_id=None,
                    costo_real=round((ejecucion.hectareas_ejecutadas or 0) * 18500, 2),
                    observaciones=ejecucion.observacion,
                )
            )
        elif kind == "fertilizacion":
            maquinaria = (maquinarias_by_est_tipo.get((establecimiento_id, "tractor")) or [None])[0]
            operador = empleados_by_est_role.get((establecimiento_id, "encargado_campo")) or empleados_by_est[establecimiento_id][0]
            ejec_fertilizacion.append(
                EjecucionFertilizacion(
                    plan_fertilizacion_id=new_plan_id,
                    fecha_labor=ejecucion.fecha,
                    superficie_ejecutada_ha=ejecucion.hectareas_ejecutadas,
                    dosis_real=ejecucion.dosis_aplicada,
                    volumen_aplicado=round((ejecucion.hectareas_ejecutadas or 0) * (ejecucion.dosis_aplicada or 0), 2),
                    horas_operativas=ejecucion.horas_trabajadas,
                    maquinaria_id=maquinaria.id if maquinaria else None,
                    implemento_id=implemento_by_maquinaria.get(maquinaria.id).id if maquinaria and implemento_by_maquinaria.get(maquinaria.id) else None,
                    operador_id=operador.id,
                    costo_real=round((ejecucion.hectareas_ejecutadas or 0) * 14800, 2),
                    observaciones=ejecucion.observacion,
                )
            )
        elif kind == "pulverizacion":
            maquinaria = (maquinarias_by_est_tipo.get((establecimiento_id, "pulverizadora")) or [None])[0]
            operador = empleados_by_est_role.get((establecimiento_id, "operador_pulverizacion")) or empleados_by_est[establecimiento_id][0]
            ejec_pulverizacion.append(
                EjecucionPulverizacion(
                    plan_pulverizacion_id=new_plan_id,
                    fecha_labor=ejecucion.fecha,
                    superficie_ejecutada_ha=ejecucion.hectareas_ejecutadas,
                    dosis_real=ejecucion.dosis_aplicada,
                    volumen_aplicado=round((ejecucion.hectareas_ejecutadas or 0) * (ejecucion.dosis_aplicada or 0), 2),
                    agua_litros_ha=round(85 + (ejecucion.id % 4) * 12, 1),
                    condiciones="Buena ventana operativa" if ejecucion.estado == "completado" else "Ejecucion parcial por condicion de campo",
                    horas_operativas=ejecucion.horas_trabajadas,
                    maquinaria_id=maquinaria.id if maquinaria else None,
                    implemento_id=implemento_by_maquinaria.get(maquinaria.id).id if maquinaria and implemento_by_maquinaria.get(maquinaria.id) else None,
                    operador_id=operador.id,
                    costo_real=round((ejecucion.hectareas_ejecutadas or 0) * 9900, 2),
                    observaciones=ejecucion.observacion,
                )
            )
    db.add_all(ejec_siembra + ejec_fertilizacion + ejec_pulverizacion)
    await db.flush()

    rendimiento_rows = []
    for cosecha in cosechas:
        lote = lotes_by_id.get(cosecha.lote_id)
        lot_campaign = lote_campania_by_lote.get(cosecha.lote_id)
        if not lote or not lot_campaign:
            continue
        producto = productos_by_cultivo.get(lot_campaign.cultivo_id)
        rendimiento_rows.append(
            RendimientoLote(
                lote_campania_id=lot_campaign.id,
                cosecha_id=cosecha.id,
                fecha_cosecha=cosecha.fecha,
                superficie_cosechada_ha=lote.hectareas,
                produccion_tn=cosecha.volumen_cosechado,
                rendimiento_tn_ha=cosecha.rendimiento,
                humedad_pct=cosecha.humedad,
                merma_pct=cosecha.merma,
                calidad="comercial",
                precio_estimado_tn=producto.precio_referencia if producto else None,
                ingreso_estimado=(producto.precio_referencia * cosecha.volumen_cosechado) if producto and producto.precio_referencia else None,
            )
        )
    db.add_all(rendimiento_rows)
    await db.flush()

    monitoreos = []
    for obs in observaciones:
        lot_campaign = lote_campania_by_lote.get(obs.lote_id)
        if not lot_campaign:
            continue
        ambiente = ambientes_by_lote[obs.lote_id][_label_hash(obs.ambiente or obs.categoria) % len(ambientes_by_lote[obs.lote_id])]
        monitoreos.append(
            MonitoreoPlaga(
                lote_campania_id=lot_campaign.id,
                ambiente_id=ambiente.id,
                fecha=obs.fecha,
                tipo=obs.categoria,
                organismo=obs.descripcion[:100],
                severidad=obs.severidad,
                incidencia_pct=obs.cobertura_pct,
                umbral=25 if obs.categoria in {"plagas", "malezas"} else 15,
                accion_recomendada=obs.accion_sugerida,
                monitoreador_id=lot_campaign.responsable_id,
            )
        )
    for lot_campaign in lotes_campania:
        if campanias_by_id[lot_campaign.campania_id].activa:
            ambiente = ambientes_by_lote[lot_campaign.lote_id][lot_campaign.id % len(ambientes_by_lote[lot_campaign.lote_id])]
            monitoreos.append(
                MonitoreoPlaga(
                    lote_campania_id=lot_campaign.id,
                    ambiente_id=ambiente.id,
                    fecha=today - timedelta(days=(lot_campaign.id % 8) + 2),
                    tipo="plagas",
                    organismo="Monitoreo preventivo de isocas y malezas de otoño",
                    severidad="alta" if lot_campaign.id % 6 == 0 else "media",
                    incidencia_pct=round(8 + (lot_campaign.id % 7) * 3.8, 1),
                    umbral=22,
                    accion_recomendada="Priorizar control sectorizado en los ambientes de menor vigor",
                    monitoreador_id=lot_campaign.responsable_id,
                )
            )
    db.add_all(monitoreos)
    await db.flush()

    movimientos_stock = []
    legacy_movement_map = {}
    for movimiento in movimientos_insumo:
        deposito = deposito_by_est_tipo[(movimiento.establecimiento_id, "insumos")]
        movimiento_stock = MovimientoStock(
            empresa_id=establecimientos_by_id[movimiento.establecimiento_id].empresa_id,
            establecimiento_id=movimiento.establecimiento_id,
            deposito_id=deposito.id,
            producto_id=None,
            insumo_id=movimiento.insumo_id,
            lote_campania_id=lote_campania_by_lote.get(movimiento.lote_id).id if movimiento.lote_id and lote_campania_by_lote.get(movimiento.lote_id) else None,
            fecha_movimiento=movimiento.fecha,
            tipo_movimiento="ingreso" if movimiento.tipo == "ingreso" else "consumo",
            origen="legacy_movimiento_insumo",
            referencia=f"MOV-INS-{movimiento.id}",
            cantidad=movimiento.cantidad,
            unidad_medida_id=unidad_by_code[insumos_by_id[movimiento.insumo_id].unidad].id if insumos_by_id[movimiento.insumo_id].unidad in unidad_by_code else unidad_by_code["lt"].id,
            costo_unitario=_safe_div(movimiento.costo_total, movimiento.cantidad),
            monto_total=movimiento.costo_total,
            observaciones="Movimiento generado desde la capa legacy",
        )
        movimientos_stock.append(movimiento_stock)
        legacy_movement_map[movimiento.id] = movimiento_stock

    for cosecha in cosechas:
        lote = lotes_by_id.get(cosecha.lote_id)
        if not lote or lote.establecimiento_id not in establecimientos_by_id:
            continue
        lot_campaign = lote_campania_by_lote.get(lote.id)
        producto = productos_by_cultivo.get(lot_campaign.cultivo_id) if lot_campaign else None
        if not producto:
            continue
        deposito = deposito_by_est_tipo[(lote.establecimiento_id, "granos")]
        movimientos_stock.append(
            MovimientoStock(
                empresa_id=establecimientos_by_id[lote.establecimiento_id].empresa_id,
                establecimiento_id=lote.establecimiento_id,
                deposito_id=deposito.id,
                producto_id=producto.id,
                insumo_id=None,
                lote_campania_id=lot_campaign.id if lot_campaign else None,
                fecha_movimiento=cosecha.fecha,
                tipo_movimiento="ingreso_produccion",
                origen="cosecha",
                referencia=f"COSECHA-{cosecha.id}",
                cantidad=cosecha.volumen_cosechado,
                unidad_medida_id=unidad_by_code["tn"].id,
                costo_unitario=producto.precio_referencia,
                monto_total=(producto.precio_referencia or 0) * (cosecha.volumen_cosechado or 0),
                observaciones="Ingreso de grano a deposito comercial",
            )
        )

    stock_source_by_company_product = defaultdict(list)
    assigned_sales_by_stock_id = defaultdict(float)
    for stock in stocks:
        establecimiento = establecimientos_by_id.get(stock.establecimiento_id)
        if not establecimiento:
            continue
        stock_source_by_company_product[(establecimiento.empresa_id, stock.producto_id)].append(stock)

    for venta in ventas:
        producto = productos_by_id.get(venta.producto_id)
        if not producto:
            continue
        sources = stock_source_by_company_product.get((venta.empresa_id, venta.producto_id))
        if not sources:
            continue
        source = sources[venta.id % len(sources)]
        assigned_sales_by_stock_id[source.id] += venta.volumen or 0
        lot_campaign_candidates = [
            item for item in lotes_campania
            if item.empresa_id == venta.empresa_id and item.campania_id == venta.campania_id and item.cultivo_id == producto.cultivo_id
        ]
        lot_campaign = lot_campaign_candidates[venta.id % len(lot_campaign_candidates)] if lot_campaign_candidates else None
        movimientos_stock.append(
            MovimientoStock(
                empresa_id=venta.empresa_id,
                establecimiento_id=source.establecimiento_id,
                deposito_id=deposito_by_est_tipo[(source.establecimiento_id, "granos")].id,
                producto_id=venta.producto_id,
                insumo_id=None,
                lote_campania_id=lot_campaign.id if lot_campaign else None,
                fecha_movimiento=venta.fecha,
                tipo_movimiento="egreso_venta",
                origen="venta",
                referencia=f"VENTA-{venta.id}",
                cantidad=venta.volumen,
                unidad_medida_id=unidad_by_code["tn"].id,
                costo_unitario=venta.precio_tn,
                monto_total=venta.total,
                observaciones="Egreso comercial desde deposito",
            )
        )

    db.add_all(movimientos_stock)
    await db.flush()

    ingresos_insumos = []
    salidas_insumos = []
    consumos_insumos = []
    for movimiento in movimientos_insumo:
        erp_movement = legacy_movement_map[movimiento.id]
        if movimiento.tipo == "ingreso":
            ingresos_insumos.append(
                IngresoInsumo(
                    empresa_id=establecimientos_by_id[movimiento.establecimiento_id].empresa_id,
                    deposito_id=deposito_by_est_tipo[(movimiento.establecimiento_id, "insumos")].id,
                    proveedor_id=proveedores[movimiento.id % len(proveedores)].id if proveedores else None,
                    orden_compra_id=None,
                    remito_id=None,
                    fecha_ingreso=movimiento.fecha,
                    insumo_id=movimiento.insumo_id,
                    cantidad=movimiento.cantidad,
                    costo_unitario=_safe_div(movimiento.costo_total, movimiento.cantidad),
                    monto_total=movimiento.costo_total,
                    movimiento_stock_id=erp_movement.id,
                )
            )
        else:
            lot_campaign = lote_campania_by_lote.get(movimiento.lote_id) if movimiento.lote_id else None
            salidas_insumos.append(
                SalidaInsumo(
                    empresa_id=establecimientos_by_id[movimiento.establecimiento_id].empresa_id,
                    deposito_id=deposito_by_est_tipo[(movimiento.establecimiento_id, "insumos")].id,
                    lote_campania_id=lot_campaign.id if lot_campaign else None,
                    fecha_salida=movimiento.fecha,
                    insumo_id=movimiento.insumo_id,
                    cantidad=movimiento.cantidad,
                    destino="labor" if lot_campaign else "consumo general",
                    movimiento_stock_id=erp_movement.id,
                    costo_total=movimiento.costo_total,
                )
            )
            consumos_insumos.append(
                ConsumoInsumo(
                    empresa_id=establecimientos_by_id[movimiento.establecimiento_id].empresa_id,
                    establecimiento_id=movimiento.establecimiento_id,
                    lote_campania_id=lot_campaign.id if lot_campaign else None,
                    insumo_id=movimiento.insumo_id,
                    movimiento_stock_id=erp_movement.id,
                    fecha_consumo=movimiento.fecha,
                    labor_origen="siembra" if insumos_by_id[movimiento.insumo_id].tipo == "semilla" else "fertilizacion" if insumos_by_id[movimiento.insumo_id].tipo == "fertilizante" else "pulverizacion",
                    cantidad=movimiento.cantidad,
                    unidad_medida_id=unidad_by_code.get(insumos_by_id[movimiento.insumo_id].unidad, unidad_by_code["lt"]).id,
                    costo_total=movimiento.costo_total,
                    costo_ha=round(_safe_div(movimiento.costo_total, lotes_by_id[movimiento.lote_id].hectareas), 2) if movimiento.lote_id and lotes_by_id.get(movimiento.lote_id) else None,
                )
            )

    db.add_all(ingresos_insumos + salidas_insumos + consumos_insumos)
    await db.flush()

    stock_actual_rows = []
    for stock in stocks:
        establecimiento = establecimientos_by_id.get(stock.establecimiento_id)
        if not establecimiento:
            continue
        deposito = deposito_by_est_tipo[(stock.establecimiento_id, "granos")]
        cantidad = (stock.volumen_disponible or 0) + (stock.volumen_vendido or 0) + (stock.volumen_comprometido or 0)
        stock_actual_rows.append(
            StockActual(
                empresa_id=establecimiento.empresa_id,
                establecimiento_id=stock.establecimiento_id,
                deposito_id=deposito.id,
                producto_id=stock.producto_id,
                insumo_id=None,
                fecha_corte=today,
                lote=None,
                cantidad=cantidad,
                reservado=stock.volumen_comprometido or 0,
                disponible=stock.volumen_disponible or 0,
                costo_unitario=productos_by_id[stock.producto_id].precio_referencia if productos_by_id.get(stock.producto_id) else None,
                valor_total=(productos_by_id[stock.producto_id].precio_referencia or 0) * cantidad if productos_by_id.get(stock.producto_id) else None,
            )
        )

    insumo_balance = defaultdict(float)
    insumo_cost = defaultdict(float)
    for movimiento in movimientos_insumo:
        key = (movimiento.establecimiento_id, movimiento.insumo_id)
        sign = 1 if movimiento.tipo == "ingreso" else -1
        insumo_balance[key] += sign * (movimiento.cantidad or 0)
        insumo_cost[key] = _safe_div(movimiento.costo_total or 0, movimiento.cantidad or 1)
    for (establecimiento_id, insumo_id), balance in insumo_balance.items():
        deposito = deposito_by_est_tipo[(establecimiento_id, "insumos")]
        unit_cost = insumo_cost[(establecimiento_id, insumo_id)] or insumos_by_id[insumo_id].precio_unitario
        stock_actual_rows.append(
            StockActual(
                empresa_id=establecimientos_by_id[establecimiento_id].empresa_id,
                establecimiento_id=establecimiento_id,
                deposito_id=deposito.id,
                producto_id=None,
                insumo_id=insumo_id,
                fecha_corte=today,
                lote=None,
                cantidad=max(balance, 0),
                reservado=round(max(balance, 0) * 0.12, 2),
                disponible=round(max(balance, 0) * 0.88, 2),
                costo_unitario=unit_cost,
                valor_total=round(max(balance, 0) * unit_cost, 2),
            )
        )
    db.add_all(stock_actual_rows)
    await db.flush()

    pedidos_compra = []
    selected_stock_projections = []
    ordenes_compra = []
    contratos_compra = []
    for idx, projection in enumerate(stock_proyectado):
        if not projection.compra_sugerida or projection.compra_sugerida <= 0:
            continue
        establecimiento = establecimientos_by_id[projection.establecimiento_id]
        insumo = insumos_by_id[projection.insumo_id]
        solicitante = empleados_by_est_role.get((establecimiento.id, "deposito")) or empleados_by_est[establecimiento.id][0]
        pedido = PedidoCompra(
            empresa_id=establecimiento.empresa_id,
            establecimiento_id=establecimiento.id,
            centro_costo_id=centro_costo_operativo[establecimiento.id].id,
            solicitante_id=solicitante.id,
            numero=f"SOL-{establecimiento.id:02d}-{idx + 1:04d}",
            fecha_pedido=today - timedelta(days=18 - (idx % 9)),
            estado="aprobado" if idx % 5 != 0 else "pendiente",
            prioridad="alta" if projection.severidad in {"warning", "critical"} else "media",
            moneda_id=moneda_by_code["ARS"].id,
            monto_estimado=round(projection.compra_sugerida * insumo.precio_unitario, 2),
            observaciones=f"Reposicion sugerida por cobertura {projection.cobertura_dias} dias",
        )
        pedidos_compra.append(pedido)
        selected_stock_projections.append(projection)
    db.add_all(pedidos_compra)
    await db.flush()

    pedido_by_index = {idx: pedido for idx, pedido in enumerate(pedidos_compra)}
    for idx, pedido in pedido_by_index.items():
        projection = selected_stock_projections[idx]
        insumo = insumos_by_id[projection.insumo_id]
        establecimiento = establecimientos_by_id[pedido.establecimiento_id]
        proveedor = proveedores[(insumo.id + idx) % len(proveedores)]
        deposito = deposito_by_est_tipo[(establecimiento.id, "insumos")]
        orden = OrdenCompra(
            empresa_id=pedido.empresa_id,
            pedido_compra_id=pedido.id,
            proveedor_id=proveedor.id,
            deposito_id=deposito.id,
            numero=f"OC-{pedido.empresa_id:02d}-{idx + 1:04d}",
            fecha_orden=pedido.fecha_pedido + timedelta(days=2),
            fecha_entrega_estimada=pedido.fecha_pedido + timedelta(days=7 + (idx % 5)),
            estado="emitida" if pedido.estado == "aprobado" else "pendiente",
            moneda_id=moneda_by_code["ARS"].id,
            monto_total=pedido.monto_estimado,
            condicion_pago="30 dias",
        )
        ordenes_compra.append(orden)
    db.add_all(ordenes_compra)
    await db.flush()

    for idx, orden in enumerate(ordenes_compra):
        projection = selected_stock_projections[idx]
        insumo = insumos_by_id[projection.insumo_id]
        proveedor = next(item for item in proveedores if item.id == orden.proveedor_id)
        contratos_compra.append(
            ContratoCompra(
                empresa_id=orden.empresa_id,
                proveedor_id=proveedor.id,
                producto_id=None,
                insumo_id=insumo.id,
                numero=f"CC-{orden.empresa_id:02d}-{idx + 1:04d}",
                fecha_contrato=orden.fecha_orden,
                fecha_entrega=orden.fecha_entrega_estimada,
                cantidad=projection.compra_sugerida,
                precio_unitario=insumo.precio_unitario,
                moneda_id=moneda_by_code["ARS"].id,
                estado="vigente",
            )
        )
    db.add_all(contratos_compra)
    await db.flush()

    remitos = []
    for idx, orden in enumerate(ordenes_compra):
        remitos.append(
            Remito(
                empresa_id=orden.empresa_id,
                proveedor_id=orden.proveedor_id,
                cliente_id=None,
                orden_compra_id=orden.id,
                contrato_venta_id=None,
                numero=f"RTOC-{orden.empresa_id:02d}-{idx + 1:05d}",
                fecha_remito=orden.fecha_orden + timedelta(days=5 + (idx % 4)),
                tipo="compra",
                estado="emitido",
                observaciones="Remito de compra generado desde la capa ERP",
            )
        )
    db.add_all(remitos)
    await db.flush()

    transferencias = []
    stock_ok_by_company_insumo = defaultdict(list)
    for projection in stock_proyectado:
        establishment = establecimientos_by_id[projection.establecimiento_id]
        stock_ok_by_company_insumo[(establishment.empresa_id, projection.insumo_id)].append(projection)
    for projection in stock_proyectado:
        if projection.severidad == "ok":
            continue
        establishment = establecimientos_by_id[projection.establecimiento_id]
        candidates = [
            item for item in stock_ok_by_company_insumo[(establishment.empresa_id, projection.insumo_id)]
            if item.establecimiento_id != projection.establecimiento_id and (item.stock_actual or 0) > (projection.compra_sugerida or 0)
        ]
        if not candidates:
            continue
        origin = max(candidates, key=lambda item: item.stock_actual or 0)
        transferencias.append(
            TransferenciaDeposito(
                empresa_id=establishment.empresa_id,
                deposito_origen_id=deposito_by_est_tipo[(origin.establecimiento_id, "insumos")].id,
                deposito_destino_id=deposito_by_est_tipo[(projection.establecimiento_id, "insumos")].id,
                producto_id=None,
                insumo_id=projection.insumo_id,
                fecha_transferencia=today - timedelta(days=projection.id % 12),
                cantidad=min(origin.stock_actual * 0.2, projection.compra_sugerida or 0),
                estado="confirmada",
                referencia=f"TR-{projection.id:05d}",
            )
        )
    db.add_all(transferencias)
    await db.flush()

    contratos_venta = []
    legacy_contract_map = {}
    for idx, contrato in enumerate(contratos):
        producto = productos_by_cultivo.get(contrato.cultivo_id)
        contratos_venta.append(
            ContratoVenta(
                empresa_id=contrato.empresa_id,
                cliente_id=contrato.cliente_id,
                campania_id=contrato.campania_id,
                cultivo_id=contrato.cultivo_id,
                producto_id=producto.id if producto else productos[0].id,
                numero=f"CV-{contrato.empresa_id:02d}-{idx + 1:04d}",
                fecha_contrato=(contrato.fecha_entrega - timedelta(days=60)),
                fecha_entrega_desde=contrato.fecha_entrega - timedelta(days=15),
                fecha_entrega_hasta=contrato.fecha_entrega,
                volumen_tn=contrato.volumen_contratado,
                precio_tn=contrato.precio_fijado,
                volumen_fijado_tn=(contrato.volumen_contratado if contrato.precio_fijado else round((contrato.volumen_contratado or 0) * 0.3, 2)),
                volumen_entregado_tn=0,
                estado=contrato.estado,
                condicion="Camion a puerto",
            )
        )
    db.add_all(contratos_venta)
    await db.flush()
    for legacy, new in zip(contratos, contratos_venta, strict=False):
        legacy_contract_map[legacy.id] = new

    entregas = []
    for idx, entrega in enumerate(entregas_comerciales):
        if entrega.contrato_id not in legacy_contract_map:
            continue
        contract = legacy_contract_map[entrega.contrato_id]
        matching_remito = next((item for item in remitos if item.empresa_id == contract.empresa_id and item.proveedor_id is None), None)
        entregas.append(
            Entrega(
                contrato_venta_id=contract.id,
                remito_id=matching_remito.id if matching_remito else None,
                deposito_id=None,
                fecha_programada=entrega.fecha_programada,
                fecha_entrega=entrega.fecha_entrega,
                volumen_tn=entrega.volumen_tn,
                calidad="camara",
                estado=entrega.estado,
            )
        )
    if not entregas:
        for contract in contratos_venta:
            entregas.append(
                Entrega(
                    contrato_venta_id=contract.id,
                    remito_id=None,
                    deposito_id=None,
                    fecha_programada=contract.fecha_entrega_desde or today,
                    fecha_entrega=None if contract.estado == "vigente" else contract.fecha_entrega_hasta,
                    volumen_tn=round((contract.volumen_tn or 0) * 0.5, 2),
                    calidad="camara",
                    estado="pendiente" if contract.estado == "vigente" else "entregada",
                )
            )
    db.add_all(entregas)
    await db.flush()

    fijaciones = []
    for contract in contratos_venta:
        if contract.precio_tn:
            fijaciones.append(
                Fijacion(
                    contrato_venta_id=contract.id,
                    fecha_fijacion=contract.fecha_contrato + timedelta(days=12),
                    volumen_tn=contract.volumen_fijado_tn,
                    precio_tn=contract.precio_tn,
                    mercado_referencia="Rosario",
                    observaciones="Fijacion registrada en contrato comercial",
                )
            )
        elif contract.estado == "vigente":
            fijaciones.append(
                Fijacion(
                    contrato_venta_id=contract.id,
                    fecha_fijacion=today - timedelta(days=5 + (contract.id % 6)),
                    volumen_tn=round((contract.volumen_tn or 0) * 0.22, 2),
                    precio_tn=round((productos_by_id[contract.producto_id].precio_referencia or 0) * 0.98, 2),
                    mercado_referencia="Rosario",
                    observaciones="Fijacion parcial recomendada por exposicion abierta",
                )
            )
    db.add_all(fijaciones)
    await db.flush()

    liquidaciones = []
    for idx, venta in enumerate(ventas):
        producto = productos_by_id.get(venta.producto_id)
        candidate_contracts = [
            item for item in contratos_venta
            if item.empresa_id == venta.empresa_id and item.campania_id == venta.campania_id and item.producto_id == venta.producto_id
        ]
        contract = candidate_contracts[idx % len(candidate_contracts)] if candidate_contracts else None
        entrega_rel = next((item for item in entregas if contract and item.contrato_venta_id == contract.id), None)
        liquidaciones.append(
            Liquidacion(
                contrato_venta_id=contract.id if contract else None,
                entrega_id=entrega_rel.id if entrega_rel else None,
                cliente_id=venta.cliente_id,
                numero=f"LIQ-{venta.empresa_id:02d}-{idx + 1:05d}",
                fecha_liquidacion=venta.fecha + timedelta(days=2),
                volumen_tn=venta.volumen,
                precio_tn=venta.precio_tn,
                bonificaciones=round(venta.total * 0.005, 2),
                gastos_comerciales=round(venta.total * 0.032, 2),
                importe_neto=round(venta.total * 0.963, 2),
                moneda_id=moneda_by_code["ARS"].id,
            )
        )
    db.add_all(liquidaciones)
    await db.flush()

    posiciones_erp = []
    for position in posiciones:
        posiciones_erp.append(
            PosicionComercialERP(
                empresa_id=position.empresa_id,
                campania_id=position.campania_id,
                cultivo_id=position.cultivo_id,
                toneladas_estimadas=round((position.toneladas_producidas or 0) * 1.07, 2),
                toneladas_producidas=position.toneladas_producidas,
                toneladas_contratadas=position.toneladas_comprometidas,
                toneladas_fijadas=position.toneladas_fijadas,
                toneladas_entregadas=position.toneladas_entregadas,
                toneladas_sin_precio=max((position.toneladas_producidas or 0) - (position.toneladas_fijadas or 0), 0),
                stock_fisico_tn=position.stock_fisico,
                precio_promedio=position.precio_referencia * 0.98 if position.precio_referencia else None,
                precio_mercado=position.precio_referencia,
                riesgo="alto" if (position.toneladas_producidas or 0) and ((position.toneladas_producidas - position.toneladas_fijadas) / position.toneladas_producidas) > 0.35 else "medio",
            )
        )
    db.add_all(posiciones_erp)
    await db.flush()

    # Reconciliacion de calidad de datos:
    # 1. Documentos historicos de compra para ingresos legacy.
    # 2. Remitos de venta y agregados de contratos coherentes.
    # 3. Movimientos de apertura/ajuste para que stock cierre con la operacion.
    # 4. Sincronizacion de stock legacy, stock proyectado y posiciones comerciales.
    contract_by_id = {item.id: item for item in contratos_venta}
    stock_actual_grain_by_key = {
        (item.establecimiento_id, item.producto_id): item
        for item in stock_actual_rows
        if item.producto_id is not None
    }
    stock_actual_input_by_key = {
        (item.establecimiento_id, item.insumo_id): item
        for item in stock_actual_rows
        if item.insumo_id is not None
    }
    projection_by_key = {
        (item.establecimiento_id, item.insumo_id): item
        for item in stock_proyectado
    }
    sales_dates_by_key = defaultdict(list)
    for venta in ventas:
        sales_dates_by_key[(venta.empresa_id, venta.campania_id, venta.producto_id)].append(venta.fecha)

    historical_purchase_requests = []
    historical_purchase_orders = []
    historical_purchase_contracts = []
    historical_purchase_remitos = []
    historical_ingresos = [item for item in movimientos_insumo if item.tipo == "ingreso"]
    for idx, movimiento in enumerate(historical_ingresos):
        establecimiento = establecimientos_by_id[movimiento.establecimiento_id]
        insumo = insumos_by_id[movimiento.insumo_id]
        proveedor = _supplier_for_insumo(proveedores, insumo)
        solicitante = empleados_by_est_role.get((establecimiento.id, "deposito")) or empleados_by_est[establecimiento.id][0]
        pedido = PedidoCompra(
            empresa_id=establecimiento.empresa_id,
            establecimiento_id=establecimiento.id,
            centro_costo_id=centro_costo_operativo[establecimiento.id].id,
            solicitante_id=solicitante.id,
            numero=f"HSP-{establecimiento.id:02d}-{idx + 1:04d}",
            fecha_pedido=movimiento.fecha - timedelta(days=7 + (idx % 3)),
            estado="cerrado",
            prioridad="alta" if insumo.tipo in {"combustible", "fertilizante"} else "media",
            moneda_id=moneda_by_code["ARS"].id,
            monto_estimado=movimiento.costo_total,
            observaciones="Pedido historico generado para cerrar trazabilidad de ingresos legacy",
        )
        historical_purchase_requests.append(pedido)
    db.add_all(historical_purchase_requests)
    await db.flush()

    for idx, movimiento in enumerate(historical_ingresos):
        establecimiento = establecimientos_by_id[movimiento.establecimiento_id]
        insumo = insumos_by_id[movimiento.insumo_id]
        proveedor = _supplier_for_insumo(proveedores, insumo)
        pedido = historical_purchase_requests[idx]
        deposito = deposito_by_est_tipo[(establecimiento.id, "insumos")]
        orden = OrdenCompra(
            empresa_id=establecimiento.empresa_id,
            pedido_compra_id=pedido.id,
            proveedor_id=proveedor.id,
            deposito_id=deposito.id,
            numero=f"HOC-{establecimiento.empresa_id:02d}-{idx + 1:04d}",
            fecha_orden=pedido.fecha_pedido + timedelta(days=1),
            fecha_entrega_estimada=movimiento.fecha,
            estado="recibida",
            moneda_id=moneda_by_code["ARS"].id,
            monto_total=movimiento.costo_total,
            condicion_pago="30 dias",
        )
        historical_purchase_orders.append(orden)
    db.add_all(historical_purchase_orders)
    await db.flush()

    for idx, movimiento in enumerate(historical_ingresos):
        insumo = insumos_by_id[movimiento.insumo_id]
        orden = historical_purchase_orders[idx]
        remito = Remito(
            empresa_id=orden.empresa_id,
            proveedor_id=orden.proveedor_id,
            cliente_id=None,
            orden_compra_id=orden.id,
            contrato_venta_id=None,
            numero=f"HRC-{orden.empresa_id:02d}-{idx + 1:05d}",
            fecha_remito=movimiento.fecha,
            tipo="compra",
            estado="recibido",
            observaciones="Remito historico asociado a ingreso legacy",
        )
        historical_purchase_remitos.append(remito)
        historical_purchase_contracts.append(
            ContratoCompra(
                empresa_id=orden.empresa_id,
                proveedor_id=orden.proveedor_id,
                producto_id=None,
                insumo_id=insumo.id,
                numero=f"HCC-{orden.empresa_id:02d}-{idx + 1:04d}",
                fecha_contrato=orden.fecha_orden,
                fecha_entrega=movimiento.fecha,
                cantidad=movimiento.cantidad,
                precio_unitario=_safe_div(movimiento.costo_total, movimiento.cantidad),
                moneda_id=moneda_by_code["ARS"].id,
                estado="cumplido",
            )
        )
    db.add_all(historical_purchase_contracts + historical_purchase_remitos)
    await db.flush()

    for idx, movimiento in enumerate(historical_ingresos):
        ingreso_row = next(
            item
            for item in ingresos_insumos
            if item.movimiento_stock_id == legacy_movement_map[movimiento.id].id
        )
        ingreso_row.orden_compra_id = historical_purchase_orders[idx].id
        ingreso_row.remito_id = historical_purchase_remitos[idx].id

    pedidos_compra.extend(historical_purchase_requests)
    ordenes_compra.extend(historical_purchase_orders)
    contratos_compra.extend(historical_purchase_contracts)
    remitos.extend(historical_purchase_remitos)

    venta_remitos = []
    for idx, entrega in enumerate(entregas):
        contract = contract_by_id.get(entrega.contrato_venta_id)
        if not contract:
            continue
        remito_date = entrega.fecha_entrega or entrega.fecha_programada
        venta_remitos.append(
            Remito(
                empresa_id=contract.empresa_id,
                proveedor_id=None,
                cliente_id=contract.cliente_id,
                orden_compra_id=None,
                contrato_venta_id=contract.id,
                numero=f"HRV-{contract.empresa_id:02d}-{idx + 1:05d}",
                fecha_remito=remito_date,
                tipo="venta",
                estado="emitido" if entrega.estado != "entregada" else "cerrado",
                observaciones="Remito comercial generado desde entregas ERP",
            )
        )
    db.add_all(venta_remitos)
    await db.flush()
    for entrega, remito in zip(entregas, venta_remitos, strict=False):
        entrega.remito_id = remito.id
    remitos.extend(venta_remitos)

    for contract in contratos_venta:
        related_deliveries = [item for item in entregas if item.contrato_venta_id == contract.id]
        related_fixations = [item for item in fijaciones if item.contrato_venta_id == contract.id]
        delivered_qty = round(sum(item.volumen_tn or 0 for item in related_deliveries), 2)
        fixed_qty = round(sum(item.volumen_tn or 0 for item in related_fixations), 2)
        contract.volumen_entregado_tn = min(delivered_qty, contract.volumen_tn or 0)
        contract.volumen_fijado_tn = min(fixed_qty, contract.volumen_tn or 0)

        related_sales = sales_dates_by_key.get((contract.empresa_id, contract.campania_id, contract.producto_id), [])
        reference_dates = [
            *(item.fecha_entrega or item.fecha_programada for item in related_deliveries if item.fecha_programada),
            *related_sales,
        ]
        if reference_dates:
            earliest_reference = min(reference_dates)
            proposed_contract_date = earliest_reference - timedelta(days=20)
            if proposed_contract_date < contract.fecha_contrato:
                contract.fecha_contrato = proposed_contract_date
        if contract.fecha_entrega_desde and contract.fecha_entrega_desde < contract.fecha_contrato:
            contract.fecha_entrega_desde = contract.fecha_contrato + timedelta(days=10)
        if contract.fecha_entrega_hasta and contract.fecha_entrega_desde and contract.fecha_entrega_hasta < contract.fecha_entrega_desde:
            contract.fecha_entrega_hasta = contract.fecha_entrega_desde + timedelta(days=12)
        for fixation in related_fixations:
            if fixation.fecha_fijacion < contract.fecha_contrato:
                fixation.fecha_fijacion = contract.fecha_contrato + timedelta(days=5)

    transfer_movement_rows = []
    for idx, transfer in enumerate(transferencias):
        insumo = insumos_by_id.get(transfer.insumo_id) if transfer.insumo_id else None
        unidad_id = unidad_by_code.get(insumo.unidad, unidad_by_code["lt"]).id if insumo else unidad_by_code["tn"].id
        origin_est = next(item.establecimiento_id for item in depositos if item.id == transfer.deposito_origen_id)
        target_est = next(item.establecimiento_id for item in depositos if item.id == transfer.deposito_destino_id)
        transfer_movement_rows.extend(
            [
                MovimientoStock(
                    empresa_id=transfer.empresa_id,
                    establecimiento_id=origin_est,
                    deposito_id=transfer.deposito_origen_id,
                    producto_id=transfer.producto_id,
                    insumo_id=transfer.insumo_id,
                    lote_campania_id=None,
                    fecha_movimiento=transfer.fecha_transferencia,
                    tipo_movimiento="transferencia_salida",
                    origen="transferencia",
                    referencia=transfer.referencia,
                    cantidad=transfer.cantidad,
                    unidad_medida_id=unidad_id,
                    costo_unitario=None,
                    monto_total=None,
                    observaciones="Salida por transferencia interna",
                ),
                MovimientoStock(
                    empresa_id=transfer.empresa_id,
                    establecimiento_id=target_est,
                    deposito_id=transfer.deposito_destino_id,
                    producto_id=transfer.producto_id,
                    insumo_id=transfer.insumo_id,
                    lote_campania_id=None,
                    fecha_movimiento=transfer.fecha_transferencia,
                    tipo_movimiento="transferencia_entrada",
                    origen="transferencia",
                    referencia=transfer.referencia,
                    cantidad=transfer.cantidad,
                    unidad_medida_id=unidad_id,
                    costo_unitario=None,
                    monto_total=None,
                    observaciones="Ingreso por transferencia interna",
                ),
            ]
        )
    db.add_all(transfer_movement_rows)
    await db.flush()
    movimientos_stock.extend(transfer_movement_rows)

    def _movement_sign(tipo_movimiento: str) -> int:
        if tipo_movimiento in {"ingreso", "ingreso_produccion", "transferencia_entrada", "saldo_inicial", "ajuste_positivo"}:
            return 1
        if tipo_movimiento in {"consumo", "egreso_venta", "transferencia_salida", "ajuste_negativo"}:
            return -1
        return 0

    movement_balance = defaultdict(float)
    movement_avg_cost = defaultdict(lambda: {"qty": 0.0, "value": 0.0})
    for row in movimientos_stock:
        key = (row.establecimiento_id, row.producto_id, row.insumo_id)
        sign = _movement_sign(row.tipo_movimiento)
        movement_balance[key] += sign * (row.cantidad or 0)
        if row.costo_unitario and sign > 0:
            movement_avg_cost[key]["qty"] += row.cantidad or 0
            movement_avg_cost[key]["value"] += (row.cantidad or 0) * row.costo_unitario

    stock_reconciliation_rows = []
    for stock in stocks:
        key = (stock.establecimiento_id, stock.producto_id, None)
        current_net = movement_balance[key]
        target_qty = round((stock.volumen_disponible or 0) + (stock.volumen_comprometido or 0), 2)
        delta = round(target_qty - current_net, 2)
        if abs(delta) <= 0.01:
            continue
        stock_reconciliation_rows.append(
            MovimientoStock(
                empresa_id=establecimientos_by_id[stock.establecimiento_id].empresa_id,
                establecimiento_id=stock.establecimiento_id,
                deposito_id=deposito_by_est_tipo[(stock.establecimiento_id, "granos")].id,
                producto_id=stock.producto_id,
                insumo_id=None,
                lote_campania_id=None,
                fecha_movimiento=campanias[0].fecha_inicio - timedelta(days=10),
                tipo_movimiento="saldo_inicial" if delta > 0 else "ajuste_negativo",
                origen="reconciliacion_seed_erp",
                referencia=f"STK-G-{stock.id}",
                cantidad=abs(delta),
                unidad_medida_id=unidad_by_code["tn"].id,
                costo_unitario=productos_by_id[stock.producto_id].precio_referencia if productos_by_id.get(stock.producto_id) else None,
                monto_total=abs(delta) * (productos_by_id[stock.producto_id].precio_referencia or 0) if productos_by_id.get(stock.producto_id) else None,
                observaciones="Apertura/ajuste para reconciliar stock con cosecha y ventas",
            )
        )
        movement_balance[key] += delta

    for (establecimiento_id, insumo_id), projection in projection_by_key.items():
        key = (establecimiento_id, None, insumo_id)
        current_net = movement_balance[key]
        insumo = insumos_by_id[insumo_id]
        if insumo.tipo == "combustible":
            desired_buffer = round(max(projection.stock_actual or 0, (projection.consumo_plan_mes or 0) * 0.35), 2)
        elif insumo.tipo == "fertilizante":
            desired_buffer = round(max(projection.stock_actual or 0, (projection.consumo_plan_mes or 0) * 0.18), 2)
        elif insumo.tipo == "semilla":
            desired_buffer = round(max(projection.stock_actual or 0, 0), 2)
        else:
            desired_buffer = round(max(projection.stock_actual or 0, (projection.consumo_plan_mes or 0) * 0.1), 2)
        target_qty = max(desired_buffer, round(max(current_net, 0), 2))
        delta = round(target_qty - current_net, 2)
        if abs(delta) <= 0.01:
            continue
        stock_reconciliation_rows.append(
            MovimientoStock(
                empresa_id=establecimientos_by_id[establecimiento_id].empresa_id,
                establecimiento_id=establecimiento_id,
                deposito_id=deposito_by_est_tipo[(establecimiento_id, "insumos")].id,
                producto_id=None,
                insumo_id=insumo_id,
                lote_campania_id=None,
                fecha_movimiento=campanias[0].fecha_inicio - timedelta(days=12),
                tipo_movimiento="saldo_inicial" if delta > 0 else "ajuste_negativo",
                origen="reconciliacion_seed_erp",
                referencia=f"STK-I-{establecimiento_id}-{insumo_id}",
                cantidad=abs(delta),
                unidad_medida_id=unidad_by_code.get(insumo.unidad, unidad_by_code["lt"]).id,
                costo_unitario=insumo.precio_unitario,
                monto_total=abs(delta) * insumo.precio_unitario,
                observaciones="Apertura/ajuste para reconciliar compras, consumos y stock actual",
            )
        )
        movement_balance[key] += delta

    db.add_all(stock_reconciliation_rows)
    await db.flush()
    movimientos_stock.extend(stock_reconciliation_rows)

    for stock in stocks:
        product = productos_by_id.get(stock.producto_id)
        if not product:
            continue
        key = (stock.establecimiento_id, stock.producto_id, None)
        final_qty = round(max(movement_balance[key], 0), 2)
        reserved = round(min(stock.volumen_comprometido or 0, final_qty), 2)
        available = round(max(final_qty - reserved, 0), 2)
        stock.volumen_disponible = available
        stock.volumen_comprometido = reserved
        stock.volumen_vendido = round(assigned_sales_by_stock_id.get(stock.id, stock.volumen_vendido or 0), 2)
        stock.fecha_actualizacion = datetime.utcnow()

        stock_row = stock_actual_grain_by_key.get((stock.establecimiento_id, stock.producto_id))
        if stock_row:
            stock_row.cantidad = final_qty
            stock_row.reservado = reserved
            stock_row.disponible = available
            stock_row.costo_unitario = product.precio_referencia
            stock_row.valor_total = round(final_qty * (product.precio_referencia or 0), 2)

    for (establecimiento_id, insumo_id), projection in projection_by_key.items():
        insumo = insumos_by_id[insumo_id]
        key = (establecimiento_id, None, insumo_id)
        final_qty = round(max(movement_balance[key], 0), 2)
        reserved = round(final_qty * 0.12, 2) if final_qty > 0 else 0
        available = round(max(final_qty - reserved, 0), 2)

        stock_row = stock_actual_input_by_key.get((establecimiento_id, insumo_id))
        if stock_row:
            stock_row.cantidad = final_qty
            stock_row.reservado = reserved
            stock_row.disponible = available
            stock_row.costo_unitario = insumo.precio_unitario
            stock_row.valor_total = round(final_qty * insumo.precio_unitario, 2)

        projection.stock_actual = final_qty
        projection.cobertura_dias = round(_safe_div(final_qty, max((projection.consumo_real_mes or 0) / 30, 0.1)), 1)
        projection.cobertura_ha = round(_safe_div(final_qty, max((projection.consumo_real_mes or 0) / 180, 0.1)), 1)
        projection.quiebre_en_dias = None if projection.cobertura_dias > 45 else max(int(projection.cobertura_dias), 1)
        projection.compra_sugerida = round(max((projection.consumo_plan_mes or 0) * 1.3 - final_qty, 0), 2)
        projection.stock_inmovilizado = round(max(final_qty - (projection.consumo_plan_mes or 0) * 2, 0), 2)
        projection.costo_inventario = round(final_qty * insumo.precio_unitario, 2)
        projection.severidad = "critical" if projection.cobertura_dias < 10 else "warning" if projection.cobertura_dias < 25 else "ok"

    contract_agg = defaultdict(lambda: {"comprometido": 0.0, "fijado": 0.0, "entregado": 0.0})
    for contract in contratos_venta:
        if contract.cultivo_id is None or contract.campania_id is None:
            continue
        key = (contract.empresa_id, contract.campania_id, contract.cultivo_id)
        contract_agg[key]["comprometido"] += contract.volumen_tn or 0
        contract_agg[key]["fijado"] += contract.volumen_fijado_tn or 0
        contract_agg[key]["entregado"] += contract.volumen_entregado_tn or 0

    stock_by_company_crop = defaultdict(float)
    for stock in stocks:
        product = productos_by_id.get(stock.producto_id)
        establecimiento = establecimientos_by_id.get(stock.establecimiento_id)
        if not product or not establecimiento or not product.cultivo_id:
            continue
        stock_by_company_crop[(establecimiento.empresa_id, product.cultivo_id)] += (stock.volumen_disponible or 0) + (stock.volumen_comprometido or 0)

    for position in posiciones:
        key = (position.empresa_id, position.campania_id, position.cultivo_id)
        if key in contract_agg:
            position.toneladas_comprometidas = round(contract_agg[key]["comprometido"], 2)
            position.toneladas_fijadas = round(contract_agg[key]["fijado"], 2)
            position.toneladas_entregadas = round(contract_agg[key]["entregado"], 2)
        position.stock_fisico = round(stock_by_company_crop.get((position.empresa_id, position.cultivo_id), 0), 2)

    for position in posiciones_erp:
        key = (position.empresa_id, position.campania_id, position.cultivo_id)
        if key in contract_agg:
            position.toneladas_contratadas = round(contract_agg[key]["comprometido"], 2)
            position.toneladas_fijadas = round(contract_agg[key]["fijado"], 2)
            position.toneladas_entregadas = round(contract_agg[key]["entregado"], 2)
            position.toneladas_sin_precio = round(max(position.toneladas_producidas - position.toneladas_fijadas, 0), 2)
        position.stock_fisico_tn = round(stock_by_company_crop.get((position.empresa_id, position.cultivo_id), 0), 2)

    await db.flush()

    presupuestos_campania = []
    lot_campaigns_by_company_camp = defaultdict(list)
    for item in lotes_campania:
        lot_campaigns_by_company_camp[(item.empresa_id, item.campania_id)].append(item)
    presupuestos_by_key = defaultdict(list)
    for item in presupuestos_lote:
        lote = lotes_by_id.get(item.lote_id)
        if not lote:
            continue
        establecimiento = establecimientos_by_id[lote.establecimiento_id]
        presupuestos_by_key[(establecimiento.empresa_id, item.campania_id)].append((item, lote))
    for (empresa_id, campania_id), items in presupuestos_by_key.items():
        ingreso_plan = sum(entry.ingreso_plan_ha * lote.hectareas for entry, lote in items)
        costo_directo = sum(entry.costo_directo_plan_ha * lote.hectareas for entry, lote in items)
        costo_indirecto = sum(entry.costo_indirecto_ha * lote.hectareas for entry, lote in items)
        presupuestos_campania.append(
            PresupuestoCampania(
                empresa_id=empresa_id,
                campania_id=campania_id,
                moneda_id=moneda_by_code["ARS"].id,
                ingreso_plan=round(ingreso_plan, 2),
                costo_directo_plan=round(costo_directo, 2),
                costo_indirecto_plan=round(costo_indirecto, 2),
                margen_plan=round(ingreso_plan - costo_directo - costo_indirecto, 2),
                capital_trabajo_objetivo=round(costo_directo * 0.48, 2),
                observaciones="Presupuesto agregado desde la capa de lotes",
            )
        )
    db.add_all(presupuestos_campania)
    await db.flush()

    costos_directos = []
    for labor in labores:
        lot_campaign = lote_campania_by_lote.get(labor.lote_id)
        lote = lotes_by_id.get(labor.lote_id)
        if not lot_campaign or not lote:
            continue
        costos_directos.append(
            CostoDirecto(
                empresa_id=lot_campaign.empresa_id,
                lote_campania_id=lot_campaign.id,
                centro_costo_id=lot_campaign.centro_costo_id,
                fecha_costo=labor.fecha,
                categoria="labor",
                subcategoria=labor.tipo,
                concepto=f"Labor {labor.tipo} - {lote.nombre}",
                monto=round((labor.costo_ha or 0) * (lote.hectareas or 0), 2),
                moneda_id=moneda_by_code["ARS"].id,
                referencia=f"LAB-{labor.id}",
                origen_tipo="labor_legacy",
                origen_id=labor.id,
            )
        )
    for movimiento in movimientos_insumo:
        if movimiento.tipo != "egreso" or not movimiento.lote_id or movimiento.lote_id not in lote_campania_by_lote:
            continue
        lot_campaign = lote_campania_by_lote[movimiento.lote_id]
        insumo = insumos_by_id[movimiento.insumo_id]
        costos_directos.append(
            CostoDirecto(
                empresa_id=lot_campaign.empresa_id,
                lote_campania_id=lot_campaign.id,
                centro_costo_id=lot_campaign.centro_costo_id,
                fecha_costo=movimiento.fecha,
                categoria="insumo",
                subcategoria=insumo.tipo,
                concepto=f"Consumo {insumo.nombre}",
                monto=movimiento.costo_total,
                moneda_id=moneda_by_code["ARS"].id,
                referencia=f"INS-{movimiento.id}",
                origen_tipo="movimiento_insumo_legacy",
                origen_id=movimiento.id,
            )
        )
    db.add_all(costos_directos)
    await db.flush()

    costos_indirectos = []
    for flujo in flujos:
        if flujo.tipo != "egreso" or flujo.categoria in {"venta", "insumos", "labores"}:
            continue
        company_lots = lot_campaigns_by_company_camp.get((flujo.empresa_id, flujo.campania_id), [])
        est_id = company_lots[0].establecimiento_id if company_lots else None
        cc = centro_costo_admin.get(flujo.empresa_id)
        costos_indirectos.append(
            CostoIndirecto(
                empresa_id=flujo.empresa_id,
                establecimiento_id=est_id,
                centro_costo_id=cc.id if cc else None,
                fecha_costo=flujo.fecha,
                categoria=flujo.categoria,
                concepto=flujo.concepto,
                monto=flujo.monto,
                moneda_id=moneda_by_code["ARS"].id,
            )
        )
    db.add_all(costos_indirectos)
    await db.flush()

    asignaciones = []
    for costo in costos_indirectos:
        eligible_lots = [
            item
            for item in lotes_campania
            if item.empresa_id == costo.empresa_id
            and campanias_by_id[item.campania_id].fecha_inicio <= costo.fecha_costo <= campanias_by_id[item.campania_id].fecha_fin
        ]
        if not eligible_lots:
            eligible_lots = [item for item in lotes_campania if item.empresa_id == costo.empresa_id and campanias_by_id[item.campania_id].activa]
        total_ha = sum(item.superficie_ha or 0 for item in eligible_lots)
        if not total_ha:
            continue
        for item in eligible_lots:
            share = (item.superficie_ha or 0) / total_ha
            asignaciones.append(
                AsignacionCosto(
                    costo_indirecto_id=costo.id,
                    lote_campania_id=item.id,
                    criterio="ha",
                    base_valor=item.superficie_ha or 0,
                    monto_asignado=round((costo.monto or 0) * share, 2),
                )
            )
    db.add_all(asignaciones)
    await db.flush()

    cuentas_cobrar = []
    cobranzas = []
    for idx, liquidacion in enumerate(liquidaciones):
        age_days = (today - liquidacion.fecha_liquidacion).days
        paid_ratio = 1.0 if age_days > 45 else 0.72 if age_days > 20 else 0.38
        paid_amount = round(liquidacion.importe_neto * paid_ratio, 2)
        venta = ventas[idx]
        cuentas_cobrar.append(
            CuentaCobrar(
                empresa_id=venta.empresa_id,
                cliente_id=liquidacion.cliente_id,
                liquidacion_id=liquidacion.id,
                numero_comprobante=f"FAC-{idx + 1:05d}",
                fecha_emision=liquidacion.fecha_liquidacion,
                fecha_vencimiento=liquidacion.fecha_liquidacion + timedelta(days=15),
                monto_original=liquidacion.importe_neto,
                saldo=round(liquidacion.importe_neto - paid_amount, 2),
                moneda_id=moneda_by_code["ARS"].id,
                estado="cobrada" if paid_ratio >= 0.99 else "parcial" if paid_ratio > 0 else "pendiente",
            )
        )
    db.add_all(cuentas_cobrar)
    await db.flush()
    for account in cuentas_cobrar:
        collected = round(account.monto_original - account.saldo, 2)
        if collected <= 0:
            continue
        split = [collected] if collected < account.monto_original * 0.55 else [round(collected * 0.55, 2), round(collected * 0.45, 2)]
        for pay_idx, amount in enumerate(split):
            cobranzas.append(
                Cobranza(
                    empresa_id=account.empresa_id,
                    cuenta_cobrar_id=account.id,
                    fecha_cobranza=account.fecha_emision + timedelta(days=7 + pay_idx * 8),
                    monto=amount,
                    moneda_id=moneda_by_code["ARS"].id,
                    medio_cobro="transferencia",
                    referencia=f"COB-{account.id:05d}-{pay_idx + 1}",
                )
            )
    db.add_all(cobranzas)
    await db.flush()

    cuentas_pagar = []
    pagos = []
    for idx, orden in enumerate(ordenes_compra):
        if orden.estado != "recibida":
            continue
        paid_ratio = 1.0 if idx % 4 == 0 else 0.55 if idx % 3 == 0 else 0
        paid_amount = round((orden.monto_total or 0) * paid_ratio, 2)
        cuentas_pagar.append(
            CuentaPagar(
                empresa_id=orden.empresa_id,
                proveedor_id=orden.proveedor_id,
                orden_compra_id=orden.id,
                numero_comprobante=f"FC-{idx + 1:05d}",
                fecha_emision=orden.fecha_orden,
                fecha_vencimiento=orden.fecha_orden + timedelta(days=30),
                monto_original=orden.monto_total or 0,
                saldo=round((orden.monto_total or 0) - paid_amount, 2),
                moneda_id=moneda_by_code["ARS"].id,
                estado="pagada" if paid_ratio >= 0.99 else "parcial" if paid_ratio > 0 else "pendiente",
            )
        )
    db.add_all(cuentas_pagar)
    await db.flush()
    for account in cuentas_pagar:
        paid = round(account.monto_original - account.saldo, 2)
        if paid <= 0:
            continue
        pagos.append(
            Pago(
                empresa_id=account.empresa_id,
                cuenta_pagar_id=account.id,
                fecha_pago=account.fecha_emision + timedelta(days=18),
                monto=paid,
                moneda_id=moneda_by_code["ARS"].id,
                medio_pago="transferencia",
                referencia=f"PAG-{account.id:05d}",
            )
        )
    db.add_all(pagos)
    await db.flush()

    partes_trabajo = []
    partes_maquinaria = []
    horas_maquina = []
    for idx, ejecucion in enumerate(ejec_siembra + ejec_fertilizacion + ejec_pulverizacion):
        maquinaria_id = getattr(ejecucion, "maquinaria_id", None)
        lot_campaign_id = None
        labor_tipo_id = None
        fecha = ejecucion.fecha_labor
        ha = getattr(ejecucion, "superficie_ejecutada_ha", 0)
        combustible = round(ha * (3.4 if isinstance(ejecucion, EjecucionSiembra) else 2.2), 2)
        if isinstance(ejecucion, EjecucionSiembra):
            plan = next(item for item in plan_siembra_rows if item.id == ejecucion.plan_siembra_id)
            lot_campaign_id = plan.lote_campania_id
            labor_tipo_id = plan.labor_tipo_id
        elif isinstance(ejecucion, EjecucionFertilizacion):
            plan = next(item for item in plan_fertilizacion_rows if item.id == ejecucion.plan_fertilizacion_id)
            lot_campaign_id = plan.lote_campania_id
            labor_tipo_id = labor_tipo_by_code["FERTILIZACION"].id
        else:
            plan = next(item for item in plan_pulverizacion_rows if item.id == ejecucion.plan_pulverizacion_id)
            lot_campaign_id = plan.lote_campania_id
            labor_tipo_id = labor_tipo_by_code["PULVERIZACION"].id
        lot_campaign = next(item for item in lotes_campania if item.id == lot_campaign_id)
        part = ParteTrabajo(
            empresa_id=lot_campaign.empresa_id,
            establecimiento_id=lot_campaign.establecimiento_id,
            lote_campania_id=lot_campaign_id,
            fecha_trabajo=fecha,
            labor_tipo_id=labor_tipo_id,
            maquinaria_id=maquinaria_id,
            implemento_id=getattr(ejecucion, "implemento_id", None),
            operador_id=getattr(ejecucion, "operador_id", None),
            contratista_id=getattr(ejecucion, "contratista_id", None),
            horas_operativas=getattr(ejecucion, "horas_operativas", 0) or 0,
            horas_improductivas=getattr(ejecucion, "horas_improductivas", 0) or 0,
            superficie_trabajada_ha=ha,
            combustible_litros=combustible,
            estado="cerrado",
            observaciones=getattr(ejecucion, "observaciones", None),
        )
        partes_trabajo.append(part)
    db.add_all(partes_trabajo)
    await db.flush()

    for idx, part in enumerate(partes_trabajo):
        if not part.maquinaria_id:
            continue
        parte_maq = ParteMaquinaria(
            maquinaria_id=part.maquinaria_id,
            establecimiento_id=part.establecimiento_id,
            lote_campania_id=part.lote_campania_id,
            fecha=part.fecha_trabajo,
            labor_tipo_id=part.labor_tipo_id,
            horometro_inicio=round((idx + 1) * 8.5, 1),
            horometro_fin=round((idx + 1) * 8.5 + part.horas_operativas + part.horas_improductivas, 1),
            horas_operativas=part.horas_operativas,
            horas_improductivas=part.horas_improductivas,
            hectareas=part.superficie_trabajada_ha,
            operador_id=part.operador_id,
            observaciones=part.observaciones,
        )
        partes_maquinaria.append(parte_maq)
    db.add_all(partes_maquinaria)
    await db.flush()

    for part in partes_maquinaria:
        horas_maquina.extend(
            [
                HorasMaquina(
                    maquinaria_id=part.maquinaria_id,
                    parte_maquinaria_id=part.id,
                    fecha=part.fecha,
                    tipo_hora="productiva",
                    horas=part.horas_operativas,
                    costo_hora=round(42000 + (part.maquinaria_id % 6) * 3500, 2),
                    costo_total=round(part.horas_operativas * (42000 + (part.maquinaria_id % 6) * 3500), 2),
                ),
                HorasMaquina(
                    maquinaria_id=part.maquinaria_id,
                    parte_maquinaria_id=part.id,
                    fecha=part.fecha,
                    tipo_hora="improductiva",
                    horas=part.horas_improductivas,
                    costo_hora=round(25500 + (part.maquinaria_id % 4) * 2200, 2),
                    costo_total=round(part.horas_improductivas * (25500 + (part.maquinaria_id % 4) * 2200), 2),
                ),
            ]
        )
    db.add_all(horas_maquina)
    await db.flush()

    maint_preventive = []
    maint_corrective = []
    downtime_by_machine = defaultdict(list)
    for item in downtime_rows:
        downtime_by_machine[item.maquinaria_id].append(item)
    for item in service_schedule:
        maint_preventive.append(
            MantenimientoPreventivo(
                maquinaria_id=item.maquinaria_id,
                service_schedule_id=item.id,
                fecha_programada=item.fecha_programada,
                fecha_ejecucion=item.fecha_programada if item.completado else None,
                horas_equipo=item.horas_programadas,
                descripcion=item.tipo_service,
                costo=round(185000 + (item.maquinaria_id % 5) * 48000, 2),
                estado="completado" if item.completado else "pendiente",
            )
        )
    for item in mantenimientos:
        if item.tipo == "preventivo":
            maint_preventive.append(
                MantenimientoPreventivo(
                    maquinaria_id=item.maquinaria_id,
                    service_schedule_id=None,
                    fecha_programada=item.fecha,
                    fecha_ejecucion=item.fecha,
                    horas_equipo=item.horas_maquina,
                    descripcion=item.descripcion or "Service preventivo",
                    costo=item.costo,
                    estado="completado",
                )
            )
        else:
            related_downtime = downtime_by_machine[item.maquinaria_id][0] if downtime_by_machine[item.maquinaria_id] else None
            maint_corrective.append(
                MantenimientoCorrectivo(
                    maquinaria_id=item.maquinaria_id,
                    downtime_id=related_downtime.id if related_downtime else None,
                    fecha_falla=datetime.combine(item.fecha, time(8, 0)),
                    fecha_resolucion=datetime.combine(item.fecha + timedelta(days=2), time(16, 0)),
                    descripcion=item.descripcion or "Correctivo",
                    criticidad="alta" if item.costo > 900000 else "media",
                    costo=item.costo,
                    horas_perdidas=round((related_downtime.horas_downtime if related_downtime else 8) or 8, 2),
                    estado="cerrado",
                )
            )
    for item in downtime_rows:
        if any(row.downtime_id == item.id for row in maint_corrective):
            continue
        maint_corrective.append(
            MantenimientoCorrectivo(
                maquinaria_id=item.maquinaria_id,
                downtime_id=item.id,
                fecha_falla=item.fecha_inicio,
                fecha_resolucion=item.fecha_fin,
                descripcion=item.motivo,
                criticidad=item.criticidad,
                costo=round((item.horas_downtime or 0) * 42000, 2),
                horas_perdidas=item.horas_downtime,
                estado="cerrado" if item.fecha_fin else "abierto",
            )
        )
    db.add_all(maint_preventive + maint_corrective)
    await db.flush()

    disponibilidad = []
    downtime_by_machine_day = defaultdict(float)
    for item in downtime_rows:
        current = item.fecha_inicio.date()
        end_date = (item.fecha_fin or item.fecha_inicio).date()
        while current <= end_date:
            downtime_by_machine_day[(item.maquinaria_id, current)] += round((item.horas_downtime or 0) / max((end_date - item.fecha_inicio.date()).days + 1, 1), 2)
            current += timedelta(days=1)
    for maquina in maquinarias:
        for day_offset in range(120):
            current_day = today - timedelta(days=day_offset)
            downtime_hours = downtime_by_machine_day[(maquina.id, current_day)]
            base_capacity = 10 if maquina.tipo in {"cosechadora", "sembradora"} else 8
            service_penalty = 3 if any(item.maquinaria_id == maquina.id and item.fecha_programada == current_day for item in maint_preventive) else 0
            productive = max(base_capacity - downtime_hours - service_penalty - ((day_offset + maquina.id) % 3) * 0.4, 0)
            improductive = round(max(base_capacity - productive - downtime_hours, 0), 2)
            disponible = maquina.estado != "baja" and downtime_hours < base_capacity * 0.9
            disponibilidad.append(
                DisponibilidadEquipo(
                    maquinaria_id=maquina.id,
                    fecha=current_day,
                    disponible=disponible,
                    capacidad_teorica_horas=base_capacity,
                    horas_productivas=round(productive, 2),
                    horas_improductivas=improductive,
                    downtime_horas=round(downtime_hours, 2),
                    criticidad="alta" if maquina.tipo in {"cosechadora", "sembradora"} else "media",
                )
            )
    db.add_all(disponibilidad)
    await db.flush()

    clima_rows = []
    for establecimiento in establecimientos:
        province_factor = {
            "Córdoba": 1.0,
            "Santa Fe": 1.08,
            "Buenos Aires": 0.94,
            "La Pampa": 0.88,
        }.get(establecimiento.provincia, 1.0)
        for day_offset in range(365):
            current_day = today - timedelta(days=364 - day_offset)
            day_of_year = current_day.timetuple().tm_yday
            season_wave = math.sin((2 * math.pi * day_of_year) / 365)
            rain_wave = math.sin((2 * math.pi * (day_of_year + 35 + establecimiento.id * 5)) / 45)
            temp_media = 18 + season_wave * 9 * province_factor + math.cos((2 * math.pi * day_of_year) / 28) * 1.8
            precip = max((rain_wave + 0.4) * 9 + ((establecimiento.id + day_offset) % 5 - 2) * 1.4, 0)
            humedad = max(min(68 + precip * 1.2 - season_wave * 6, 96), 34)
            riesgo = "alto" if precip > 22 or humedad > 88 else "medio" if precip > 10 else "bajo"
            clima_rows.append(
                ClimaDiario(
                    establecimiento_id=establecimiento.id,
                    fecha=current_day,
                    temp_min_c=round(temp_media - (7.5 + (day_offset % 3) * 0.6), 1),
                    temp_max_c=round(temp_media + (8.1 + (day_offset % 4) * 0.5), 1),
                    temp_media_c=round(temp_media, 1),
                    precipitacion_mm=round(precip, 1),
                    humedad_relativa=round(humedad, 1),
                    viento_kmh=round(11 + abs(math.cos(day_of_year / 18)) * 8 + (establecimiento.id % 4), 1),
                    et0_mm=round(max(2.8 + season_wave * 1.5, 0.8), 2),
                    riesgo_operativo=riesgo,
                    fuente="Seed ERP / Open-Meteo style",
                )
            )
    db.add_all(clima_rows)
    await db.flush()

    commodity_base = {
        "Soja": 286,
        "Maiz": 182,
        "Trigo": 221,
        "Girasol": 338,
        "Sorgo": 161,
    }
    commodity_rows = []
    for cultivo in cultivos:
        base_price = commodity_base.get(cultivo.nombre, 200)
        prev_price = None
        for day_offset in range(210):
            current_day = today - timedelta(days=209 - day_offset)
            trend = day_offset * (0.04 if cultivo.nombre in {"Girasol", "Trigo"} else 0.015)
            swing = math.sin((day_offset + cultivo.id * 5) / 11) * 6 + math.cos((day_offset + cultivo.id * 3) / 23) * 3
            price = round(base_price + trend + swing, 2)
            commodity_rows.append(
                CommoditiesPrecio(
                    cultivo_id=cultivo.id,
                    fecha=current_day,
                    mercado="CBOT" if cultivo.nombre in {"Soja", "Maiz", "Trigo"} else "MATBA",
                    moneda_id=moneda_by_code["USD"].id,
                    precio=price,
                    precio_min=round(price - 4.8, 2),
                    precio_max=round(price + 4.8, 2),
                    volumen=round(850 + (day_offset % 15) * 42 + cultivo.id * 30, 2),
                    interes_abierto=round(1200 + (day_offset % 22) * 55 + cultivo.id * 40, 2),
                    fuente="Series externas sintetizadas para seed ERP",
                )
            )
            prev_price = price
    db.add_all(commodity_rows)
    await db.flush()

    macro_rows = []
    prev_values = {}
    for day_offset in range(210):
        current_day = today - timedelta(days=209 - day_offset)
        fx_official = round(950 + day_offset * 0.85 + math.sin(day_offset / 17) * 3.2, 2)
        fx_wholesale = round(fx_official * 0.992, 2)
        tasa = round(38 - day_offset * 0.035 + math.cos(day_offset / 13) * 1.2, 2)
        series_specs = [
            ("fx_oficial", "Tipo de Cambio Oficial", "fx", fx_official, "ARS/USD"),
            ("fx_mayorista", "Tipo de Cambio Mayorista", "fx", fx_wholesale, "ARS/USD"),
            ("tasa_politica", "Tasa de Referencia", "tasas", tasa, "%"),
        ]
        for code, name, category, value, unit in series_specs:
            previous = prev_values.get(code)
            macro_rows.append(
                MacroSerie(
                    codigo=code,
                    nombre=name,
                    categoria=category,
                    fecha=current_day,
                    valor=value,
                    unidad=unit,
                    variacion_diaria=_series_variation(value, previous),
                    variacion_mensual=None,
                    variacion_interanual=None,
                    fuente="BCRA / series sintetizadas",
                )
            )
            prev_values[code] = value

    monthly_series = [
        ("inflacion_mensual", "Inflacion Mensual", "precios", "%", 9.2, -0.18),
        ("actividad", "Indice de Actividad", "actividad", "indice", 103.5, 0.12),
    ]
    monthly_history = defaultdict(list)
    for code, name, category, unit, base_value, slope in monthly_series:
        previous = None
        for month_offset in range(24):
            current_day = _month_start_shift(today.replace(day=1), month_offset - 23)
            value = round(base_value + slope * month_offset + math.sin(month_offset / 3.2) * (0.8 if code == "inflacion_mensual" else 1.6), 2)
            yearly_reference = monthly_history[code][-12] if len(monthly_history[code]) >= 12 else None
            macro_rows.append(
                MacroSerie(
                    codigo=code,
                    nombre=name,
                    categoria=category,
                    fecha=current_day,
                    valor=value,
                    unidad=unit,
                    variacion_diaria=None,
                    variacion_mensual=_series_variation(value, previous),
                    variacion_interanual=_series_variation(value, yearly_reference),
                    fuente="BCRA / Datos Argentina sintetizados",
                )
            )
            monthly_history[code].append(value)
            previous = value
    db.add_all(macro_rows)
    await db.flush()

    alerts = []
    commodity_latest = {}
    for item in commodity_rows[-len(cultivos):]:
        commodity_latest[item.cultivo_id] = item
    for cultivo in cultivos:
        latest = max((item for item in commodity_rows if item.cultivo_id == cultivo.id), key=lambda row: row.fecha)
        if latest.precio >= commodity_base.get(cultivo.nombre, 200) * 1.06:
            severity = "media"
            action = "Evaluar coberturas y fijaciones parciales"
            impact = "Mejora de margen comercial"
        elif latest.precio <= commodity_base.get(cultivo.nombre, 200) * 0.94:
            severity = "alta"
            action = "Revisar break-even y exposicion comercial"
            impact = "Compresion del margen esperado"
        else:
            severity = "baja"
            action = "Seguir monitoreando tendencia"
            impact = "Escenario neutral"
        alerts.append(
            AlertaContexto(
                tipo="mercado",
                modulo="commodities",
                referencia=cultivo.nombre,
                severidad=severity,
                fecha=today,
                titulo=f"{cultivo.nombre}: lectura de mercado actual",
                descripcion=f"Precio de referencia {latest.precio} USD/tn frente a rango historico reciente.",
                impacto=impact,
                accion_sugerida=action,
                fuente=latest.fuente,
            )
        )
    for establecimiento in establecimientos:
        clima_reciente = [item for item in clima_rows if item.establecimiento_id == establecimiento.id and item.fecha >= today - timedelta(days=6)]
        lluvia = sum(item.precipitacion_mm or 0 for item in clima_reciente)
        if lluvia < 12:
            alerts.append(
                AlertaContexto(
                    tipo="clima",
                    modulo="clima",
                    referencia=establecimiento.nombre,
                    severidad="alta",
                    fecha=today,
                    titulo=f"{establecimiento.nombre}: deficit hidrico reciente",
                    descripcion=f"Lluvia acumulada de 7 dias: {round(lluvia, 1)} mm.",
                    impacto="Riesgo operativo y agronomico sobre implantacion",
                    accion_sugerida="Repriorizar labores y monitorear humedad util",
                    fuente="Clima diario ERP",
                )
            )
        else:
            alerts.append(
                AlertaContexto(
                    tipo="clima",
                    modulo="clima",
                    referencia=establecimiento.nombre,
                    severidad="baja",
                    fecha=today,
                    titulo=f"{establecimiento.nombre}: ventana operativa favorable",
                    descripcion=f"Lluvia acumulada de 7 dias: {round(lluvia, 1)} mm.",
                    impacto="Condiciones razonables para avanzar con labores",
                    accion_sugerida="Sostener plan semanal",
                    fuente="Clima diario ERP",
                )
            )
    fx_latest = max((item for item in macro_rows if item.codigo == "fx_oficial"), key=lambda row: row.fecha)
    tasa_latest = max((item for item in macro_rows if item.codigo == "tasa_politica"), key=lambda row: row.fecha)
    infl_latest = max((item for item in macro_rows if item.codigo == "inflacion_mensual"), key=lambda row: row.fecha)
    alerts.append(
        AlertaContexto(
            tipo="macro",
            modulo="macro",
            referencia="Costo financiero",
            severidad="media" if tasa_latest.valor > infl_latest.valor * 3 else "baja",
            fecha=today,
            titulo="Lectura macro de campana",
            descripcion=f"Tasa {tasa_latest.valor}% vs inflacion mensual {infl_latest.valor}%, FX oficial {fx_latest.valor}.",
            impacto="Condiciona capital de trabajo y decisiones comerciales",
            accion_sugerida="Comparar financiacion bancaria vs canje y fijaciones",
            fuente="Macro series ERP",
        )
    )
    db.add_all(alerts)
    await db.flush()
