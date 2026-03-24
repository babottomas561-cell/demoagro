from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.lemon_dimensions import (
    CalibreDim,
    CampaniaDim,
    CanalDim,
    CampoDim,
    ClienteDim,
    DestinoFrutaDim,
    EmpresaDim,
    EstablecimientoDim,
    LineaEmpaqueDim,
    LoteDim,
    MercadoDim,
    TurnoDim,
    VariedadDim,
)

router = APIRouter()


@router.get("/catalogos/filtros")
async def get_filtros(db: AsyncSession = Depends(get_db)):
    empresas = (await db.execute(select(EmpresaDim).where(EmpresaDim.activa.is_(True)).order_by(EmpresaDim.nombre))).scalars().all()
    campanias = (await db.execute(select(CampaniaDim).order_by(CampaniaDim.fecha_inicio.desc()))).scalars().all()
    establecimientos = (await db.execute(select(EstablecimientoDim).order_by(EstablecimientoDim.nombre))).scalars().all()
    campos = (await db.execute(select(CampoDim).order_by(CampoDim.nombre))).scalars().all()
    lotes = (await db.execute(select(LoteDim).order_by(LoteDim.nombre))).scalars().all()
    variedades = (await db.execute(select(VariedadDim).where(VariedadDim.activa.is_(True)).order_by(VariedadDim.nombre))).scalars().all()
    clientes = (await db.execute(select(ClienteDim).where(ClienteDim.activo.is_(True)).order_by(ClienteDim.nombre))).scalars().all()
    mercados = (await db.execute(select(MercadoDim).where(MercadoDim.activo.is_(True)).order_by(MercadoDim.nombre))).scalars().all()
    canales = (await db.execute(select(CanalDim).where(CanalDim.activo.is_(True)).order_by(CanalDim.nombre))).scalars().all()
    lineas = (await db.execute(select(LineaEmpaqueDim).where(LineaEmpaqueDim.activa.is_(True)).order_by(LineaEmpaqueDim.nombre))).scalars().all()
    turnos = (await db.execute(select(TurnoDim).where(TurnoDim.activo.is_(True)).order_by(TurnoDim.turno_id))).scalars().all()
    destinos = (await db.execute(select(DestinoFrutaDim).order_by(DestinoFrutaDim.orden))).scalars().all()
    calibres = (await db.execute(select(CalibreDim).order_by(CalibreDim.diametro_max_mm.desc()))).scalars().all()

    return {
        "empresas": [
            {
                "id": item.empresa_id,
                "codigo": item.codigo,
                "nombre": item.nombre,
                "razon_social": item.razon_social,
                "provincia_base": item.provincia_base,
            }
            for item in empresas
        ],
        "campanias": [
            {
                "id": item.campania_id,
                "codigo": item.codigo,
                "nombre": item.nombre,
                "fecha_inicio": item.fecha_inicio,
                "fecha_fin": item.fecha_fin,
                "estado": item.estado,
                "activa": item.activa,
            }
            for item in campanias
        ],
        "establecimientos": [
            {
                "id": item.establecimiento_id,
                "codigo": item.codigo,
                "nombre": item.nombre,
                "empresa_id": item.empresa_id,
                "provincia": item.provincia,
                "localidad": item.localidad,
                "superficie_total_ha": item.superficie_total_ha,
                "packhouse_activo": item.packhouse_activo,
                "lat": item.lat,
                "lon": item.lon,
            }
            for item in establecimientos
        ],
        "campos": [
            {
                "id": item.campo_id,
                "codigo": item.codigo,
                "nombre": item.nombre,
                "establecimiento_id": item.establecimiento_id,
                "superficie_ha": item.superficie_ha,
            }
            for item in campos
        ],
        "lotes": [
            {
                "id": item.lote_id,
                "codigo": item.codigo,
                "nombre": item.nombre,
                "campo_id": item.campo_id,
                "superficie_ha": item.superficie_ha,
                "anio_plantacion": item.anio_plantacion,
            }
            for item in lotes
        ],
        "variedades": [
            {
                "id": item.variedad_id,
                "codigo": item.codigo,
                "nombre": item.nombre,
                "grupo": item.grupo,
                "destino_preferido": item.destino_preferido,
            }
            for item in variedades
        ],
        "clientes": [
            {
                "id": item.cliente_id,
                "codigo": item.codigo,
                "nombre": item.nombre,
                "tipo": item.tipo,
                "pais": item.pais,
                "region": item.region,
            }
            for item in clientes
        ],
        "mercados": [
            {
                "id": item.mercado_id,
                "codigo": item.codigo,
                "nombre": item.nombre,
                "region": item.region,
                "moneda": item.moneda,
            }
            for item in mercados
        ],
        "canales": [
            {
                "id": item.canal_id,
                "codigo": item.codigo,
                "nombre": item.nombre,
            }
            for item in canales
        ],
        "lineas": [
            {
                "id": item.linea_id,
                "codigo": item.codigo,
                "nombre": item.nombre,
                "establecimiento_id": item.establecimiento_id,
                "capacidad_tn_hora": item.capacidad_tn_hora,
            }
            for item in lineas
        ],
        "turnos": [
            {
                "id": item.turno_id,
                "codigo": item.codigo,
                "nombre": item.nombre,
            }
            for item in turnos
        ],
        "destinos": [
            {
                "id": item.destino_id,
                "codigo": item.codigo,
                "nombre": item.nombre,
                "es_comercial": item.es_comercial,
            }
            for item in destinos
        ],
        "calibres": [
            {
                "id": item.calibre_id,
                "codigo": item.codigo,
                "nombre": item.nombre,
                "apto_exportacion": item.apto_exportacion,
            }
            for item in calibres
        ],
        "monedas": [
            {"id": "ARS", "codigo": "ARS", "nombre": "Peso argentino"},
            {"id": "USD", "codigo": "USD", "nombre": "Dólar estadounidense"},
        ],
    }


