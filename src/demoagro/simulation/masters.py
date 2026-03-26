from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from demoagro.config import CROP_LIBRARY, PAYROLL_CATEGORIES, PRODUCT_LIBRARY, SimulationConfig
from demoagro.simulation.common import add_days, campaign_date, frame, make_ids, weighted_choice


def generate_master_data(config: SimulationConfig, rng: np.random.Generator) -> dict[str, pd.DataFrame]:
    units = frame(
        [
            {"unidad_medida_id": "UOM_0001", "uom_code": "KG", "uom_name": "Kilogramo"},
            {"unidad_medida_id": "UOM_0002", "uom_code": "TN", "uom_name": "Tonelada"},
            {"unidad_medida_id": "UOM_0003", "uom_code": "LT", "uom_name": "Litro"},
            {"unidad_medida_id": "UOM_0004", "uom_code": "HA", "uom_name": "Hectarea"},
            {"unidad_medida_id": "UOM_0005", "uom_code": "UN", "uom_name": "Unidad"},
            {"unidad_medida_id": "UOM_0006", "uom_code": "HR", "uom_name": "Hora"},
            {"unidad_medida_id": "UOM_0007", "uom_code": "MES", "uom_name": "Mes"},
        ]
    )

    categories = frame(
        [
            {"categoria_producto_id": "CAT_0001", "category_code": "GRANO", "category_name": "Grano"},
            {"categoria_producto_id": "CAT_0002", "category_code": "SEMILLA", "category_name": "Semilla"},
            {"categoria_producto_id": "CAT_0003", "category_code": "FERTILIZANTE", "category_name": "Fertilizante"},
            {"categoria_producto_id": "CAT_0004", "category_code": "FITOSANITARIO", "category_name": "Fitosanitario"},
            {"categoria_producto_id": "CAT_0005", "category_code": "COMBUSTIBLE", "category_name": "Combustible"},
            {"categoria_producto_id": "CAT_0006", "category_code": "REPUESTO", "category_name": "Repuesto"},
            {"categoria_producto_id": "CAT_0007", "category_code": "SERVICIO", "category_name": "Servicio"},
        ]
    )

    vat_conditions = frame(
        [
            {"condicion_iva_id": "IVA_0001", "condition_code": "RI", "condition_name": "Responsable Inscripto"},
            {"condicion_iva_id": "IVA_0002", "condition_code": "MT", "condition_name": "Monotributo"},
        ]
    )

    labor_types = frame(
        [
            {"labor_tipo_id": "LABT_0001", "labor_type_code": "SIEMBRA", "labor_type_name": "Siembra"},
            {"labor_tipo_id": "LABT_0002", "labor_type_code": "FERTILIZACION", "labor_type_name": "Fertilizacion"},
            {"labor_tipo_id": "LABT_0003", "labor_type_code": "PULVERIZACION", "labor_type_name": "Pulverizacion"},
            {"labor_tipo_id": "LABT_0004", "labor_type_code": "COSECHA", "labor_type_name": "Cosecha"},
        ]
    )

    payroll_categories = frame(
        [
            {
                "categoria_rrhh_id": f"RRC_{index + 1:04d}",
                "category_code": category["category_code"],
                "category_name": category["category_name"],
                "base_salary": category["base_salary"],
            }
            for index, category in enumerate(PAYROLL_CATEGORIES)
        ]
    )

    tax_types = frame(
        [
            {"tipo_impuesto_id": "TAX_0001", "tax_code": "IVA_DEBITO", "tax_name": "IVA Debito Fiscal"},
            {"tipo_impuesto_id": "TAX_0002", "tax_code": "IVA_CREDITO", "tax_name": "IVA Credito Fiscal"},
            {"tipo_impuesto_id": "TAX_0003", "tax_code": "CARGAS_SOC", "tax_name": "Cargas Sociales"},
        ]
    )

    product_rows: list[dict[str, object]] = []
    for index, product in enumerate(PRODUCT_LIBRARY, start=1):
        product_rows.append(
            {
                "producto_id": f"PROD_{index:04d}",
                **product,
                "currency_code": config.currency_code,
            }
        )
    products = frame(product_rows)

    company = frame(
        [
            {
                "empresa_id": "EMP_0001",
                "company_name": config.company_name,
                "currency_code": config.currency_code,
                "country_code": "AR",
            }
        ]
    )

    establishments = frame(
        [
            {
                "establecimiento_id": "EST_0001",
                "empresa_id": "EMP_0001",
                "establishment_name": "Campo Norte",
                "region_code": "NOA",
            },
            {
                "establecimiento_id": "EST_0002",
                "empresa_id": "EMP_0001",
                "establishment_name": "Campo Sur",
                "region_code": "CENTRO",
            },
        ]
    )

    cost_centers = frame(
        [
            {"centro_costo_id": "CC_0001", "empresa_id": "EMP_0001", "center_code": "AGRO", "center_name": "Produccion Agricola"},
            {"centro_costo_id": "CC_0002", "empresa_id": "EMP_0001", "center_code": "LOG", "center_name": "Logistica"},
            {"centro_costo_id": "CC_0003", "empresa_id": "EMP_0001", "center_code": "MNT", "center_name": "Mantenimiento"},
            {"centro_costo_id": "CC_0004", "empresa_id": "EMP_0001", "center_code": "ADM", "center_name": "Administracion"},
            {"centro_costo_id": "CC_0005", "empresa_id": "EMP_0001", "center_code": "COM", "center_name": "Comercial"},
            {"centro_costo_id": "CC_0006", "empresa_id": "EMP_0001", "center_code": "RRHH", "center_name": "RRHH"},
        ]
    )

    deposits = frame(
        [
            {
                "deposito_id": "DEP_0001",
                "establecimiento_id": "EST_0001",
                "deposit_name": "Panal de Insumos Norte",
                "deposit_type": "INSUMOS",
            },
            {
                "deposito_id": "DEP_0002",
                "establecimiento_id": "EST_0001",
                "deposit_name": "Silo Norte",
                "deposit_type": "GRANO",
            },
            {
                "deposito_id": "DEP_0003",
                "establecimiento_id": "EST_0002",
                "deposit_name": "Silo Sur",
                "deposit_type": "GRANO",
            },
            {
                "deposito_id": "DEP_0004",
                "establecimiento_id": "EST_0001",
                "deposit_name": "Panal de Repuestos",
                "deposit_type": "REPUESTOS",
            },
        ]
    )

    clients = _generate_clients(config, rng)
    suppliers = _generate_suppliers(config, rng)
    campaigns = _generate_campaigns(config)
    lots = _generate_lots(config, rng)
    lot_campaign = _generate_lot_campaign(config, rng, lots, campaigns)
    financial_accounts = frame(
        [
            {"cuenta_financiera_id": "BANK_0001", "empresa_id": "EMP_0001", "account_name": "Caja Operativa", "account_type": "CAJA"},
            {"cuenta_financiera_id": "BANK_0002", "empresa_id": "EMP_0001", "account_name": "Banco Principal", "account_type": "BANCO"},
            {"cuenta_financiera_id": "BANK_0003", "empresa_id": "EMP_0001", "account_name": "Banco Cobros", "account_type": "BANCO"},
        ]
    )
    employees = _generate_employees(config, rng, payroll_categories)
    assets = _generate_assets(config, rng)
    transporters = _generate_transporters()
    chart_of_accounts = _generate_chart_of_accounts()

    return {
        "fin_condiciones_iva": vat_conditions,
        "erp_unidades_medida": units,
        "erp_categorias_producto": categories,
        "erp_productos": products,
        "erp_empresas": company,
        "erp_establecimientos": establishments,
        "erp_centros_costo": cost_centers,
        "erp_depositos": deposits,
        "erp_clientes": clients,
        "erp_proveedores": suppliers,
        "erp_campanias": campaigns,
        "erp_lotes": lots,
        "erp_lote_campania": lot_campaign,
        "erp_labores_tipo": labor_types,
        "fin_cuentas_financieras": financial_accounts,
        "rrhh_categorias": payroll_categories,
        "rrhh_empleados": employees,
        "mnt_activos": assets,
        "log_transportistas": transporters,
        "cont_plan_cuentas": chart_of_accounts,
        "tax_tipos_impuesto": tax_types,
    }


