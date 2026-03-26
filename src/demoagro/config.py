from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SimulationConfig:
    company_name: str = "Demoagro SA"
    currency_code: str = "USD"
    seed: int = 42
    active_campaign_start_year: int = 2024
    campaign_count: int = 2
    num_lots: int = 12
    num_clients: int = 8
    num_suppliers: int = 10
    num_employees: int = 24
    num_assets: int = 8
    sale_ratio_min: float = 0.72
    sale_ratio_max: float = 0.92
    default_vat_rate: float = 0.21
    employer_contrib_rate: float = 0.24
    employee_deduction_rate: float = 0.17
    crop_mix: dict[str, float] = field(
        default_factory=lambda: {"MAIZ": 0.35, "SOJA": 0.4, "TRIGO": 0.25}
    )

    @property
    def active_campaign_label(self) -> str:
        next_year = self.active_campaign_start_year + 1
        return f"{self.active_campaign_start_year}/{next_year}"


CROP_LIBRARY: dict[str, dict[str, object]] = {
    "MAIZ": {
        "product_code": "MAIZ_GRANO",
        "display_name": "Maiz",
        "yield_tn_ha": 8.7,
        "yield_sd": 1.2,
        "sale_price": 205.0,
        "seed_code": "SEM_MAIZ",
        "input_rates": {
            "SEM_MAIZ": 22.0,
            "UREA": 180.0,
            "MAP": 90.0,
            "GLIFOSATO": 2.1,
            "INSECTICIDA": 0.35,
        },
        "sow_month": 9,
        "fert_month": 11,
        "spray_months": [12, 1],
        "harvest_month": 4,
        "labor_costs": {
            "SIEMBRA": 48.0,
            "FERTILIZACION": 22.0,
            "PULVERIZACION": 18.0,
            "COSECHA": 62.0,
        },
    },
    "SOJA": {
        "product_code": "SOJA_GRANO",
        "display_name": "Soja",
        "yield_tn_ha": 3.2,
        "yield_sd": 0.45,
        "sale_price": 315.0,
        "seed_code": "SEM_SOJA",
        "input_rates": {
            "SEM_SOJA": 70.0,
            "MAP": 55.0,
            "GLIFOSATO": 2.6,
            "INSECTICIDA": 0.28,
        },
        "sow_month": 11,
        "fert_month": 12,
        "spray_months": [1, 2],
        "harvest_month": 5,
        "labor_costs": {
            "SIEMBRA": 38.0,
            "FERTILIZACION": 16.0,
            "PULVERIZACION": 18.0,
            "COSECHA": 52.0,
        },
    },
    "TRIGO": {
        "product_code": "TRIGO_GRANO",
        "display_name": "Trigo",
        "yield_tn_ha": 4.4,
        "yield_sd": 0.6,
        "sale_price": 225.0,
        "seed_code": "SEM_TRIGO",
        "input_rates": {
            "SEM_TRIGO": 140.0,
            "UREA": 130.0,
            "MAP": 70.0,
            "FUNGICIDA": 0.45,
        },
        "sow_month": 6,
        "fert_month": 8,
        "spray_months": [9, 10],
        "harvest_month": 12,
        "labor_costs": {
            "SIEMBRA": 34.0,
            "FERTILIZACION": 18.0,
            "PULVERIZACION": 17.0,
            "COSECHA": 49.0,
        },
    },
}