@router.get("/catalogos/campanias")
async def get_campanias(db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(CampaniaDim).order_by(CampaniaDim.fecha_inicio.desc()))).scalars().all()
    return {"items": [{"id": item.campania_id, "nombre": item.nombre, "activa": item.activa} for item in items]}


@router.get("/catalogos/establecimientos")
async def get_establecimientos(db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(EstablecimientoDim).order_by(EstablecimientoDim.nombre))).scalars().all()
    return {"items": [{"id": item.establecimiento_id, "nombre": item.nombre, "empresa_id": item.empresa_id} for item in items]}


@router.get("/catalogos/campos")
async def get_campos(db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(CampoDim).order_by(CampoDim.nombre))).scalars().all()
    return {"items": [{"id": item.campo_id, "nombre": item.nombre, "establecimiento_id": item.establecimiento_id} for item in items]}


@router.get("/catalogos/lotes")
async def get_lotes(db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(LoteDim).order_by(LoteDim.nombre))).scalars().all()
    return {"items": [{"id": item.lote_id, "nombre": item.nombre, "campo_id": item.campo_id} for item in items]}


@router.get("/catalogos/variedades")
async def get_variedades(db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(VariedadDim).where(VariedadDim.activa.is_(True)).order_by(VariedadDim.nombre))).scalars().all()
    return {"items": [{"id": item.variedad_id, "nombre": item.nombre} for item in items]}


@router.get("/catalogos/clientes")
async def get_clientes(db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(ClienteDim).where(ClienteDim.activo.is_(True)).order_by(ClienteDim.nombre))).scalars().all()
    return {"items": [{"id": item.cliente_id, "nombre": item.nombre} for item in items]}


@router.get("/catalogos/mercados")
async def get_mercados(db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(MercadoDim).where(MercadoDim.activo.is_(True)).order_by(MercadoDim.nombre))).scalars().all()
    return {"items": [{"id": item.mercado_id, "nombre": item.nombre} for item in items]}