def _generate_campaigns(config: SimulationConfig) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    start_year = config.active_campaign_start_year - (config.campaign_count - 1)
    for index, campaign_start in enumerate(range(start_year, config.active_campaign_start_year + 1), start=1):
        rows.append(
            {
                "campania_id": f"CAMP_{index:04d}",
                "empresa_id": "EMP_0001",
                "campaign_code": f"{campaign_start}/{campaign_start + 1}",
                "campaign_start_date": date(campaign_start, 7, 1),
                "campaign_end_date": date(campaign_start + 1, 6, 30),
                "campaign_weather_factor": round(0.92 + index * 0.06, 3),
            }
        )
    return frame(rows)


def _generate_lots(config: SimulationConfig, rng: np.random.Generator) -> pd.DataFrame:
    lot_ids = make_ids("LOT", config.num_lots)
    rows: list[dict[str, object]] = []
    for lot_id in lot_ids:
        establishment_id = weighted_choice(["EST_0001", "EST_0002"], [0.55, 0.45], rng)
        hectares = round(float(rng.uniform(85, 210)), 1)
        rows.append(
            {
                "lote_id": lot_id,
                "establecimiento_id": establishment_id,
                "lot_name": lot_id.replace("_", "-"),
                "net_hectares": hectares,
                "soil_productivity_index": round(float(rng.uniform(0.88, 1.16)), 3),
                "distance_to_silo_km": int(rng.integers(8, 52)),
            }
        )
    return frame(rows)


