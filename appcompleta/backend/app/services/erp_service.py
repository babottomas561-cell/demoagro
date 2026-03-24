"""
ERP Service - servicios para los endpoints /api/erp/
"""
from datetime import date
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.siembra import Siembra
from app.models.cosecha_v2 import CosechaV2
from app.models.labor import Labor
from app.models.lote import Lote
from app.models.establecimiento import Establecimiento
from app.models.campania import Campania
from app.models.cultivo import Cultivo
from app.models.cliente import Cliente
from app.models.comercial_v2 import ContratoV2, VentaV2
from app.models.financiero import FlujoCajaV2
from app.models.empresa import Empresa
from app.services.campaign_scope import resolve_campaign_id


async def get_erp_filters(db: AsyncSession):
    empresas = (await db.execute(select(Empresa).order_by(Empresa.nombre))).scalars().all()
    campanias = (await db.execute(select(Campania).order_by(Campania.fecha_inicio.desc()))).scalars().all()
    establecimientos = (await db.execute(select(Establecimiento).order_by(Establecimiento.nombre))).scalars().all()
    clientes = (await db.execute(select(Cliente).order_by(Cliente.nombre))).scalars().all()
    estados_lote = [row[0] for row in (await db.execute(select(Lote.estado).distinct().order_by(Lote.estado))).all() if row[0]]
    tipos_labor = [row[0] for row in (await db.execute(select(Labor.tipo).distinct().order_by(Labor.tipo))).all() if row[0]]
    estados_contrato = [row[0] for row in (await db.execute(select(ContratoV2.estado).distinct().order_by(ContratoV2.estado))).all() if row[0]]

    return {
        "empresas": [{"id": row.id, "nombre": row.nombre} for row in empresas],
        "campanias": [
            {
                "id": row.id,
                "nombre": row.nombre,
                "activa": row.activa,
                "fecha_inicio": row.fecha_inicio.isoformat() if row.fecha_inicio else None,
                "fecha_fin": row.fecha_fin.isoformat() if row.fecha_fin else None,
            }
            for row in campanias
        ],
        "establecimientos": [
            {
                "id": row.id,
                "empresa_id": row.empresa_id,
                "nombre": row.nombre,
                "provincia": row.provincia,
            }
            for row in establecimientos
        ],
        "clientes": [{"id": row.id, "nombre": row.nombre} for row in clientes],
        "estados_lote": estados_lote,
        "tipos_labor": tipos_labor,
        "estados_contrato": estados_contrato,
    }


async def get_siembras(
    db: AsyncSession,
    campania_id: Optional[int] = None,
    empresa_id: Optional[int] = None,
    cultivo_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
):
    resolved_camp = await resolve_campaign_id(db=db, campania_id=campania_id)

    q = (
        select(Siembra, Lote, Establecimiento, Cultivo, Campania)
        .join(Lote, Siembra.lote_id == Lote.id)
        .join(Establecimiento, Lote.establecimiento_id == Establecimiento.id)
        .join(Cultivo, Siembra.cultivo_id == Cultivo.id)
        .join(Campania, Siembra.campania_id == Campania.id)
    )
    if resolved_camp:
        q = q.where(Siembra.campania_id == resolved_camp)
    if empresa_id:
        q = q.where(Establecimiento.empresa_id == empresa_id)
    if cultivo_id:
        q = q.where(Siembra.cultivo_id == cultivo_id)

    total_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    q = q.offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).all()

    items = [
        {
            "id": s.id,
            "lote": l.nombre,
            "establecimiento": est.nombre,
            "provincia": est.provincia,
            "empresa_id": est.empresa_id,
            "campania": camp.nombre,
            "cultivo": cult.nombre,
            "fecha": s.fecha.isoformat() if s.fecha else None,
            "ha_sembradas": s.ha_sembradas,
            "densidad": s.densidad,
            "hibrido": s.hibrido,
            "observaciones": s.observaciones,
        }
        for s, l, est, cult, camp in rows
    ]

    return {"total": total, "page": page, "limit": limit, "items": items}


async def get_cosechas_erp(
    db: AsyncSession,
    campania_id: Optional[int] = None,
    empresa_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
):
    resolved_camp = await resolve_campaign_id(db=db, campania_id=campania_id)

    q = (
        select(CosechaV2, Siembra, Lote, Establecimiento, Cultivo, Campania)
        .join(Siembra, CosechaV2.siembra_id == Siembra.id)
        .join(Lote, Siembra.lote_id == Lote.id)
        .join(Establecimiento, Lote.establecimiento_id == Establecimiento.id)
        .join(Cultivo, Siembra.cultivo_id == Cultivo.id)
        .join(Campania, Siembra.campania_id == Campania.id)
    )
    if resolved_camp:
        q = q.where(Siembra.campania_id == resolved_camp)
    if empresa_id:
        q = q.where(Establecimiento.empresa_id == empresa_id)
    if establecimiento_id:
        q = q.where(Establecimiento.id == establecimiento_id)

    total_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    q = q.offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).all()

    items = [
        {
            "id": c.id,
            "siembra_id": c.siembra_id,
            "lote": l.nombre,
            "establecimiento": est.nombre,
            "empresa_id": est.empresa_id,
            "campania": camp.nombre,
            "cultivo": cult.nombre,
            "fecha": c.fecha.isoformat() if c.fecha else None,
            "ha_cosechadas": c.ha_cosechadas,
            "rendimiento_tn_ha": c.rendimiento_tn_ha,
            "produccion_total_tn": round((c.ha_cosechadas or 0) * (c.rendimiento_tn_ha or 0), 2),
            "humedad": c.humedad,
            "calidad": c.calidad,
            "precio_mercado_usd": c.precio_mercado,
            "valor_total_ars": c.valor_total,
        }
        for c, s, l, est, cult, camp in rows
    ]

    return {"total": total, "page": page, "limit": limit, "items": items}


