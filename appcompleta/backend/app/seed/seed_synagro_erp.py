from __future__ import annotations

import importlib
import pkgutil
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

import app.models as models_pkg
from app.models.campania import Campania
from app.models.cliente import Cliente
from app.models.comercial_v2 import ContratoV2, RemitoCampo, VentaV2
from app.models.cultivo import Cultivo
from app.models.empresa import Empresa
from app.models.erp_catalog import (
    Ambiente,
    Campo as ERPCampo,
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
    Variedad as ERPVariedad,
)
from app.models.erp_operational import (
    AsignacionCosto,
    Cobranza as ERPCobranza,
    ConsumoInsumo,
    ContratoVenta as ERPContratoVenta,
    CuentaCobrar as ERPCuentaCobrar,
    CostoDirecto as ERPCostoDirecto,
    CostoIndirecto as ERPCostoIndirecto,
    DisponibilidadEquipo,
    Entrega,
    Fijacion,
    HorasMaquina,
    Liquidacion as ERPLiquidacion,
    LoteCampania as ERPLoteCampania,
    MonitoreoPlaga,
    MovimientoStock,
    ParteMaquinaria,
    ParteTrabajo,
    PosicionComercialERP,
    PresupuestoCampania,
    RendimientoLote as ERPRendimientoLote,
    StockActual,
)
from app.models.establecimiento import Establecimiento
from app.models.financiero import CuentaCorriente, FlujoCajaV2, Presupuesto
from app.models.insumo import Insumo, MovimientoInsumo
from app.models.labor import Labor
from app.models.lemon_commercial import (
    CobranzasFact,
    ContratoVentaFact,
    CostosDirectosFact,
    CostosIndirectosFact,
    CuentasCobrarFact,
    EmbarqueFact,
    LiquidacionFact,
    PresupuestoLoteFact,
    StockFinalFact,
)
from app.models.lemon_dimensions import (
    CalibreDim,
    CampaniaDim,
    CampoDim,
    CanalDim,
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
from app.models.lemon_external import TipoCambioFact
from app.models.lemon_field import (
    AplicacionFitosanitariaFact,
    CosechaFact,
    FertirriegoFact,
    LoteCampaniaFact,
    RendimientoLoteFact,
    RiegoFact,
    ScoutingFact,
)
from app.models.lemon_packhouse import (
    ConsumoPackhouseFact,
    DowntimePackhouseFact,
    ManoObraPackhouseFact,
    MantenimientoPackhouseFact,
    PackhouseTurnoFact,
)
from app.models.lemon_quality import (
    ClasificacionCalidadFact,
    PackoutFact,
    RecepcionFrutaFact,
    RechazoFact,
)
from app.models.lote import Lote
from app.models.maquinaria import Maquinaria
from app.models.mantenimiento import Mantenimiento
from app.models.producto import Producto
from app.models.proveedor import Proveedor
from app.models.siembra import Siembra
from app.models.stock import Stock
from app.models.cosecha_v2 import CosechaV2


def _load_all_model_modules():
    for _, module_name, _ in pkgutil.iter_modules(models_pkg.__path__):
        if module_name.startswith("__"):
            continue
        importlib.import_module(f"app.models.{module_name}")


def _safe_float(value) -> float:
    return round(float(value or 0), 2)


def _safe_int(value) -> int:
    return int(value or 0)


def _cuit(prefix: int, number: int) -> str:
    return f"{prefix:02d}{number:09d}"


ERP_CLEAR_TABLES = [
    "cobranzas",
    "cuentas_cobrar",
    "asignaciones_costos",
    "costos_directos",
    "costos_indirectos",
    "presupuestos_campania",
    "posiciones_comerciales",
    "liquidaciones",
    "fijaciones",
    "entregas",
    "contratos_venta",
    "movimientos_stock",
    "stock_actual",
    "partes_trabajo",
    "consumos_insumos",
    "monitoreos_plagas",
    "rendimientos_lote",
    "disponibilidad_equipos",
    "horas_maquina",
    "partes_maquinaria",
    "implementos",
    "contratistas",
    "empleados",
    "labores_tipos",
    "categorias_producto",
    "centros_costos",
    "depositos",
    "monedas",
    "unidades_medida",
    "variedades",
    "ambientes",
    "campos",
    "unidades_negocio",
]

GENERIC_CLEAR_TABLES = [
    "remitos_campo",
    "ventas_v2",
    "contratos_v2",
    "flujo_caja_v2",
    "presupuestos",
    "stocks",
    "movimientos_insumo",
    "cosechas_v2",
    "siembras",
    "labores",
    "mantenimientos",
    "maquinarias",
    "insumos",
    "productos",
    "proveedores",
    "lotes",
    "clientes",
    "cultivos",
    "campanias",
    "establecimientos",
    "cuentas_corrientes",
    "empresas",
]


async def _clear_tables(db: AsyncSession, tables: list[str]):
    await db.execute(text("PRAGMA foreign_keys = OFF"))
    for table_name in tables:
        await db.execute(text(f"DELETE FROM {table_name}"))
    await db.execute(text("PRAGMA foreign_keys = ON"))


async def sync_synagro_erp(db: AsyncSession, force: bool = False) -> dict:
    _load_all_model_modules()

    existing = (await db.execute(select(Empresa).limit(1))).scalar_one_or_none()
    if existing and not force:
        return {"status": "skipped", "reason": "ERP Synagro-like ya sincronizado"}

    await _clear_tables(db, ERP_CLEAR_TABLES + GENERIC_CLEAR_TABLES)

    empresa_dim = (await db.execute(select(EmpresaDim))).scalars().first()
    campanias_dim = (await db.execute(select(CampaniaDim).order_by(CampaniaDim.campania_id))).scalars().all()
    establecimientos_dim = (await db.execute(select(EstablecimientoDim).order_by(EstablecimientoDim.establecimiento_id))).scalars().all()
    campos_dim = (await db.execute(select(CampoDim).order_by(CampoDim.campo_id))).scalars().all()
    lotes_dim = (await db.execute(select(LoteDim).order_by(LoteDim.lote_id))).scalars().all()
    variedades_dim = (await db.execute(select(VariedadDim).order_by(VariedadDim.variedad_id))).scalars().all()
    clientes_dim = (await db.execute(select(ClienteDim).order_by(ClienteDim.cliente_id))).scalars().all()
    mercados_dim = (await db.execute(select(MercadoDim).order_by(MercadoDim.mercado_id))).scalars().all()
    canales_dim = (await db.execute(select(CanalDim).order_by(CanalDim.canal_id))).scalars().all()
    destinos_dim = (await db.execute(select(DestinoFrutaDim).order_by(DestinoFrutaDim.destino_id))).scalars().all()
    depositos_dim = (await db.execute(select(DepositoDim).order_by(DepositoDim.deposito_id))).scalars().all()
    plagas_dim = (await db.execute(select(PlagaDim).order_by(PlagaDim.plaga_id))).scalars().all()
    enfermedades_dim = (await db.execute(select(EnfermedadDim).order_by(EnfermedadDim.enfermedad_id))).scalars().all()
    fecha_dim = (await db.execute(select(FechaDim))).scalars().all()

    lote_campania_fact = (await db.execute(select(LoteCampaniaFact))).scalars().all()
    cosechas_fact = (await db.execute(select(CosechaFact))).scalars().all()
    rendimientos_fact = (await db.execute(select(RendimientoLoteFact))).scalars().all()
    scouting_fact = (await db.execute(select(ScoutingFact))).scalars().all()
    aplicaciones_fact = (await db.execute(select(AplicacionFitosanitariaFact))).scalars().all()
    riego_fact = (await db.execute(select(RiegoFact))).scalars().all()
    fert_fact = (await db.execute(select(FertirriegoFact))).scalars().all()
    recepciones_fact = (await db.execute(select(RecepcionFrutaFact))).scalars().all()
    clasificacion_fact = (await db.execute(select(ClasificacionCalidadFact))).scalars().all()
    packout_fact = (await db.execute(select(PackoutFact))).scalars().all()
    rechazos_fact = (await db.execute(select(RechazoFact))).scalars().all()
    packhouse_turnos = (await db.execute(select(PackhouseTurnoFact))).scalars().all()
    downtime_fact = (await db.execute(select(DowntimePackhouseFact))).scalars().all()
    mano_obra_fact = (await db.execute(select(ManoObraPackhouseFact))).scalars().all()
    consumo_pack_fact = (await db.execute(select(ConsumoPackhouseFact))).scalars().all()
    mantenimiento_pack_fact = (await db.execute(select(MantenimientoPackhouseFact))).scalars().all()
    contratos_fact = (await db.execute(select(ContratoVentaFact))).scalars().all()
    embarques_fact = (await db.execute(select(EmbarqueFact))).scalars().all()
    liquidaciones_fact = (await db.execute(select(LiquidacionFact))).scalars().all()
    cuentas_fact = (await db.execute(select(CuentasCobrarFact))).scalars().all()
    cobranzas_fact = (await db.execute(select(CobranzasFact))).scalars().all()
    costos_directos_fact = (await db.execute(select(CostosDirectosFact))).scalars().all()
    costos_indirectos_fact = (await db.execute(select(CostosIndirectosFact))).scalars().all()
    presupuestos_fact = (await db.execute(select(PresupuestoLoteFact))).scalars().all()
    stock_final_fact = (await db.execute(select(StockFinalFact))).scalars().all()
    tc_fact = (await db.execute(select(TipoCambioFact))).scalars().all()

    fecha_map = {row.fecha_id: row for row in fecha_dim}
    campania_dim_map = {row.campania_id: row for row in campanias_dim}
    establecimiento_dim_map = {row.establecimiento_id: row for row in establecimientos_dim}
    campo_dim_map = {row.campo_id: row for row in campos_dim}
    lote_dim_map = {row.lote_id: row for row in lotes_dim}
    variedad_dim_map = {row.variedad_id: row for row in variedades_dim}
    cliente_dim_map = {row.cliente_id: row for row in clientes_dim}
    mercado_dim_map = {row.mercado_id: row for row in mercados_dim}
    canal_dim_map = {row.canal_id: row for row in canales_dim}
    destino_dim_map = {row.destino_id: row for row in destinos_dim}
    deposito_dim_map = {row.deposito_id: row for row in depositos_dim}
    plaga_dim_map = {row.plaga_id: row for row in plagas_dim}
    enfermedad_dim_map = {row.enfermedad_id: row for row in enfermedades_dim}
    tc_by_fecha = {row.fecha: row for row in tc_fact}

    liquidacion_by_embarque = {row.embarque_id: row for row in liquidaciones_fact}
    contrato_fact_map = {row.contrato_venta_id: row for row in contratos_fact}
    lote_campania_fact_map = {row.lote_campania_id: row for row in lote_campania_fact}
    cuenta_fact_map = {row.cuenta_cobrar_id: row for row in cuentas_fact}
    embarque_fact_map = {row.embarque_id: row for row in embarques_fact}
    cuenta_by_contrato = defaultdict(list)
    for row in cuentas_fact:
        cuenta_by_contrato[row.contrato_venta_id].append(row)
    cobranzas_by_cuenta = defaultdict(list)
    for row in cobranzas_fact:
        cobranzas_by_cuenta[row.cuenta_cobrar_id].append(row)

    # ── Generic ERP-like base ------------------------------------------------
    empresa = Empresa(
        nombre=empresa_dim.nombre,
        cuit=_cuit(30, empresa_dim.empresa_id),
        razon_social=empresa_dim.razon_social,
        tipo="SA",
        activa=True,
    )
    db.add(empresa)
    await db.flush()

    cuentas_corrientes = [
        CuentaCorriente(empresa_id=empresa.id, banco="Banco Macro", nro_cuenta="001-000123/4", tipo="corriente", moneda="ARS"),
        CuentaCorriente(empresa_id=empresa.id, banco="Banco Galicia", nro_cuenta="USD-009876/2", tipo="corriente", moneda="USD"),
    ]
    db.add_all(cuentas_corrientes)
    await db.flush()

    campania_map: dict[int, Campania] = {}
    for row in campanias_dim:
        camp = Campania(
            nombre=row.nombre,
            fecha_inicio=row.fecha_inicio,
            fecha_fin=row.fecha_fin,
            activa=bool(row.activa),
        )
        db.add(camp)
        await db.flush()
        campania_map[row.campania_id] = camp

    cultivo = Cultivo(nombre="Limón", unidad="kg")
    db.add(cultivo)
    await db.flush()

    establecimiento_map: dict[int, Establecimiento] = {}
    for row in establecimientos_dim:
        est = Establecimiento(
            empresa_id=empresa.id,
            nombre=row.nombre,
            ubicacion=row.localidad or row.provincia,
            provincia=row.provincia,
            lat=row.lat,
            lon=row.lon,
            hectareas_totales=row.superficie_total_ha,
        )
        db.add(est)
        await db.flush()
        establecimiento_map[row.establecimiento_id] = est

    cliente_map: dict[int, Cliente] = {}
    for row in clientes_dim:
        cli = Cliente(
            nombre=row.nombre,
            cuit=_cuit(33, row.cliente_id),
            provincia=row.region or row.pais,
            tipo=row.tipo or "cliente",
        )
        db.add(cli)
        await db.flush()
        cliente_map[row.cliente_id] = cli

    proveedores_seed = [
        ("Nutrientes del NOA", "insumos"),
        ("Protección Citrus", "insumos"),
        ("Envases Tucumán", "insumos"),
        ("Combustibles del Norte", "servicios"),
        ("Talleres Yerba Buena", "maquinaria"),
        ("Logística Citrus Cargo", "transporte"),
    ]
    proveedores: list[Proveedor] = []
    for idx, (nombre, tipo) in enumerate(proveedores_seed, start=1):
        proveedor = Proveedor(nombre=nombre, cuit=_cuit(30, 900000000 + idx), tipo=tipo)
        db.add(proveedor)
        await db.flush()
        proveedores.append(proveedor)

    producto_map: dict[str, Producto] = {}
    for destino in destinos_dim:
        producto = Producto(
            nombre=f"Limón {destino.nombre}",
            cultivo_id=cultivo.id,
            unidad="kg",
            precio_referencia=0,
        )
        db.add(producto)
        await db.flush()
        producto_map[destino.codigo] = producto
    first_producto = next(iter(producto_map.values()), None)

    insumos_seed = [
        ("Urea", "fertilizante", "kg", 0.85),
        ("MAP", "fertilizante", "kg", 1.10),
        ("Cobre tribásico", "fungicida", "kg", 4.20),
        ("Aceite mineral", "insecticida", "lt", 2.95),
        ("Gas oil", "combustible", "lt", 1.35),
        ("Caja telescópica", "empaque", "unidad", 0.45),
    ]
    insumo_map: dict[str, Insumo] = {}
    for idx, (nombre, tipo, unidad, precio) in enumerate(insumos_seed, start=1):
        insumo = Insumo(nombre=nombre, tipo=tipo, unidad=unidad, precio_unitario=precio * 1000)
        db.add(insumo)
        await db.flush()
        insumo_map[nombre] = insumo

    maquinaria_seed = [
        ("tractor", "John Deere", "6110J", 2021, "operativo", 3250, 1),
        ("pulverizadora", "Pla", "MAP II 3250", 2020, "operativo", 2810, 1),
        ("autoelevador", "Toyota", "8FG", 2019, "operativo", 4180, 1),
        ("tractor", "New Holland", "T6.180", 2022, "operativo", 1940, 2),
        ("camión interno", "Iveco", "Tector", 2018, "mantenimiento", 5620, 2),
    ]
    maquinarias: list[Maquinaria] = []
    for tipo, marca, modelo, anio, estado, horas, est_idx in maquinaria_seed:
        maq = Maquinaria(
            establecimiento_id=establecimiento_map[establecimientos_dim[est_idx - 1].establecimiento_id].id,
            tipo=tipo,
            marca=marca,
            modelo=modelo,
            anio=anio,
            horas_totales=horas,
            estado=estado,
        )
        db.add(maq)
        await db.flush()
        maquinarias.append(maq)

    old_lote_map: dict[int, Lote] = {}
    for lc in lote_campania_fact:
        lote = lote_dim_map[lc.lote_id]
        camp = campania_dim_map[lc.campania_id]
        old_lote = Lote(
            establecimiento_id=establecimiento_map[lc.establecimiento_id].id,
            nombre=f"{lote.codigo} · {camp.nombre}",
            hectareas=lc.superficie_ha,
            cultivo_id=cultivo.id,
            campania_id=campania_map[lc.campania_id].id,
            estado="cosechado" if lc.estado == "cerrada" else ("sembrado" if lc.estado in {"activa", "en_curso"} else "barbecho"),
            fecha_siembra=camp.fecha_inicio,
            fecha_cosecha=lc.fecha_fin_cosecha_estimada,
            rendimiento_real=round(lc.objetivo_kg_ha / 1000, 2),
            rendimiento_historico=round((lc.objetivo_kg_ha / 1000) * 0.94, 2),
        )
        db.add(old_lote)
        await db.flush()
        old_lote_map[lc.lote_campania_id] = old_lote

    siembras: list[Siembra] = []
    for lc in lote_campania_fact:
        variedad = variedad_dim_map[lc.variedad_id]
        siembra = Siembra(
            lote_id=old_lote_map[lc.lote_campania_id].id,
            campania_id=campania_map[lc.campania_id].id,
            cultivo_id=cultivo.id,
            fecha=campania_dim_map[lc.campania_id].fecha_inicio,
            ha_sembradas=lc.superficie_ha,
            densidad=round(lc.arboles_productivos / max(lc.superficie_ha, 1), 1),
            hibrido=variedad.nombre,
            observaciones=f"Lote perenne de limón en campaña {campania_dim_map[lc.campania_id].nombre}",
        )
        siembras.append(siembra)
    db.add_all(siembras)
    await db.flush()
    siembra_map = {lc.lote_campania_id: siembra for lc, siembra in zip(lote_campania_fact, siembras)}

    rendimiento_fact_map = {row.lote_campania_id: row for row in rendimientos_fact}

    cosechas_v2: list[CosechaV2] = []
    for row in cosechas_fact:
        lc = lote_campania_fact_map[row.lote_campania_id]
        rendimiento = rendimiento_fact_map.get(row.lote_campania_id)
        kg_ha = _safe_float(rendimiento.kg_ha if rendimiento else lc.objetivo_kg_ha)
        ha_cosechadas = round(_safe_float(row.kg_cosechados) / max(kg_ha, 1), 3)
        tc = tc_by_fecha.get(row.fecha_cosecha)
        precio_mercado = 980.0
        tipo_cambio = tc.exportacion if tc else 1000.0
        calidad = "buena" if row.fruta_danada_pct < 6 else ("regular" if row.fruta_danada_pct < 12 else "mala")
        cosechas_v2.append(
            CosechaV2(
                siembra_id=siembra_map[row.lote_campania_id].id,
                fecha=row.fecha_cosecha,
                ha_cosechadas=ha_cosechadas,
                rendimiento_tn_ha=round(kg_ha / 1000, 2),
                humedad=0,
                calidad=calidad,
                precio_mercado=precio_mercado,
                valor_total=round((_safe_float(row.kg_cosechados) / 1000) * precio_mercado * tipo_cambio, 2),
            )
        )
    db.add_all(cosechas_v2)

    labores: list[Labor] = []
    for row in aplicaciones_fact:
        labores.append(
            Labor(
                lote_id=old_lote_map[row.lote_campania_id].id,
                tipo="fumigacion",
                fecha=row.fecha_aplicacion,
                costo_ha=row.costo_ars_ha,
                observacion=row.objetivo,
            )
        )
    for row in riego_fact:
        superficie = old_lote_map[row.lote_campania_id].hectareas
        labores.append(
            Labor(
                lote_id=old_lote_map[row.lote_campania_id].id,
                tipo="riego",
                fecha=row.fecha_riego,
                costo_ha=round(_safe_float(row.costo_ars) / max(superficie, 1), 2),
                observacion=f"{row.m3_aplicados:.0f} m3",
            )
        )
    for row in cosechas_fact:
        superficie = old_lote_map[row.lote_campania_id].hectareas
        labores.append(
            Labor(
                lote_id=old_lote_map[row.lote_campania_id].id,
                tipo="cosecha",
                fecha=row.fecha_cosecha,
                costo_ha=round(_safe_float(row.costo_cosecha_ars) / max(superficie, 1), 2),
                observacion=f"{row.kg_cosechados:.0f} kg cosechados",
            )
        )
    db.add_all(labores)

    movimiento_insumos: list[MovimientoInsumo] = []
    for row in fert_fact:
        movimiento_insumos.append(
            MovimientoInsumo(
                establecimiento_id=old_lote_map[row.lote_campania_id].establecimiento_id,
                insumo_id=insumo_map["Urea"].id if row.nutriente.lower().startswith("n") else insumo_map["MAP"].id,
                tipo="egreso",
                cantidad=row.kg_aplicados,
                fecha=row.fecha_fertirriego,
                costo_total=row.costo_ars,
                lote_id=old_lote_map[row.lote_campania_id].id,
            )
        )
    for row in aplicaciones_fact:
        movimiento_insumos.append(
            MovimientoInsumo(
                establecimiento_id=old_lote_map[row.lote_campania_id].establecimiento_id,
                insumo_id=insumo_map["Cobre tribásico"].id if "cobre" in row.producto.lower() else insumo_map["Aceite mineral"].id,
                tipo="egreso",
                cantidad=max(row.dosis_l_ha * old_lote_map[row.lote_campania_id].hectareas, 1),
                fecha=row.fecha_aplicacion,
                costo_total=round(row.costo_ars_ha * old_lote_map[row.lote_campania_id].hectareas, 2),
                lote_id=old_lote_map[row.lote_campania_id].id,
            )
        )
    monthly_purchase_dates = sorted({row.fecha for row in mano_obra_fact})[::8]
    for idx, purchase_date in enumerate(monthly_purchase_dates, start=1):
        movimiento_insumos.append(
            MovimientoInsumo(
                establecimiento_id=establecimiento_map[establecimientos_dim[0].establecimiento_id].id,
                insumo_id=insumo_map["Caja telescópica"].id,
                tipo="ingreso",
                cantidad=8000 + idx * 250,
                fecha=purchase_date,
                costo_total=(8000 + idx * 250) * insumo_map["Caja telescópica"].precio_unitario,
                lote_id=None,
            )
        )
    db.add_all(movimiento_insumos)

    contratos_v2: list[ContratoV2] = []
    contrato_v2_map: dict[int, ContratoV2] = {}
    for idx, row in enumerate(contratos_fact, start=1):
        canal = canal_dim_map[row.canal_id]
        contrato = ContratoV2(
            empresa_id=empresa.id,
            campania_id=campania_map[row.campania_id].id,
            cultivo_id=cultivo.id,
            cliente_id=cliente_map[row.cliente_id].id,
            tipo="forward" if canal.codigo == "EXP" else ("disponible" if canal.codigo == "LOC" else "industria"),
            cantidad_tn=round(row.kg_contratados / 1000, 2),
            precio_usd=row.precio_objetivo_usd_tn,
            precio_ars=None,
            fecha_firma=row.fecha_contrato,
            fecha_entrega=campania_dim_map[row.campania_id].fecha_fin,
            estado=row.estado,
        )
        db.add(contrato)
        await db.flush()
        contratos_v2.append(contrato)
        contrato_v2_map[row.contrato_venta_id] = contrato

    ventas_v2: list[VentaV2] = []
    remitos_campo: list[RemitoCampo] = []
    for embarque in embarques_fact:
        contrato = contrato_v2_map[embarque.contrato_venta_id]
        liqui = liquidacion_by_embarque.get(embarque.embarque_id)
        tc = tc_by_fecha.get(embarque.fecha_embarque)
        precio_usd = embarque.precio_realizado_usd_tn
        tipo_cambio = liqui.tipo_cambio_aplicado if liqui else (tc.exportacion if tc else 1000.0)
        total_ars = liqui.importe_neto_ars if liqui else round((embarque.kg_embarcados / 1000) * precio_usd * tipo_cambio, 2)
        venta = VentaV2(
            empresa_id=empresa.id,
            campania_id=contrato.campania_id,
            cultivo_id=cultivo.id,
            cliente_id=contrato.cliente_id,
            contrato_id=contrato.id,
            fecha=embarque.fecha_embarque,
            cantidad_tn=round(embarque.kg_embarcados / 1000, 2),
            precio_ars_tn=round(total_ars / max((embarque.kg_embarcados / 1000), 0.001), 2),
            precio_usd_tn=precio_usd,
            importe_total_ars=total_ars,
            tipo_cambio=tipo_cambio,
            condicion_pago="credito",
        )
        db.add(venta)
        await db.flush()
        ventas_v2.append(venta)
        mercado = mercado_dim_map[embarque.mercado_id]
        remitos_campo.append(
            RemitoCampo(
                venta_id=venta.id,
                fecha=embarque.fecha_embarque,
                cantidad_tn=round(embarque.kg_embarcados / 1000, 2),
                chofer=f"Chofer {embarque.embarque_id % 9 + 1}",
                patente=f"AE{embarque.embarque_id % 900:03d}TX",
                destino=mercado.nombre,
            )
        )
    db.add_all(remitos_campo)

    latest_stock_date = max((row.fecha for row in stock_final_fact), default=None)
    stocks_map = defaultdict(lambda: {"volumen_disponible": 0.0, "volumen_vendido": 0.0, "volumen_comprometido": 0.0})
    for row in stock_final_fact:
        if row.fecha != latest_stock_date:
            continue
        deposito = deposito_dim_map[row.deposito_id]
        product = producto_map[destino_dim_map[row.destino_id].codigo]
        key = (establecimiento_map[deposito.establecimiento_id].id, product.id)
        stocks_map[key]["volumen_disponible"] += row.kg_stock / 1000
    for contrato in contratos_v2:
        key = None
        for est in establecimiento_map.values():
            key = (est.id, next(iter(producto_map.values())).id)
            break
        if key:
            stocks_map[key]["volumen_comprometido"] += contrato.cantidad_tn
    stock_rows = [
        Stock(
            establecimiento_id=est_id,
            producto_id=prod_id,
            volumen_disponible=round(values["volumen_disponible"], 2),
            volumen_vendido=round(values["volumen_vendido"], 2),
            volumen_comprometido=round(values["volumen_comprometido"], 2),
        )
        for (est_id, prod_id), values in stocks_map.items()
    ]
    db.add_all(stock_rows)

    flujo_rows: list[FlujoCajaV2] = []
    for row in cobranzas_fact:
        cuenta = cuenta_fact_map.get(row.cuenta_cobrar_id)
        contrato_fact = contrato_fact_map.get(cuenta.contrato_venta_id) if cuenta else None
        campania_id = campania_map[contrato_fact.campania_id].id if contrato_fact else None
        tc = tc_by_fecha.get(row.fecha_cobranza)
        flujo_rows.append(
            FlujoCajaV2(
                empresa_id=empresa.id,
                fecha=row.fecha_cobranza,
                tipo="ingreso",
                categoria="cobranzas",
                subcategoria="clientes",
                importe_ars=row.monto_cobrado_ars,
                importe_usd=round(row.monto_cobrado_ars / max((tc.exportacion if tc else 1000), 1), 2),
                tipo_cambio=tc.exportacion if tc else None,
                descripcion="Cobranza clientes limón",
                referencia_tipo="cobranza",
                referencia_id=row.cobranza_id,
                cuenta_id=cuentas_corrientes[0].id,
                campania_id=campania_id,
            )
        )
    for row in costos_directos_fact:
        flujo_rows.append(
            FlujoCajaV2(
                empresa_id=empresa.id,
                fecha=row.fecha,
                tipo="egreso",
                categoria=row.categoria,
                subcategoria=row.subcategoria,
                importe_ars=row.monto_ars,
                descripcion=f"Costo directo {row.categoria}",
                referencia_tipo="costo_directo",
                referencia_id=row.costo_directo_id,
                cuenta_id=cuentas_corrientes[0].id,
                campania_id=campania_map[lote_campania_fact_map[row.lote_campania_id].campania_id].id,
            )
        )
    for row in costos_indirectos_fact:
        flujo_rows.append(
            FlujoCajaV2(
                empresa_id=empresa.id,
                fecha=row.fecha,
                tipo="egreso",
                categoria=row.categoria,
                subcategoria="indirecto",
                importe_ars=row.monto_ars,
                descripcion=f"Costo indirecto {row.categoria}",
                referencia_tipo="costo_indirecto",
                referencia_id=row.costo_indirecto_id,
                cuenta_id=cuentas_corrientes[0].id,
                campania_id=campania_map[row.campania_id].id,
            )
        )
    db.add_all(flujo_rows)

    presupuesto_map = defaultdict(lambda: {"presupuestado": 0.0, "ejecutado": 0.0})
    for row in presupuestos_fact:
        campania_id = lote_campania_fact_map[row.lote_campania_id].campania_id
        presupuesto_map[campania_id]["presupuestado"] += row.margen_plan_ars
    for row in costos_directos_fact:
        campania_id = lote_campania_fact_map[row.lote_campania_id].campania_id
        presupuesto_map[campania_id]["ejecutado"] += row.monto_ars
    for row in costos_indirectos_fact:
        presupuesto_map[row.campania_id]["ejecutado"] += row.monto_ars
    db.add_all(
        [
            Presupuesto(
                empresa_id=empresa.id,
                campania_id=campania_map[campania_id].id,
                categoria="Campaña limón",
                importe_presupuestado=round(values["presupuestado"], 2),
                importe_ejecutado=round(values["ejecutado"], 2),
                fecha_creacion=campania_dim_map[campania_id].fecha_inicio,
            )
            for campania_id, values in presupuesto_map.items()
        ]
    )

    maintenance_rows = []
    for idx, maq in enumerate(maquinarias, start=1):
        maintenance_rows.append(
            Mantenimiento(
                maquinaria_id=maq.id,
                tipo="preventivo" if idx % 2 else "correctivo",
                fecha=date(2026, max(1, idx), min(20, 3 + idx)),
                descripcion=f"Service programado {maq.tipo}",
                costo=450000 + idx * 85000,
                horas_maquina=maq.horas_totales,
                proximo_service_hs=maq.horas_totales + 250,
            )
        )
    db.add_all(maintenance_rows)

    # ── Rich ERP / Synagro-like layer ---------------------------------------
    moneda_ars = Moneda(codigo="ARS", nombre="Peso Argentino", simbolo="$", es_base=True)
    moneda_usd = Moneda(codigo="USD", nombre="Dólar Estadounidense", simbolo="USD", es_base=False)
    db.add_all([moneda_ars, moneda_usd])
    await db.flush()

    unidades = [
        UnidadMedida(codigo="kg", nombre="Kilogramo", categoria="peso", factor_base=1),
        UnidadMedida(codigo="tn", nombre="Tonelada", categoria="peso", factor_base=1000),
        UnidadMedida(codigo="ha", nombre="Hectárea", categoria="superficie", factor_base=1),
        UnidadMedida(codigo="m3", nombre="Metro cúbico", categoria="volumen", factor_base=1),
        UnidadMedida(codigo="mm", nombre="Milímetro", categoria="clima", factor_base=1),
        UnidadMedida(codigo="caja", nombre="Caja", categoria="empaque", factor_base=1),
        UnidadMedida(codigo="hora", nombre="Hora", categoria="tiempo", factor_base=1),
        UnidadMedida(codigo="lt", nombre="Litro", categoria="volumen", factor_base=1),
    ]
    db.add_all(unidades)
    await db.flush()
    unidad_map = {u.codigo: u for u in unidades}

    unidad_negocio = UnidadNegocio(
        empresa_id=empresa.id,
        codigo="LIM",
        nombre="Negocio Limón",
        descripcion="Producción, empaque y comercialización de limón",
        activa=True,
    )
    db.add(unidad_negocio)
    await db.flush()

    centros_costos = [
        CentroCosto(empresa_id=empresa.id, unidad_negocio_id=unidad_negocio.id, codigo="CAMPO", nombre="Campo", tipo="operativo", activo=True),
        CentroCosto(empresa_id=empresa.id, unidad_negocio_id=unidad_negocio.id, codigo="PACK", nombre="Packhouse", tipo="operativo", activo=True),
        CentroCosto(empresa_id=empresa.id, unidad_negocio_id=unidad_negocio.id, codigo="COM", nombre="Comercial", tipo="comercial", activo=True),
        CentroCosto(empresa_id=empresa.id, unidad_negocio_id=unidad_negocio.id, codigo="ADM", nombre="Administración", tipo="administrativo", activo=True),
        CentroCosto(empresa_id=empresa.id, unidad_negocio_id=unidad_negocio.id, codigo="RIE", nombre="Riego", tipo="operativo", activo=True),
    ]
    db.add_all(centros_costos)
    await db.flush()
    cc_map = {row.codigo: row for row in centros_costos}

    erp_campos_map: dict[int, ERPCampo] = {}
    for row in campos_dim:
        erp_campo = ERPCampo(
            empresa_id=empresa.id,
            unidad_negocio_id=unidad_negocio.id,
            establecimiento_id=establecimiento_map[row.establecimiento_id].id,
            codigo=row.codigo,
            nombre=row.nombre,
            superficie_total_ha=row.superficie_ha,
            arrendado=False,
            observaciones=row.tipo_suelo,
        )
        db.add(erp_campo)
        await db.flush()
        erp_campos_map[row.campo_id] = erp_campo

    erp_var_map: dict[int, ERPVariedad] = {}
    for row in variedades_dim:
        erp_var = ERPVariedad(
            cultivo_id=cultivo.id,
            nombre=row.nombre,
            marca=row.grupo,
            ciclo=row.epoca_principal,
            tecnologia=row.destino_preferido,
            activo=bool(row.activa),
        )
        db.add(erp_var)
        await db.flush()
        erp_var_map[row.variedad_id] = erp_var

    erp_deposito_map: dict[int, Deposito] = {}
    for row in depositos_dim:
        erp_dep = Deposito(
            empresa_id=empresa.id,
            establecimiento_id=establecimiento_map[row.establecimiento_id].id,
            codigo=row.codigo,
            nombre=row.nombre,
            tipo=row.tipo,
            capacidad=row.capacidad_kg,
            unidad_capacidad="kg",
            activo=bool(row.activo),
        )
        db.add(erp_dep)
        await db.flush()
        erp_deposito_map[row.deposito_id] = erp_dep

    empleados = [
        Empleado(empresa_id=empresa.id, centro_costo_id=cc_map["ADM"].id, establecimiento_id=None, legajo="EMP-001", nombre="María Correa", rol="Gerencia General", tipo="propio", activo=True),
        Empleado(empresa_id=empresa.id, centro_costo_id=cc_map["CAMPO"].id, establecimiento_id=establecimiento_map[establecimientos_dim[0].establecimiento_id].id, legajo="EMP-002", nombre="Luis Herrera", rol="Jefe de Campo", tipo="propio", activo=True),
        Empleado(empresa_id=empresa.id, centro_costo_id=cc_map["PACK"].id, establecimiento_id=establecimiento_map[establecimientos_dim[0].establecimiento_id].id, legajo="EMP-003", nombre="Sofía Ferreyra", rol="Jefa de Packhouse", tipo="propio", activo=True),
        Empleado(empresa_id=empresa.id, centro_costo_id=cc_map["COM"].id, establecimiento_id=None, legajo="EMP-004", nombre="Tomás Molina", rol="Responsable Comercial", tipo="propio", activo=True),
        Empleado(empresa_id=empresa.id, centro_costo_id=cc_map["RIE"].id, establecimiento_id=establecimiento_map[establecimientos_dim[1].establecimiento_id].id, legajo="EMP-005", nombre="Nicolás Paz", rol="Responsable de Riego", tipo="propio", activo=True),
    ]
    db.add_all(empleados)
    await db.flush()

    contratistas = [
        Contratista(empresa_id=empresa.id, proveedor_id=proveedores[5].id, nombre="Cuadrillas del Pedemonte", especialidad="Cosecha", activo=True),
        Contratista(empresa_id=empresa.id, proveedor_id=proveedores[1].id, nombre="Aplicaciones NOA", especialidad="Pulverización", activo=True),
        Contratista(empresa_id=empresa.id, proveedor_id=proveedores[4].id, nombre="Riego & Bombeo SRL", especialidad="Riego", activo=True),
    ]
    db.add_all(contratistas)
    await db.flush()

    implementos = [
        Implemento(empresa_id=empresa.id, establecimiento_id=establecimiento_map[establecimientos_dim[0].establecimiento_id].id, maquinaria_id=maquinarias[0].id, tipo="Acoplado bins", marca="Mainero", modelo="Bins 12", ancho_trabajo_m=2.5, activo=True),
        Implemento(empresa_id=empresa.id, establecimiento_id=establecimiento_map[establecimientos_dim[1].establecimiento_id].id, maquinaria_id=maquinarias[1].id, tipo="Turbo atomizador", marca="Metalfor", modelo="Citrus 2000", ancho_trabajo_m=8.0, activo=True),
    ]
    db.add_all(implementos)
    await db.flush()

    categorias = [
        CategoriaProducto(codigo="FRUTA", nombre="Fruta fresca", tipo="producto"),
        CategoriaProducto(codigo="INS", nombre="Insumos", tipo="insumo"),
        CategoriaProducto(codigo="EMP", nombre="Material de empaque", tipo="insumo"),
        CategoriaProducto(codigo="COMB", nombre="Combustibles", tipo="insumo"),
    ]
    db.add_all(categorias)
    await db.flush()

    labor_tipos = [
        LaborTipo(codigo="COSECHA", nombre="Cosecha", categoria="campo", requiere_equipo=False, requiere_producto=False, requiere_dosis=False),
        LaborTipo(codigo="RIEGO", nombre="Riego", categoria="campo", requiere_equipo=True, requiere_producto=False, requiere_dosis=False),
        LaborTipo(codigo="FERTI", nombre="Fertirriego", categoria="campo", requiere_equipo=True, requiere_producto=True, requiere_dosis=True),
        LaborTipo(codigo="PULV", nombre="Aplicación fitosanitaria", categoria="campo", requiere_equipo=True, requiere_producto=True, requiere_dosis=True),
        LaborTipo(codigo="PACK", nombre="Proceso packhouse", categoria="proceso", requiere_equipo=True, requiere_producto=False, requiere_dosis=False),
    ]
    db.add_all(labor_tipos)
    await db.flush()
    labor_tipo_map = {row.codigo: row for row in labor_tipos}

    ambiente_rows = []
    erp_lote_campania_map: dict[int, ERPLoteCampania] = {}
    for lc in lote_campania_fact:
        lote = lote_dim_map[lc.lote_id]
        erp_lc = ERPLoteCampania(
            empresa_id=empresa.id,
            establecimiento_id=establecimiento_map[lc.establecimiento_id].id,
            campo_id=erp_campos_map[lote.campo_id].id,
            lote_id=old_lote_map[lc.lote_campania_id].id,
            campania_id=campania_map[lc.campania_id].id,
            cultivo_id=cultivo.id,
            variedad_id=erp_var_map[lc.variedad_id].id,
            centro_costo_id=cc_map["CAMPO"].id,
            superficie_ha=lc.superficie_ha,
            modalidad="propio",
            estado="cerrado" if lc.estado == "cerrada" else "activo",
            fecha_inicio=campania_dim_map[lc.campania_id].fecha_inicio,
            fecha_fin=campania_dim_map[lc.campania_id].fecha_fin,
            fecha_siembra_plan=campania_dim_map[lc.campania_id].fecha_inicio,
            fecha_siembra_real=campania_dim_map[lc.campania_id].fecha_inicio,
            fecha_cosecha_plan=lc.fecha_fin_cosecha_estimada,
            fecha_cosecha_real=lc.fecha_fin_cosecha_estimada if lc.estado == "cerrada" else None,
            objetivo_rinde_tn_ha=round(lc.objetivo_kg_ha / 1000, 2),
            objetivo_margen_ha=lc.objetivo_margen_ha,
            responsable_id=empleados[1].id,
            observaciones=f"Condición hídrica {lc.condicion_hidrica}",
        )
        db.add(erp_lc)
        await db.flush()
        erp_lote_campania_map[lc.lote_campania_id] = erp_lc
        ambiente_rows.append(Ambiente(lote_id=old_lote_map[lc.lote_campania_id].id, codigo="A", nombre="Ambiente alto", superficie_ha=round(lc.superficie_ha * 0.55, 2), potencial_productivo="alto"))
        ambiente_rows.append(Ambiente(lote_id=old_lote_map[lc.lote_campania_id].id, codigo="B", nombre="Ambiente medio", superficie_ha=round(lc.superficie_ha * 0.45, 2), potencial_productivo="medio"))
    db.add_all(ambiente_rows)

    erp_rendimientos = []
    for row in rendimientos_fact:
        lc = erp_lote_campania_map[row.lote_campania_id]
        lotec_src = lote_campania_fact_map[row.lote_campania_id]
        camp_dim = campania_dim_map[lotec_src.campania_id]
        erp_rendimientos.append(
            ERPRendimientoLote(
                lote_campania_id=lc.id,
                cosecha_id=None,
                fecha_cosecha=min(camp_dim.fecha_fin, date.today()),
                superficie_cosechada_ha=lotec_src.superficie_ha,
                produccion_tn=round(row.kg_totales / 1000, 2),
                rendimiento_tn_ha=round(row.kg_ha / 1000, 2),
                humedad_pct=0,
                merma_pct=row.fruta_descarte_pct,
                calidad="exportable" if row.fruta_exportable_pct >= 55 else "mixta",
                precio_estimado_tn=0,
                ingreso_estimado=0,
            )
        )
    db.add_all(erp_rendimientos)

    monitoreos = []
    for row in scouting_fact:
        monitoreos.append(
            MonitoreoPlaga(
                lote_campania_id=erp_lote_campania_map[row.lote_campania_id].id,
                ambiente_id=None,
                fecha=row.fecha_evento,
                tipo="plaga" if row.plaga_id else "enfermedad",
                organismo=(plaga_dim_map[row.plaga_id].nombre if row.plaga_id else enfermedad_dim_map[row.enfermedad_id].nombre),
                severidad=row.severidad,
                incidencia_pct=row.incidencia_pct,
                umbral=5.0 if row.alerta else 10.0,
                accion_recomendada=row.recomendacion,
                monitoreador_id=empleados[1].id,
            )
        )
    db.add_all(monitoreos)

    consumos = []
    for row in fert_fact:
        consumos.append(
            ConsumoInsumo(
                empresa_id=empresa.id,
                establecimiento_id=old_lote_map[row.lote_campania_id].establecimiento_id,
                lote_campania_id=erp_lote_campania_map[row.lote_campania_id].id,
                insumo_id=insumo_map["Urea"].id if row.nutriente.lower().startswith("n") else insumo_map["MAP"].id,
                movimiento_stock_id=None,
                fecha_consumo=row.fecha_fertirriego,
                labor_origen="fertirriego",
                cantidad=row.kg_aplicados,
                unidad_medida_id=unidad_map["kg"].id,
                costo_total=row.costo_ars,
                costo_ha=round(row.costo_ars / max(old_lote_map[row.lote_campania_id].hectareas, 1), 2),
            )
        )
    for row in aplicaciones_fact:
        superficie = old_lote_map[row.lote_campania_id].hectareas
        consumos.append(
            ConsumoInsumo(
                empresa_id=empresa.id,
                establecimiento_id=old_lote_map[row.lote_campania_id].establecimiento_id,
                lote_campania_id=erp_lote_campania_map[row.lote_campania_id].id,
                insumo_id=insumo_map["Cobre tribásico"].id if "cobre" in row.producto.lower() else insumo_map["Aceite mineral"].id,
                movimiento_stock_id=None,
                fecha_consumo=row.fecha_aplicacion,
                labor_origen="fitosanitario",
                cantidad=max(row.dosis_l_ha * superficie, 1),
                unidad_medida_id=unidad_map["lt"].id,
                costo_total=round(row.costo_ars_ha * superficie, 2),
                costo_ha=row.costo_ars_ha,
            )
        )
    db.add_all(consumos)

    partes_trabajo = []
    for row in cosechas_fact[:1200]:
        partes_trabajo.append(
            ParteTrabajo(
                empresa_id=empresa.id,
                establecimiento_id=old_lote_map[row.lote_campania_id].establecimiento_id,
                lote_campania_id=erp_lote_campania_map[row.lote_campania_id].id,
                fecha_trabajo=row.fecha_cosecha,
                labor_tipo_id=labor_tipo_map["COSECHA"].id,
                maquinaria_id=None,
                implemento_id=None,
                operador_id=empleados[1].id,
                contratista_id=contratistas[0].id,
                horas_operativas=round(max(row.jornales * 0.85, 4), 2),
                horas_improductivas=round(max(row.jornales * 0.12, 0.5), 2),
                superficie_trabajada_ha=round(row.kg_cosechados / max((rendimiento_fact_map[row.lote_campania_id].kg_ha if row.lote_campania_id in rendimiento_fact_map else 25000), 1), 3),
                combustible_litros=0,
                estado="cerrado",
                observaciones=f"{row.cuadrillas} cuadrillas",
            )
        )
    for row in aplicaciones_fact:
        partes_trabajo.append(
            ParteTrabajo(
                empresa_id=empresa.id,
                establecimiento_id=old_lote_map[row.lote_campania_id].establecimiento_id,
                lote_campania_id=erp_lote_campania_map[row.lote_campania_id].id,
                fecha_trabajo=row.fecha_aplicacion,
                labor_tipo_id=labor_tipo_map["PULV"].id,
                maquinaria_id=maquinarias[1].id,
                implemento_id=implementos[1].id,
                operador_id=empleados[1].id,
                contratista_id=contratistas[1].id,
                horas_operativas=5.5,
                horas_improductivas=0.8,
                superficie_trabajada_ha=old_lote_map[row.lote_campania_id].hectareas,
                combustible_litros=35,
                estado="cerrado",
                observaciones=row.objetivo,
            )
        )
    for row in riego_fact:
        partes_trabajo.append(
            ParteTrabajo(
                empresa_id=empresa.id,
                establecimiento_id=old_lote_map[row.lote_campania_id].establecimiento_id,
                lote_campania_id=erp_lote_campania_map[row.lote_campania_id].id,
                fecha_trabajo=row.fecha_riego,
                labor_tipo_id=labor_tipo_map["RIEGO"].id,
                maquinaria_id=maquinarias[3].id,
                implemento_id=None,
                operador_id=empleados[4].id,
                contratista_id=contratistas[2].id,
                horas_operativas=row.horas_riego,
                horas_improductivas=round(row.horas_riego * 0.08, 2),
                superficie_trabajada_ha=old_lote_map[row.lote_campania_id].hectareas,
                combustible_litros=18,
                estado="cerrado",
                observaciones=f"{row.m3_aplicados:.0f} m3",
            )
        )
    db.add_all(partes_trabajo)

    latest_stock_date = max((row.fecha for row in stock_final_fact), default=None)
    stock_actual_rows = []
    for row in stock_final_fact:
        if row.fecha != latest_stock_date:
            continue
        dep = deposito_dim_map[row.deposito_id]
        dest = destino_dim_map[row.destino_id]
        stock_actual_rows.append(
            StockActual(
                empresa_id=empresa.id,
                establecimiento_id=establecimiento_map[dep.establecimiento_id].id,
                deposito_id=erp_deposito_map[row.deposito_id].id,
                producto_id=producto_map[dest.codigo].id,
                insumo_id=None,
                fecha_corte=row.fecha,
                lote=dest.nombre,
                cantidad=row.kg_stock,
                reservado=0,
                disponible=row.kg_stock,
                costo_unitario=round(row.valor_ars / max(row.kg_stock, 1), 2),
                valor_total=row.valor_ars,
            )
        )
    db.add_all(stock_actual_rows)

    movimiento_stock_rows = []
    for row in stock_final_fact:
        dep = deposito_dim_map[row.deposito_id]
        dest = destino_dim_map[row.destino_id]
        movimiento_stock_rows.append(
            MovimientoStock(
                empresa_id=empresa.id,
                establecimiento_id=establecimiento_map[dep.establecimiento_id].id,
                deposito_id=erp_deposito_map[row.deposito_id].id,
                producto_id=producto_map[dest.codigo].id,
                insumo_id=None,
                lote_campania_id=None,
                fecha_movimiento=row.fecha,
                tipo_movimiento="ajuste_corte",
                origen="stock_final_fact",
                referencia=f"STK-{row.stock_final_id}",
                cantidad=row.kg_stock,
                unidad_medida_id=unidad_map["kg"].id,
                costo_unitario=round(row.valor_ars / max(row.kg_stock, 1), 2),
                monto_total=row.valor_ars,
                observaciones=dest.nombre,
            )
        )
    db.add_all(movimiento_stock_rows)

    erp_contrato_map: dict[int, ERPContratoVenta] = {}
    erp_contratos_rows = []
    for idx, row in enumerate(contratos_fact, start=1):
        canal = canal_dim_map[row.canal_id]
        destino_producto = "FRESCO_EXPORT" if canal.codigo == "EXP" else ("FRESCO_LOCAL" if canal.codigo == "LOC" else "INDUSTRIA")
        producto = producto_map.get(destino_producto, first_producto)
        contrato = ERPContratoVenta(
            empresa_id=empresa.id,
            cliente_id=cliente_map[row.cliente_id].id,
            campania_id=campania_map[row.campania_id].id,
            cultivo_id=cultivo.id,
            producto_id=producto.id,
            numero=f"CTV-{idx:05d}",
            fecha_contrato=row.fecha_contrato,
            fecha_entrega_desde=row.fecha_contrato,
            fecha_entrega_hasta=min(campania_dim_map[row.campania_id].fecha_fin, row.fecha_contrato + timedelta(days=120)),
            volumen_tn=round(row.kg_contratados / 1000, 2),
            precio_tn=row.precio_objetivo_usd_tn,
            volumen_fijado_tn=round(row.kg_entregados / 1000 * 0.82, 2),
            volumen_entregado_tn=round(row.kg_entregados / 1000, 2),
            estado=row.estado,
            condicion=f"{row.condicion_pago_dias} días",
        )
        erp_contratos_rows.append(contrato)
        erp_contrato_map[row.contrato_venta_id] = contrato
    db.add_all(erp_contratos_rows)
    await db.flush()

    entrega_map: dict[int, Entrega] = {}
    entrega_rows = []
    for embarque in embarques_fact:
        entrega = Entrega(
            contrato_venta_id=erp_contrato_map[embarque.contrato_venta_id].id,
            remito_id=None,
            deposito_id=None,
            fecha_programada=embarque.fecha_embarque,
            fecha_entrega=embarque.fecha_embarque,
            volumen_tn=round(embarque.kg_embarcados / 1000, 2),
            calidad="exportación" if embarque.canal_id == canales_dim[0].canal_id else "mercado",
            estado="entregado",
        )
        entrega_rows.append(entrega)
        entrega_map[embarque.embarque_id] = entrega
    db.add_all(entrega_rows)
    await db.flush()

    fijaciones = []
    for embarque in embarques_fact[: len(embarques_fact) // 2]:
        fijaciones.append(
            Fijacion(
                contrato_venta_id=erp_contrato_map[embarque.contrato_venta_id].id,
                fecha_fijacion=embarque.fecha_embarque,
                volumen_tn=round(embarque.kg_embarcados / 1000, 2),
                precio_tn=embarque.precio_realizado_usd_tn,
                mercado_referencia=mercado_dim_map[embarque.mercado_id].nombre,
                observaciones="Fijación derivada de embarque realizado",
            )
        )
    db.add_all(fijaciones)

    erp_liq_map: dict[int, ERPLiquidacion] = {}
    erp_liq_rows = []
    for idx, row in enumerate(liquidaciones_fact, start=1):
        embarque = embarque_fact_map[row.embarque_id]
        liq = ERPLiquidacion(
            contrato_venta_id=erp_contrato_map[embarque.contrato_venta_id].id,
            entrega_id=entrega_map[embarque.embarque_id].id,
            cliente_id=cliente_map[embarque.cliente_id].id,
            numero=f"LIQ-{idx:05d}",
            fecha_liquidacion=row.fecha_liquidacion,
            volumen_tn=round(embarque.kg_embarcados / 1000, 2),
            precio_tn=embarque.precio_realizado_usd_tn,
            bonificaciones=0,
            gastos_comerciales=row.descuentos_usd,
            importe_neto=row.importe_neto_ars,
            moneda_id=moneda_ars.id,
        )
        erp_liq_rows.append(liq)
        erp_liq_map[row.liquidacion_id] = liq
    db.add_all(erp_liq_rows)
    await db.flush()

    erp_pres_camp_map = defaultdict(lambda: {"ingreso_plan": 0.0, "costo_d_plan": 0.0, "costo_i_plan": 0.0, "margen_plan": 0.0})
    for row in presupuestos_fact:
        campania_id = lote_campania_fact_map[row.lote_campania_id].campania_id
        acc = erp_pres_camp_map[campania_id]
        acc["ingreso_plan"] += row.ingreso_plan_ars
        acc["costo_d_plan"] += row.costo_directo_plan_ars
        acc["costo_i_plan"] += row.costo_indirecto_plan_ars
        acc["margen_plan"] += row.margen_plan_ars

    db.add_all(
        [
            PresupuestoCampania(
                empresa_id=empresa.id,
                campania_id=campania_map[campania_id].id,
                moneda_id=moneda_ars.id,
                ingreso_plan=round(values["ingreso_plan"], 2),
                costo_directo_plan=round(values["costo_d_plan"], 2),
                costo_indirecto_plan=round(values["costo_i_plan"], 2),
                margen_plan=round(values["margen_plan"], 2),
                capital_trabajo_objetivo=round(values["costo_d_plan"] * 0.22, 2),
            )
            for campania_id, values in erp_pres_camp_map.items()
        ]
    )

    erp_costos_d = []
    for row in costos_directos_fact:
        erp_costos_d.append(
            ERPCostoDirecto(
                empresa_id=empresa.id,
                lote_campania_id=erp_lote_campania_map[row.lote_campania_id].id,
                centro_costo_id=cc_map["CAMPO"].id,
                fecha_costo=row.fecha,
                categoria=row.categoria,
                subcategoria=row.subcategoria,
                concepto=f"{row.categoria} / {row.subcategoria}",
                monto=row.monto_ars,
                moneda_id=moneda_ars.id,
                referencia=f"CD-{row.costo_directo_id}",
                origen_tipo="fact",
                origen_id=row.costo_directo_id,
            )
        )
    db.add_all(erp_costos_d)

    erp_costos_i = []
    for row in costos_indirectos_fact:
        erp_costos_i.append(
            ERPCostoIndirecto(
                empresa_id=empresa.id,
                establecimiento_id=establecimiento_map[row.establecimiento_id].id,
                centro_costo_id=cc_map["ADM"].id if row.categoria.lower().startswith("admin") else cc_map["PACK"].id,
                fecha_costo=row.fecha,
                categoria=row.categoria,
                concepto=f"Costo indirecto {row.categoria}",
                monto=row.monto_ars,
                moneda_id=moneda_ars.id,
            )
        )
    db.add_all(erp_costos_i)
    await db.flush()

    surface_by_campaign = defaultdict(float)
    lcf_by_campaign = defaultdict(list)
    for lc in lote_campania_fact:
        surface_by_campaign[lc.campania_id] += lc.superficie_ha
        lcf_by_campaign[lc.campania_id].append(lc)

    asignaciones = []
    for row, erp_row in zip(costos_indirectos_fact, erp_costos_i):
        lc_items = lcf_by_campaign[row.campania_id]
        total_surface = max(surface_by_campaign[row.campania_id], 1)
        for lc in lc_items:
            share = lc.superficie_ha / total_surface
            asignaciones.append(
                AsignacionCosto(
                    costo_indirecto_id=erp_row.id,
                    lote_campania_id=erp_lote_campania_map[lc.lote_campania_id].id,
                    criterio="ha",
                    base_valor=lc.superficie_ha,
                    monto_asignado=round(row.monto_ars * share, 2),
                )
            )
    db.add_all(asignaciones)

    erp_cxc_map = {}
    embarque_ids_by_contract = defaultdict(list)
    for embarque in embarques_fact:
        embarque_ids_by_contract[embarque.contrato_venta_id].append(embarque.embarque_id)
    liquidacion_fact_by_contract = {}
    for liq in liquidaciones_fact:
        embarque = embarque_fact_map.get(liq.embarque_id)
        if embarque and embarque.contrato_venta_id not in liquidacion_fact_by_contract:
            liquidacion_fact_by_contract[embarque.contrato_venta_id] = liq
    erp_cxc_rows = []
    for idx, row in enumerate(cuentas_fact, start=1):
        liquidacion_fact = liquidacion_fact_by_contract.get(row.contrato_venta_id)
        liquidacion = erp_liq_map.get(liquidacion_fact.liquidacion_id) if liquidacion_fact else None
        cxc = ERPCuentaCobrar(
            empresa_id=empresa.id,
            cliente_id=cliente_map[row.cliente_id].id,
            liquidacion_id=liquidacion.id if liquidacion else None,
            numero_comprobante=f"CXC-{idx:06d}",
            fecha_emision=row.fecha_emision,
            fecha_vencimiento=row.fecha_vencimiento,
            monto_original=row.monto_original_ars,
            saldo=row.saldo_abierto_ars,
            moneda_id=moneda_ars.id,
            estado=row.estado,
        )
        erp_cxc_rows.append(cxc)
        erp_cxc_map[row.cuenta_cobrar_id] = cxc
    db.add_all(erp_cxc_rows)
    await db.flush()

    erp_cobranzas = []
    for row in cobranzas_fact:
        erp_cobranzas.append(
            ERPCobranza(
                empresa_id=empresa.id,
                cuenta_cobrar_id=erp_cxc_map[row.cuenta_cobrar_id].id,
                fecha_cobranza=row.fecha_cobranza,
                monto=row.monto_cobrado_ars,
                moneda_id=moneda_ars.id,
                medio_cobro=row.medio,
                referencia=f"CBR-{row.cobranza_id}",
            )
        )
    db.add_all(erp_cobranzas)

    position_acc = defaultdict(lambda: {"contratadas": 0.0, "entregadas": 0.0, "fijadas": 0.0, "stock": 0.0, "precio": []})
    for row in contratos_fact:
        acc = position_acc[row.campania_id]
        acc["contratadas"] += row.kg_contratados / 1000
        acc["entregadas"] += row.kg_entregados / 1000
    for row in embarques_fact:
        camp = contrato_fact_map[row.contrato_venta_id].campania_id
        acc = position_acc[camp]
        acc["precio"].append(row.precio_realizado_usd_tn)
    for row in stock_final_fact:
        acc = position_acc[campanias_dim[-1].campania_id if latest_stock_date and row.fecha == latest_stock_date else campanias_dim[-1].campania_id]
        acc["stock"] += row.kg_stock / 1000
    rendimiento_tn_by_campaign = defaultdict(float)
    for src in rendimientos_fact:
        rendimiento_tn_by_campaign[lote_campania_fact_map[src.lote_campania_id].campania_id] += src.kg_totales / 1000
    for camp_id, values in position_acc.items():
        db.add(
            PosicionComercialERP(
                empresa_id=empresa.id,
                campania_id=campania_map[camp_id].id,
                cultivo_id=cultivo.id,
                toneladas_estimadas=round(sum(src.objetivo_kg_ha * src.superficie_ha for src in lcf_by_campaign[camp_id]) / 1000, 2),
                toneladas_producidas=round(rendimiento_tn_by_campaign[camp_id], 2),
                toneladas_contratadas=round(values["contratadas"], 2),
                toneladas_fijadas=round(values["entregadas"] * 0.82, 2),
                toneladas_entregadas=round(values["entregadas"], 2),
                toneladas_sin_precio=round(max(values["contratadas"] - values["entregadas"] * 0.82, 0), 2),
                stock_fisico_tn=round(values["stock"], 2),
                precio_promedio=round(sum(values["precio"]) / max(len(values["precio"]), 1), 2),
                precio_mercado=round(sum(values["precio"]) / max(len(values["precio"]), 1), 2),
                riesgo="medio" if values["contratadas"] < values["entregadas"] * 1.2 else "alto",
            )
        )

    partes_maquinaria = []
    horas_maquina = []
    disponibilidad_acc = {}
    maint_prev = []
    maint_corr = []
    maquinaria_cycle = maquinarias[:3]
    for idx, row in enumerate(packhouse_turnos):
        maq = maquinaria_cycle[idx % len(maquinaria_cycle)]
        partes_maquinaria.append(
            ParteMaquinaria(
                maquinaria_id=maq.id,
                establecimiento_id=establecimiento_map[row.establecimiento_id].id,
                lote_campania_id=None,
                fecha=row.fecha,
                labor_tipo_id=labor_tipo_map["PACK"].id,
                horometro_inicio=max(maq.horas_totales - row.horas_programadas, 0),
                horometro_fin=maq.horas_totales,
                horas_operativas=row.horas_productivas,
                horas_improductivas=row.horas_downtime,
                hectareas=None,
                operador_id=empleados[2].id,
                observaciones=f"Línea {row.linea_id} turno {row.turno_id}",
            )
        )
        horas_maquina.append(
            HorasMaquina(
                maquinaria_id=maq.id,
                parte_maquinaria_id=None,
                fecha=row.fecha,
                tipo_hora="productiva",
                horas=row.horas_productivas,
                costo_hora=35000,
                costo_total=round(row.horas_productivas * 35000, 2),
            )
        )
        key = (maq.id, row.fecha)
        if key not in disponibilidad_acc:
            disponibilidad_acc[key] = {
                "capacidad": 0.0,
                "productivas": 0.0,
                "improductivas": 0.0,
                "downtime": 0.0,
            }
        disponibilidad_acc[key]["capacidad"] += row.horas_programadas
        disponibilidad_acc[key]["productivas"] += row.horas_productivas
        disponibilidad_acc[key]["improductivas"] += row.horas_downtime
        disponibilidad_acc[key]["downtime"] += row.horas_downtime
    disponibilidades = [
        DisponibilidadEquipo(
            maquinaria_id=maquinaria_id,
            fecha=fecha,
            disponible=values["downtime"] < 2.5,
            capacidad_teorica_horas=round(values["capacidad"], 2),
            horas_productivas=round(values["productivas"], 2),
            horas_improductivas=round(values["improductivas"], 2),
            downtime_horas=round(values["downtime"], 2),
            criticidad="alta" if values["downtime"] > 2.5 else "media" if values["downtime"] > 1 else "baja",
        )
        for (maquinaria_id, fecha), values in disponibilidad_acc.items()
    ]
    db.add_all(partes_maquinaria)
    db.add_all(horas_maquina)
    db.add_all(disponibilidades)

    for idx, row in enumerate(mantenimiento_pack_fact[:80], start=1):
        maq = maquinaria_cycle[idx % len(maquinaria_cycle)]
        maint_prev.append(
            Mantenimiento(
                maquinaria_id=maq.id,
                tipo="preventivo" if row.preventivo else "correctivo",
                fecha=row.fecha,
                descripcion=f"Mantenimiento packhouse {row.tipo}",
                costo=row.costo_ars,
                horas_maquina=maq.horas_totales,
                proximo_service_hs=maq.horas_totales + 180,
            )
        )
    db.add_all(maint_prev)

    await db.flush()
    return {
        "status": "ok",
        "empresa": empresa.nombre,
        "generic": {
            "empresas": 1,
            "establecimientos": len(establecimiento_map),
            "campanias": len(campania_map),
            "lotes": len(old_lote_map),
            "siembras": len(siembras),
            "cosechas_v2": len(cosechas_v2),
            "labores": len(labores),
            "contratos_v2": len(contratos_v2),
            "ventas_v2": len(ventas_v2),
            "flujo_caja_v2": len(flujo_rows),
            "stocks": len(stock_rows),
        },
        "erp": {
            "lote_campania": len(erp_lote_campania_map),
            "rendimientos_lote": len(erp_rendimientos),
            "monitoreos_plagas": len(monitoreos),
            "consumos_insumos": len(consumos),
            "partes_trabajo": len(partes_trabajo),
            "stock_actual": len(stock_actual_rows),
            "movimientos_stock": len(movimiento_stock_rows),
            "contratos_venta": len(erp_contrato_map),
            "entregas": len(entrega_map),
            "liquidaciones": len(erp_liq_map),
            "cuentas_cobrar": len(erp_cxc_map),
            "cobranzas": len(erp_cobranzas),
        },
    }