def _generate_lot_campaign(
    config: SimulationConfig,
    rng: np.random.Generator,
    lots: pd.DataFrame,
    campaigns: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    sequence = 1
    for _, campaign in campaigns.iterrows():
        for _, lot in lots.iterrows():
            crop_code = weighted_choice(config.crop_mix.keys(), config.crop_mix.values(), rng)
            crop = CROP_LIBRARY[crop_code]
            planted_ratio = float(rng.uniform(0.92, 1.0))
            planted_hectares = round(float(lot["net_hectares"]) * planted_ratio, 1)
            rows.append(
                {
                    "lote_campania_id": f"LC_{sequence:05d}",
                    "lote_id": lot["lote_id"],
                    "campania_id": campaign["campania_id"],
                    "producto_id": _product_id(crop["product_code"]),
                    "crop_code": crop_code,
                    "sown_hectares": planted_hectares,
                    "expected_yield_tn_ha": round(float(crop["yield_tn_ha"]) * float(lot["soil_productivity_index"]) * float(campaign["campaign_weather_factor"]), 2),
                }
            )
            sequence += 1
    return frame(rows)


def _generate_clients(config: SimulationConfig, rng: np.random.Generator) -> pd.DataFrame:
    names = [
        "Acopio Los Ceibos",
        "Molino Central",
        "NutriFeed",
        "Exportadora del Sur",
        "Agroinsumos del Centro",
        "Cooperativa San Miguel",
        "Granos del NOA",
        "Procesadora Andina",
    ]
    product_preferences = ["MAIZ_GRANO", "TRIGO_GRANO", "MAIZ_GRANO", "SOJA_GRANO", "TRIGO_GRANO", "SOJA_GRANO", "MAIZ_GRANO", "SOJA_GRANO"]
    payment_terms_by_client = {
        "Acopio Los Ceibos": 60,
        "Molino Central": 30,
        "NutriFeed": 45,
        "Exportadora del Sur": 75,
        "Agroinsumos del Centro": 30,
        "Cooperativa San Miguel": 60,
        "Granos del NOA": 60,
        "Procesadora Andina": 75,
    }
    rows: list[dict[str, object]] = []
    for index in range(config.num_clients):
        client_name = names[index % len(names)]
        rows.append(
            {
                "cliente_id": f"CLI_{index + 1:04d}",
                "client_name": client_name,
                "condicion_iva_id": "IVA_0001",
                "preferred_product_code": product_preferences[index % len(product_preferences)],
                "payment_term_days": payment_terms_by_client[client_name],
            }
        )
    return frame(rows)


def _generate_suppliers(config: SimulationConfig, rng: np.random.Generator) -> pd.DataFrame:
    names = [
        ("SeedCorp", "SEMILLA"),
        ("FertiNorte", "FERTILIZANTE"),
        ("Protec Agro", "FITOSANITARIO"),
        ("Combustibles Ruta", "COMBUSTIBLE"),
        ("Taller Metal", "REPUESTO"),
        ("Logistica Pampeana", "SERVICIO"),
        ("Servicios Integrales", "SERVICIO"),
        ("AgroCentro", "SEMILLA"),
        ("Quimicos del Sur", "FITOSANITARIO"),
        ("Repuestos Argentinos", "REPUESTO"),
    ]
    payment_terms_by_supplier = {
        "SeedCorp": 45,
        "FertiNorte": 45,
        "Protec Agro": 45,
        "Combustibles Ruta": 60,
        "Taller Metal": 30,
        "Logistica Pampeana": 45,
        "Servicios Integrales": 45,
        "AgroCentro": 45,
        "Quimicos del Sur": 45,
        "Repuestos Argentinos": 30,
    }
    rows: list[dict[str, object]] = []
    for index in range(config.num_suppliers):
        name, specialty = names[index % len(names)]
        rows.append(
            {
                "proveedor_id": f"SUP_{index + 1:04d}",
                "supplier_name": name,
                "condicion_iva_id": "IVA_0001",
                "supplier_group": specialty,
                "payment_term_days": payment_terms_by_supplier[name],
            }
        )
    return frame(rows)


def _generate_employees(
    config: SimulationConfig,
    rng: np.random.Generator,
    payroll_categories: pd.DataFrame,
) -> pd.DataFrame:
    first_names = ["Juan", "Maria", "Pedro", "Lucia", "Diego", "Carla", "Martin", "Sofia", "Pablo", "Valeria"]
    last_names = ["Gomez", "Suarez", "Lopez", "Rojas", "Diaz", "Paz", "Sosa", "Luna", "Quiroga", "Mendez"]
    cost_center_map = {
        "OPER_CAMPO": "CC_0001",
        "MECANICO": "CC_0003",
        "CHOFER": "CC_0002",
        "ADMIN": "CC_0004",
        "COMERCIAL": "CC_0005",
        "SUPERVISOR": "CC_0001",
    }
    rows: list[dict[str, object]] = []
    category_ids = payroll_categories["categoria_rrhh_id"].tolist()
    category_codes = payroll_categories["category_code"].tolist()
    for index in range(config.num_employees):
        category_code = weighted_choice(category_codes, [0.35, 0.12, 0.14, 0.18, 0.11, 0.10], rng)
        category_id = payroll_categories.loc[payroll_categories["category_code"] == category_code, "categoria_rrhh_id"].iloc[0]
        rows.append(
            {
                "empleado_id": f"EMPLO_{index + 1:04d}",
                "empresa_id": "EMP_0001",
                "employee_name": f"{first_names[index % len(first_names)]} {last_names[(index * 3) % len(last_names)]}",
                "categoria_rrhh_id": category_id,
                "category_code": category_code,
                "centro_costo_id": cost_center_map[category_code],
                "hire_date": add_days(date(2022, 1, 1), int(rng.integers(0, 900))),
                "status": "ACTIVO",
            }
        )
    return frame(rows)


def _generate_assets(config: SimulationConfig, rng: np.random.Generator) -> pd.DataFrame:
    asset_templates = [
        ("Tractor 150", "TRACTOR", "CC_0001"),
        ("Tractor 190", "TRACTOR", "CC_0001"),
        ("Pulverizadora 01", "PULVERIZADORA", "CC_0001"),
        ("Cosechadora 01", "COSECHADORA", "CC_0001"),
        ("Cosechadora 02", "COSECHADORA", "CC_0001"),
        ("Camion 01", "CAMION", "CC_0002"),
        ("Camion 02", "CAMION", "CC_0002"),
        ("Taller movil", "MOVIL_TECNICO", "CC_0003"),
    ]
    rows: list[dict[str, object]] = []
    for index in range(min(config.num_assets, len(asset_templates))):
        asset_name, asset_type, cost_center_id = asset_templates[index]
        rows.append(
            {
                "activo_id": f"ACT_{index + 1:04d}",
                "establecimiento_id": "EST_0001" if index < 5 else "EST_0002",
                "asset_name": asset_name,
                "asset_type": asset_type,
                "centro_costo_id": cost_center_id,
                "maintenance_cycle_days": int(rng.choice([30, 45, 60], p=[0.3, 0.5, 0.2])),
            }
        )
    return frame(rows)


def _generate_transporters() -> pd.DataFrame:
    return frame(
        [
            {"transportista_id": "TRP_0001", "transporter_name": "Logistica Pampeana", "mode": "TERCERO"},
            {"transportista_id": "TRP_0002", "transporter_name": "Camiones del Norte", "mode": "TERCERO"},
            {"transportista_id": "TRP_0003", "transporter_name": "Flota Propia", "mode": "PROPIO"},
        ]
    )


def _generate_chart_of_accounts() -> pd.DataFrame:
    rows = [
        ("CTA_0001", "1.1.01", "Caja y Bancos", "ACTIVO"),
        ("CTA_0002", "1.1.02", "Cuentas por Cobrar", "ACTIVO"),
        ("CTA_0003", "1.1.03", "IVA Credito Fiscal", "ACTIVO"),
        ("CTA_0004", "1.1.04", "Inventario Insumos", "ACTIVO"),
        ("CTA_0005", "1.1.05", "Inventario Granos", "ACTIVO"),
        ("CTA_0006", "2.1.01", "Cuentas por Pagar", "PASIVO"),
        ("CTA_0007", "2.1.02", "IVA Debito Fiscal", "PASIVO"),
        ("CTA_0008", "2.1.03", "Sueldos a Pagar", "PASIVO"),
        ("CTA_0009", "2.1.04", "Cargas Sociales a Pagar", "PASIVO"),
        ("CTA_0010", "4.1.01", "Ventas de Granos", "RESULTADO"),
        ("CTA_0011", "5.1.01", "Costo de Ventas", "RESULTADO"),
        ("CTA_0012", "5.1.02", "Gasto Salarial", "RESULTADO"),
        ("CTA_0013", "5.1.03", "Gasto Mantenimiento", "RESULTADO"),
        ("CTA_0014", "5.1.04", "Gasto Logistico", "RESULTADO"),
        ("CTA_0015", "5.1.05", "Gasto Administrativo", "RESULTADO"),
        ("CTA_0016", "5.1.06", "Impuestos y Tasas", "RESULTADO"),
    ]
    return frame(
        [
            {
                "cuenta_contable_id": account_id,
                "account_code": account_code,
                "account_name": account_name,
                "account_group": account_group,
            }
            for account_id, account_code, account_name, account_group in rows
        ]
    )


def _product_id(product_code: str) -> str:
    match = next(product for product in PRODUCT_LIBRARY if product["product_code"] == product_code)
    return f"PROD_{PRODUCT_LIBRARY.index(match) + 1:04d}"