async def get_labores_erp(
    db: AsyncSession,
    campania_id: Optional[int] = None,
    empresa_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    tipo: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    resolved_camp = await resolve_campaign_id(db=db, campania_id=campania_id)

    q = (
        select(Labor, Lote, Establecimiento)
        .join(Lote, Labor.lote_id == Lote.id)
        .join(Establecimiento, Lote.establecimiento_id == Establecimiento.id)
    )
    if tipo:
        q = q.where(Labor.tipo == tipo)
    if empresa_id:
        q = q.where(Establecimiento.empresa_id == empresa_id)
    if establecimiento_id:
        q = q.where(Establecimiento.id == establecimiento_id)
    # Labor no tiene campania_id directamente, filtrar via lote
    if resolved_camp:
        q = q.where(Lote.campania_id == resolved_camp)

    total_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    q = q.order_by(Labor.fecha.desc()).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).all()

    items = [
        {
            "id": lab.id,
            "lote": l.nombre,
            "establecimiento": est.nombre,
            "empresa_id": est.empresa_id,
            "tipo": lab.tipo,
            "fecha": lab.fecha.isoformat() if lab.fecha else None,
            "ha_trabajadas": l.hectareas,
            "costo_ha": lab.costo_ha,
            "costo_total": round((l.hectareas or 0) * (lab.costo_ha or 0), 2),
            "observacion": lab.observacion,
        }
        for lab, l, est in rows
    ]

    return {"total": total, "page": page, "limit": limit, "items": items}


async def get_contratos_erp(
    db: AsyncSession,
    estado: Optional[str] = None,
    campania_id: Optional[int] = None,
    empresa_id: Optional[int] = None,
    cliente_id: Optional[int] = None,
):
    resolved_camp = await resolve_campaign_id(db=db, campania_id=campania_id)

    q = (
        select(ContratoV2, Cultivo, Cliente, Campania)
        .join(Cultivo, ContratoV2.cultivo_id == Cultivo.id)
        .join(Cliente, ContratoV2.cliente_id == Cliente.id)
        .join(Campania, ContratoV2.campania_id == Campania.id)
    )
    if estado:
        q = q.where(ContratoV2.estado == estado)
    if resolved_camp:
        q = q.where(ContratoV2.campania_id == resolved_camp)
    if empresa_id:
        q = q.where(ContratoV2.empresa_id == empresa_id)
    if cliente_id:
        q = q.where(ContratoV2.cliente_id == cliente_id)

    rows = (await db.execute(q)).all()

    items = [
        {
            "id": c.id,
            "empresa_id": c.empresa_id,
            "campania": camp.nombre,
            "cultivo": cult.nombre,
            "cliente": cli.nombre,
            "tipo": c.tipo,
            "cantidad_tn": c.cantidad_tn,
            "precio_usd": c.precio_usd,
            "precio_ars": c.precio_ars,
            "fecha_firma": c.fecha_firma.isoformat() if c.fecha_firma else None,
            "fecha_entrega": c.fecha_entrega.isoformat() if c.fecha_entrega else None,
            "estado": c.estado,
            "valor_total_ars": round((c.cantidad_tn or 0) * (c.precio_ars or 0), 2),
            "valor_total_usd": round((c.cantidad_tn or 0) * (c.precio_usd or 0), 2),
        }
        for c, cult, cli, camp in rows
    ]

    return {"total": len(items), "items": items}


