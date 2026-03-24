#!/usr/bin/env python3
"""
Chequeo operativo de Lemon BI.

Valida:
- frontend y backend arriba
- rutas principales de los paneles limoneros
- endpoints API activos
- densidad mínima de series
- respuesta a filtros de negocio
- respuesta a filtros temporales

Uso:
  python scripts/check_setup.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx


BACKEND_URL = os.getenv("LEMON_BI_BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("LEMON_BI_FRONTEND_URL", "http://localhost:3000")
TIMEOUT = 20


@dataclass(frozen=True)
class EndpointCheck:
    name: str
    route: str
    api_path: str
    metric_key: str
    series_key: str
    min_points_30d: int
    min_points_90d: int
    filter_param: str


ENDPOINTS = [
    EndpointCheck("Gerencia", "/gerencia", "/api/gerencia/general", "margen_operativo_ars", "resultado_diario", 20, 45, "establecimiento_id"),
    EndpointCheck("Producción", "/produccion", "/api/produccion/campo", "kg_cosechados", "cosecha_diaria", 12, 30, "establecimiento_id"),
    EndpointCheck("Calidad", "/calidad", "/api/calidad/fruta", "packout_promedio_pct", "calidad_diaria", 12, 30, "establecimiento_id"),
    EndpointCheck("Packhouse", "/packhouse", "/api/packhouse/control", "eficiencia_promedio_pct", "procesamiento_diario", 12, 30, "linea_id"),
    EndpointCheck("Comercial", "/comercial-exportacion", "/api/comercial/exportacion", "precio_promedio_usd_tn", "precio_diario", 20, 45, "mercado_id"),
    EndpointCheck("Sanidad", "/sanidad", "/api/sanidad/monitoreo", "incidencia_promedio_pct", "sanidad_semanal", 4, 8, "establecimiento_id"),
    EndpointCheck("Riego", "/riego", "/api/riego/fertirriego", "m3_aplicados", "agua_semanal", 4, 8, "establecimiento_id"),
    EndpointCheck("Macro / Mercado", "/macro-mercado", "/api/macro/mercado", "precio_exportacion_usd_tn", "macro_semanal", 4, 8, "mercado_id"),
]


def icon(ok: bool) -> str:
    return "OK" if ok else "FAIL"


def format_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def fetch_json(client: httpx.Client, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = client.get(f"{BACKEND_URL}{path}", params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_status(client: httpx.Client, url: str) -> int:
    response = client.get(url, timeout=TIMEOUT)
    return response.status_code


def get_catalog_ids(catalogs: dict[str, Any]) -> dict[str, Any]:
    active_campaign = next(item for item in catalogs["campanias"] if item.get("activa"))
    establishments = sorted(catalogs["establecimientos"], key=lambda item: item["id"])
    lines = sorted(catalogs["lineas"], key=lambda item: item["id"])
    markets = sorted(catalogs["mercados"], key=lambda item: item["id"])

    return {
        "campania_id": active_campaign["id"],
        "establecimiento_a": establishments[0]["id"],
        "establecimiento_b": establishments[-1]["id"],
        "linea_a": lines[0]["id"],
        "linea_b": lines[-1]["id"],
        "mercado_a": markets[0]["id"],
        "mercado_b": markets[-1]["id"],
    }


def resolve_filter_values(check: EndpointCheck, ids: dict[str, Any]) -> tuple[Any, Any]:
    if check.filter_param == "establecimiento_id":
        return ids["establecimiento_a"], ids["establecimiento_b"]
    if check.filter_param == "linea_id":
        return ids["linea_a"], ids["linea_b"]
    if check.filter_param == "mercado_id":
        return ids["mercado_a"], ids["mercado_b"]
    raise ValueError(f"Filtro no soportado: {check.filter_param}")


def validate_endpoint(client: httpx.Client, check: EndpointCheck, ids: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    filter_a, filter_b = resolve_filter_values(check, ids)

    base_params = {"campania_id": ids["campania_id"]}
    series_30 = fetch_json(client, check.api_path, {**base_params, "periodo": "30D"})
    series_90 = fetch_json(client, check.api_path, {**base_params, "periodo": "90D"})
    filtered_a = fetch_json(client, check.api_path, {**base_params, check.filter_param: filter_a, "periodo": "30D"})
    filtered_b = fetch_json(client, check.api_path, {**base_params, check.filter_param: filter_b, "periodo": "30D"})

    for payload_name, payload in {
        "30D": series_30,
        "90D": series_90,
        "filtered_a": filtered_a,
        "filtered_b": filtered_b,
    }.items():
        for required_key in ("summary", "series", "breakdown", "meta"):
            if required_key not in payload:
                failures.append(f"{payload_name}: falta `{required_key}`")
        metric_value = payload.get("summary", {}).get(check.metric_key)
        if not is_number(metric_value):
            failures.append(f"{payload_name}: `{check.metric_key}` no es numérico")

    series_rows_30 = series_30.get("series", {}).get(check.series_key, [])
    series_rows_90 = series_90.get("series", {}).get(check.series_key, [])

    if len(series_rows_30) < check.min_points_30d:
        failures.append(f"30D: `{check.series_key}` tiene {len(series_rows_30)} puntos, mínimo esperado {check.min_points_30d}")
    if len(series_rows_90) < check.min_points_90d:
        failures.append(f"90D: `{check.series_key}` tiene {len(series_rows_90)} puntos, mínimo esperado {check.min_points_90d}")
    if len(series_rows_90) < len(series_rows_30):
        failures.append(f"`{check.series_key}` en 90D quedó más corto que 30D")

    metric_30 = series_30["summary"][check.metric_key]
    metric_a = filtered_a["summary"][check.metric_key]
    metric_b = filtered_b["summary"][check.metric_key]
    if metric_a == metric_b == metric_30:
        failures.append(f"`{check.metric_key}` no cambia con `{check.filter_param}`")

    return failures


def validate_historical_campaign_window(client: httpx.Client) -> list[str]:
    failures: list[str] = []
    stale_params = {
        "campania_id": 1,
        "periodo": "30D",
        "from_date": "2026-02-22",
        "to_date": "2026-03-22",
    }
    checks = [
        ("/api/gerencia/general", "resultado_diario"),
        ("/api/calidad/fruta", "calidad_diaria"),
        ("/api/packhouse/control", "procesamiento_diario"),
        ("/api/comercial/exportacion", "precio_diario"),
    ]
    for path, series_key in checks:
        payload = fetch_json(client, path, stale_params)
        series_len = len(payload.get("series", {}).get(series_key, []))
        if series_len == 0:
            failures.append(f"`{path}` devuelve 0 filas con campaña histórica y fechas fuera de campaña")
    return failures


def main() -> int:
    print("\n" + "=" * 72)
    print("  Lemon BI — Verificación Operativa")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)

    failures: list[str] = []

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        try:
            backend_health = fetch_status(client, f"{BACKEND_URL}/api/health")
            frontend_health = fetch_status(client, FRONTEND_URL)
            print(f"\n  Servicios")
            frontend_ok = frontend_health in {200, 307, 308}
            print(f"  {icon(backend_health == 200)} Backend {backend_health}")
            print(f"  {icon(frontend_ok)} Frontend {frontend_health}")
            if backend_health != 200:
                failures.append(f"Backend devolvió {backend_health}")
            if not frontend_ok:
                failures.append(f"Frontend devolvió {frontend_health}")

            catalogs = fetch_json(client, "/api/catalogos/filtros")
            ids = get_catalog_ids(catalogs)
            print("\n  Catálogos")
            print(f"  OK campaña activa: {ids['campania_id']}")
            print(f"  OK establecimientos: {len(catalogs['establecimientos'])}")
            print(f"  OK lotes: {len(catalogs['lotes'])}")
            print(f"  OK líneas: {len(catalogs['lineas'])}")
            print(f"  OK mercados: {len(catalogs['mercados'])}")

            print("\n  Rutas frontend")
            for check in ENDPOINTS:
                status = fetch_status(client, f"{FRONTEND_URL}{check.route}")
                ok = status == 200
                print(f"  {icon(ok)} {check.route} [{status}]")
                if not ok:
                    failures.append(f"Ruta {check.route} devolvió {status}")

            print("\n  APIs y filtros")
            for check in ENDPOINTS:
                status = fetch_status(client, f"{BACKEND_URL}{check.api_path}")
                ok = status == 200
                print(f"  {icon(ok)} {check.name} API [{status}]")
                if not ok:
                    failures.append(f"API {check.api_path} devolvió {status}")
                    continue

                endpoint_failures = validate_endpoint(client, check, ids)
                if endpoint_failures:
                    for failure in endpoint_failures:
                        print(f"    FAIL {failure}")
                    failures.extend([f"{check.name}: {failure}" for failure in endpoint_failures])
                else:
                    payload_30 = fetch_json(client, check.api_path, {"campania_id": ids["campania_id"], "periodo": "30D"})
                    payload_90 = fetch_json(client, check.api_path, {"campania_id": ids["campania_id"], "periodo": "90D"})
                    metric_value = payload_30["summary"][check.metric_key]
                    points_30 = len(payload_30["series"][check.series_key])
                    points_90 = len(payload_90["series"][check.series_key])
                    print(
                        f"    OK {check.metric_key}={format_number(metric_value)} | "
                        f"{check.series_key}: 30D={points_30} 90D={points_90}"
                    )

            print("\n  Campañas cerradas")
            historical_failures = validate_historical_campaign_window(client)
            if historical_failures:
                for failure in historical_failures:
                    print(f"  FAIL {failure}")
                failures.extend(historical_failures)
            else:
                print("  OK ventanas históricas responden aunque lleguen fechas fuera de campaña")

        except Exception as exc:  # pragma: no cover - script operativa
            print(f"\n  FAIL excepción no controlada: {exc}")
            return 1

    print("\n" + "=" * 72)
    if failures:
        print("  FAIL — Hay observaciones para revisar")
        for failure in failures[:20]:
            print(f"  - {failure}")
        if len(failures) > 20:
            print(f"  - ... {len(failures) - 20} más")
        print("=" * 72 + "\n")
        return 1

    print("  OK — Sistema listo para demo operativa")
    print("=" * 72 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
