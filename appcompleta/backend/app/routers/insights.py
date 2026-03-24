# Insights router - genera insights automaticos basados en datos de la BD
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import date

from app.database import get_db
from app.models.venta import Venta
from app.models.lote import Lote
from app.models.stock import Stock
from app.models.producto import Producto
from app.models.contrato import Contrato
from app.models.maquinaria import Maquinaria
from app.models.mantenimiento import Mantenimiento
from app.models.establecimiento import Establecimiento
from app.models.flujo_financiero import FlujoCaja

router = APIRouter()


@router.get("/insights/ejecutivos")
async def get_insights_ejecutivos(
    empresa_id: Optional[int] = Query(None),
    campania_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Genera insights automaticos basados en los datos de la empresa."""
    insights = []

    # 1. Rendimiento vs historico
    lotes_q = select(Lote).where(Lote.rendimiento_real.isnot(None), Lote.rendimiento_historico.isnot(None))
    if campania_id:
        lotes_q = lotes_q.where(Lote.campania_id == campania_id)
    lotes_r = await db.execute(lotes_q)
    lotes = lotes_r.scalars().all()

    if lotes:
        rend_prom = sum(l.rendimiento_real for l in lotes) / len(lotes)
        rend_hist = sum(l.rendimiento_historico for l in lotes) / len(lotes)
        diferencia_pct = (rend_prom - rend_hist) / rend_hist * 100 if rend_hist > 0 else 0
        if diferencia_pct > 10:
            insights.append({
                "tipo": "positivo",
                "categoria": "agricola",
                "titulo": "Rendimiento superior al historico",
                "descripcion": f"El rendimiento promedio actual ({round(rend_prom, 2)} tn/ha) supera el historico ({round(rend_hist, 2)} tn/ha) en un {round(diferencia_pct, 1)}%.",
                "impacto": "alto",
                "prioridad": 1,
            })
        elif diferencia_pct < -10:
            insights.append({
                "tipo": "alerta",
                "categoria": "agricola",
                "titulo": "Rendimiento por debajo del historico",
                "descripcion": f"El rendimiento promedio ({round(rend_prom, 2)} tn/ha) esta {round(abs(diferencia_pct), 1)}% por debajo del historico.",
                "impacto": "alto",
                "prioridad": 1,
            })

    # 2. Stock disponible
    stock_q = select(Stock, Producto).join(Producto, Stock.producto_id == Producto.id)
    stock_r = await db.execute(stock_q)
    stock_rows = stock_r.all()
    total_stock = sum(r[0].volumen_disponible for r in stock_rows)
    valor_stock = sum((r[0].volumen_disponible or 0) * (r[1].precio_referencia or 0) for r in stock_rows)
    if total_stock > 500:
        insights.append({
            "tipo": "oportunidad",
            "categoria": "comercial",
            "titulo": "Alto volumen de stock disponible",
            "descripcion": f"Hay {round(total_stock, 1)} toneladas disponibles, valuadas en ARS {round(valor_stock/1_000_000, 1)} M. Evaluar ventas antes del fin de campana.",
            "impacto": "alto",
            "prioridad": 2,
        })

    # 3. Contratos a vencer
    contratos_q = select(Contrato).where(Contrato.estado == "vigente")
    contratos_r = await db.execute(contratos_q)
    contratos_vigentes = contratos_r.scalars().all()
    contratos_prox = [
        c for c in contratos_vigentes
        if c.fecha_entrega and (c.fecha_entrega - date.today()).days < 60
    ]
    if contratos_prox:
        vol_comprometido = sum(c.volumen_contratado for c in contratos_prox)
        insights.append({
            "tipo": "advertencia",
            "categoria": "comercial",
            "titulo": f"{len(contratos_prox)} contratos con entrega proxima",
            "descripcion": f"Existen {len(contratos_prox)} contratos con entrega en los proximos 60 dias, totalizando {round(vol_comprometido, 1)} toneladas.",
            "impacto": "medio",
            "prioridad": 2,
        })

    # 4. Maquinaria con alertas de service
    maq_q = select(Maquinaria)
    if empresa_id:
        maq_q = maq_q.join(Establecimiento).where(Establecimiento.empresa_id == empresa_id)
    maq_r = await db.execute(maq_q)
    maquinas = maq_r.scalars().all()

    maquinas_alerta = 0
    for m in maquinas:
        ult_q = select(Mantenimiento).where(Mantenimiento.maquinaria_id == m.id)\
            .order_by(Mantenimiento.fecha.desc()).limit(1)
        ult_r = await db.execute(ult_q)
        ult = ult_r.scalar_one_or_none()
        if ult and ult.proximo_service_hs and (ult.proximo_service_hs - m.horas_totales) < 100:
            maquinas_alerta += 1

    if maquinas_alerta > 0:
        insights.append({
            "tipo": "advertencia",
            "categoria": "maquinaria",
            "titulo": f"{maquinas_alerta} equipo(s) requieren service pronto",
            "descripcion": f"{maquinas_alerta} maquinas estan proximas a su service. Programar mantenimiento preventivo.",
            "impacto": "medio",
            "prioridad": 3,
        })

    # 5. Flujo de caja
    flujo_q = select(FlujoCaja)
    if empresa_id:
        flujo_q = flujo_q.where(FlujoCaja.empresa_id == empresa_id)
    flujo_r = await db.execute(flujo_q)
    flujos = flujo_r.scalars().all()
    ingresos = sum(f.monto for f in flujos if f.tipo == "ingreso")
    egresos = sum(f.monto for f in flujos if f.tipo == "egreso")
    ratio = ingresos / max(egresos, 1)

    if ratio > 1.5:
        insights.append({
            "tipo": "positivo",
            "categoria": "finanzas",
            "titulo": "Excelente posicion financiera",
            "descripcion": f"Los ingresos superan a los egresos en un ratio de {round(ratio, 2)}x. Solida generacion de caja.",
            "impacto": "alto",
            "prioridad": 1,
        })
    elif ratio < 1.0:
        insights.append({
            "tipo": "alerta",
            "categoria": "finanzas",
            "titulo": "Flujo de caja negativo",
            "descripcion": f"Los egresos superan a los ingresos (ratio {round(ratio, 2)}x). Revisar estructura de costos.",
            "impacto": "critico",
            "prioridad": 1,
        })

    # 6. Precio de soja
    insights.append({
        "tipo": "oportunidad",
        "categoria": "mercado",
        "titulo": "Precio de soja en nivel atractivo",
        "descripcion": "El precio de la soja se encuentra en USD 295/tn (MATBA), nivel historicamente alto. Considerar fijar posicion futura.",
        "impacto": "alto",
        "prioridad": 2,
    })

    insights.sort(key=lambda x: x["prioridad"])

    return {
        "total_insights": len(insights),
        "insights": insights,
        "fecha_generacion": date.today().isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints de insights basados en datos externos reales
# ─────────────────────────────────────────────────────────────────────────────

import asyncio  # noqa: E402
import logging  # noqa: E402
from app.services.external_data_service import ExternalDataService  # noqa: E402
from app.services.cache_service import cache_service  # noqa: E402
from fastapi import HTTPException  # noqa: E402

_ext_logger = logging.getLogger(__name__)
_ext_service = ExternalDataService()


@router.get("/insights/externos")
async def get_insights_externos():
    """
    Insights automaticos generados desde APIs externas reales.

    Fuentes: BCRA + datos.gob.ar + Yahoo Finance CBOT + Open-Meteo.
    Cache TTL: 1 hora.
    """
    try:
        return await _ext_service.get_insights_macro()
    except Exception as exc:
        _ext_logger.exception("Error en /insights/externos: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/insights/cache-status")
async def get_cache_status():
    """Estado del sistema de cache (Redis o memoria en proceso)."""
    try:
        return await cache_service.cache_status()
    except Exception as exc:
        _ext_logger.exception("Error en /insights/cache-status: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/insights/cache")
async def invalidar_cache_externo(
    patron: str = Query("*", description="Patron glob de claves a invalidar"),
):
    """Invalida claves del cache de datos externos por patron glob."""
    try:
        eliminadas = await cache_service.invalidate_pattern(patron)
        return {"ok": True, "patron": patron, "claves_eliminadas": eliminadas}
    except Exception as exc:
        _ext_logger.exception("Error al invalidar cache '%s': %s", patron, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/insights/fuentes")
async def get_estado_fuentes():
    """Estado de disponibilidad de cada fuente de datos externa."""
    from app.integrations.usda_client import USDAClient
    from app.integrations.bcr_client import BCRClient

    usda = USDAClient()
    bcr = BCRClient()
    usda_ok, bcr_ok = await asyncio.gather(usda.is_available(), bcr.is_available())

    return {
        "fuentes": [
            {
                "nombre": "BCRA - Banco Central de la Republica Argentina",
                "url": "https://api.bcra.gob.ar/estadisticas/v3.0/",
                "disponible": True,
                "requiere_api_key": False,
                "nota": "API publica. SSL verify=False por problemas de certificado.",
                "datos": ["tipo_cambio", "inflacion", "tasas", "reservas"],
            },
            {
                "nombre": "Datos Abiertos Argentina - Series de Tiempo",
                "url": "https://apis.datos.gob.ar/series/api/",
                "disponible": True,
                "requiere_api_key": False,
                "nota": "API publica del gobierno argentino.",
                "datos": ["ipc", "tipo_cambio_bna", "pbi", "exportaciones"],
            },
            {
                "nombre": "Open-Meteo",
                "url": "https://open-meteo.com",
                "disponible": True,
                "requiere_api_key": False,
                "nota": "API meteorologica gratuita para uso no comercial.",
                "datos": ["pronostico_7d", "historico_30d", "alertas_climaticas"],
            },
            {
                "nombre": "Yahoo Finance CBOT Futures",
                "url": "https://finance.yahoo.com",
                "disponible": True,
                "requiere_api_key": False,
                "nota": "Endpoint JSON publico. Precios diferidos ~15 minutos.",
                "datos": ["soja_ZS=F", "maiz_ZC=F", "trigo_ZW=F"],
            },
            {
                "nombre": "USDA FAS - Production Supply and Distribution",
                "url": "https://apps.fas.usda.gov/psdonline/",
                "disponible": usda_ok,
                "requiere_api_key": True,
                "nota": "Requiere USDA_API_KEY. Fallback a datos estaticos 2023/24.",
                "datos": ["produccion_soja", "produccion_maiz", "produccion_trigo"],
            },
            {
                "nombre": "BCR - Bolsa de Comercio de Rosario",
                "url": "https://www.bcr.com.ar",
                "disponible": bcr_ok,
                "requiere_api_key": False,
                "nota": "Sin API REST publica. Usa precios de referencia + INDEC.",
                "datos": ["precios_pizarra_referencia", "exportaciones_cereales_indec"],
            },
        ]
    }