async def get_ventas_erp(
    db: AsyncSession,
    campania_id: Optional[int] = None,
    empresa_id: Optional[int] = None,
    cliente_id: Optional[int] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
):
    resolved_camp = await resolve_campaign_id(db=db, campania_id=campania_id)

    q = (
        select(VentaV2, Cultivo, Cliente)
        .join(Cultivo, VentaV2.cultivo_id == Cultivo.id)
        .join(Cliente, VentaV2.cliente_id == Cliente.id)
        .order_by(VentaV2.fecha.desc())
    )
    if resolved_camp:
        q = q.where(VentaV2.campania_id == resolved_camp)
    if empresa_id:
        q = q.where(VentaV2.empresa_id == empresa_id)
    if cliente_id:
        q = q.where(VentaV2.cliente_id == cliente_id)
    if desde:
        try:
            q = q.where(VentaV2.fecha >= date.fromisoformat(desde))
        except ValueError:
            pass
    if hasta:
        try:
            q = q.where(VentaV2.fecha <= date.fromisoformat(hasta))
        except ValueError:
            pass

    rows = (await db.execute(q)).all()

    items = [
        {
            "id": v.id,
            "empresa_id": v.empresa_id,
            "campania_id": v.campania_id,
            "cultivo": cult.nombre,
            "cliente": cli.nombre,
            "fecha": v.fecha.isoformat() if v.fecha else None,
            "cantidad_tn": v.cantidad_tn,
            "precio_ars_tn": v.precio_ars_tn,
            "precio_usd_tn": v.precio_usd_tn,
            "importe_total_ars": v.importe_total_ars,
            "tipo_cambio": v.tipo_cambio,
            "condicion_pago": v.condicion_pago,
        }
        for v, cult, cli in rows
    ]

    total_ars = round(sum(v.importe_total_ars or 0 for v, _, _ in rows), 2)
    total_tn = round(sum(v.cantidad_tn or 0 for v, _, _ in rows), 2)

    return {
        "total_registros": len(items),
        "total_ars": total_ars,
        "total_tn": total_tn,
        "items": items,
    }


async def get_flujo_caja_erp(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    categoria: Optional[str] = None,
):
    resolved_camp = await resolve_campaign_id(db=db, campania_id=campania_id)
    q = select(FlujoCajaV2).order_by(FlujoCajaV2.fecha.desc())
    if empresa_id:
        q = q.where(FlujoCajaV2.empresa_id == empresa_id)
    if resolved_camp:
        q = q.where(FlujoCajaV2.campania_id == resolved_camp)
    if categoria:
        q = q.where(FlujoCajaV2.categoria == categoria)
    if desde:
        try:
            q = q.where(FlujoCajaV2.fecha >= date.fromisoformat(desde))
        except ValueError:
            pass
    if hasta:
        try:
            q = q.where(FlujoCajaV2.fecha <= date.fromisoformat(hasta))
        except ValueError:
            pass

    rows = (await db.execute(q)).scalars().all()

    ingresos = sum(f.importe_ars or 0 for f in rows if f.tipo == "ingreso")
    egresos = sum(f.importe_ars or 0 for f in rows if f.tipo == "egreso")

    items = [
        {
            "id": f.id,
            "empresa_id": f.empresa_id,
            "fecha": f.fecha.isoformat() if f.fecha else None,
            "tipo": f.tipo,
            "categoria": f.categoria,
            "subcategoria": f.subcategoria,
            "importe_ars": f.importe_ars,
            "importe_usd": f.importe_usd,
            "tipo_cambio": f.tipo_cambio,
            "descripcion": f.descripcion,
        }
        for f in rows
    ]

    return {
        "total_registros": len(items),
        "ingresos_ars": round(ingresos, 2),
        "egresos_ars": round(egresos, 2),
        "resultado_neto_ars": round(ingresos - egresos, 2),
        "items": items,
    }


async def get_lotes_erp(
    db: AsyncSession,
    campania_id: Optional[int] = None,
    empresa_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    estado: Optional[str] = None,
):
    resolved_camp = await resolve_campaign_id(db=db, campania_id=campania_id)
    q = (
        select(Lote, Establecimiento, Cultivo)
        .join(Establecimiento, Lote.establecimiento_id == Establecimiento.id)
        .outerjoin(Cultivo, Lote.cultivo_id == Cultivo.id)
    )
    if resolved_camp:
        q = q.where(Lote.campania_id == resolved_camp)
    if empresa_id:
        q = q.where(Establecimiento.empresa_id == empresa_id)
    if establecimiento_id:
        q = q.where(Lote.establecimiento_id == establecimiento_id)
    if estado:
        q = q.where(Lote.estado == estado)

    rows = (await db.execute(q)).all()

    items = [
        {
            "id": l.id,
            "nombre": l.nombre,
            "establecimiento": est.nombre,
            "empresa_id": est.empresa_id,
            "provincia": est.provincia,
            "ha": l.hectareas,
            "cultivo": cult.nombre if cult else None,
            "estado": l.estado,
            "fecha_siembra": l.fecha_siembra.isoformat() if l.fecha_siembra else None,
            "rendimiento_real": l.rendimiento_real,
            "rendimiento_historico": l.rendimiento_historico,
        }
        for l, est, cult in rows
    ]

    ha_total = round(sum(l.hectareas for l, _, _ in rows), 2)
    ha_sembradas = round(sum(l.hectareas for l, _, _ in rows if l.estado in ("sembrado", "cosechado")), 2)

    return {
        "total": len(items),
        "ha_total": ha_total,
        "ha_sembradas": ha_sembradas,
        "items": items,
    }