PRODUCT_LIBRARY: list[dict[str, object]] = [
    {
        "product_code": "MAIZ_GRANO",
        "product_name": "Maiz Grano",
        "category_code": "GRANO",
        "uom_code": "TN",
        "standard_cost": 138.0,
        "standard_price": 205.0,
    },
    {
        "product_code": "SOJA_GRANO",
        "product_name": "Soja Grano",
        "category_code": "GRANO",
        "uom_code": "TN",
        "standard_cost": 212.0,
        "standard_price": 315.0,
    },
    {
        "product_code": "TRIGO_GRANO",
        "product_name": "Trigo Grano",
        "category_code": "GRANO",
        "uom_code": "TN",
        "standard_cost": 152.0,
        "standard_price": 225.0,
    },
    {
        "product_code": "SEM_MAIZ",
        "product_name": "Semilla de Maiz",
        "category_code": "SEMILLA",
        "uom_code": "KG",
        "standard_cost": 4.8,
        "standard_price": 6.2,
    },
    {
        "product_code": "SEM_SOJA",
        "product_name": "Semilla de Soja",
        "category_code": "SEMILLA",
        "uom_code": "KG",
        "standard_cost": 1.25,
        "standard_price": 1.8,
    },
    {
        "product_code": "SEM_TRIGO",
        "product_name": "Semilla de Trigo",
        "category_code": "SEMILLA",
        "uom_code": "KG",
        "standard_cost": 0.72,
        "standard_price": 1.1,
    },
    {
        "product_code": "UREA",
        "product_name": "Urea",
        "category_code": "FERTILIZANTE",
        "uom_code": "KG",
        "standard_cost": 0.62,
        "standard_price": 0.85,
    },
    {
        "product_code": "MAP",
        "product_name": "MAP",
        "category_code": "FERTILIZANTE",
        "uom_code": "KG",
        "standard_cost": 0.74,
        "standard_price": 0.96,
    },
    {
        "product_code": "GLIFOSATO",
        "product_name": "Glifosato",
        "category_code": "FITOSANITARIO",
        "uom_code": "LT",
        "standard_cost": 6.2,
        "standard_price": 7.9,
    },
    {
        "product_code": "INSECTICIDA",
        "product_name": "Insecticida",
        "category_code": "FITOSANITARIO",
        "uom_code": "LT",
        "standard_cost": 18.0,
        "standard_price": 22.0,
    },
    {
        "product_code": "FUNGICIDA",
        "product_name": "Fungicida",
        "category_code": "FITOSANITARIO",
        "uom_code": "LT",
        "standard_cost": 21.0,
        "standard_price": 25.0,
    },
    {
        "product_code": "GASOIL",
        "product_name": "Gasoil",
        "category_code": "COMBUSTIBLE",
        "uom_code": "LT",
        "standard_cost": 1.15,
        "standard_price": 1.35,
    },
    {
        "product_code": "FILTRO_ACEITE",
        "product_name": "Filtro de Aceite",
        "category_code": "REPUESTO",
        "uom_code": "UN",
        "standard_cost": 15.0,
        "standard_price": 20.0,
    },
    {
        "product_code": "RODAMIENTO",
        "product_name": "Rodamiento",
        "category_code": "REPUESTO",
        "uom_code": "UN",
        "standard_cost": 42.0,
        "standard_price": 58.0,
    },
    {
        "product_code": "CORREA",
        "product_name": "Correa",
        "category_code": "REPUESTO",
        "uom_code": "UN",
        "standard_cost": 26.0,
        "standard_price": 35.0,
    },
    {
        "product_code": "SERV_TALLER",
        "product_name": "Servicio de Taller",
        "category_code": "SERVICIO",
        "uom_code": "HR",
        "standard_cost": 38.0,
        "standard_price": 50.0,
    },
    {
        "product_code": "FLETE_TERCERIZADO",
        "product_name": "Flete Tercerizado",
        "category_code": "SERVICIO",
        "uom_code": "TN",
        "standard_cost": 14.0,
        "standard_price": 18.0,
    },
]


PAYROLL_CATEGORIES: list[dict[str, object]] = [
    {"category_code": "OPER_CAMPO", "category_name": "Operario de Campo", "base_salary": 1250.0},
    {"category_code": "MECANICO", "category_name": "Mecanico", "base_salary": 1450.0},
    {"category_code": "CHOFER", "category_name": "Chofer", "base_salary": 1380.0},
    {"category_code": "ADMIN", "category_name": "Administracion", "base_salary": 1180.0},
    {"category_code": "COMERCIAL", "category_name": "Comercial", "base_salary": 1420.0},
    {"category_code": "SUPERVISOR", "category_name": "Supervisor", "base_salary": 1820.0},
]

