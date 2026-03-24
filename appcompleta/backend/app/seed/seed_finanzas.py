from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta
import calendar

from app.models.empresa import Empresa
from app.models.campania import Campania
from app.models.flujo_financiero import FlujoCaja
from app.seed.campaign_utils import build_campaign_template_map, shift_date_years


async def seed_finanzas(db: AsyncSession):
    empresas = (await db.execute(select(Empresa))).scalars().all()
    campanias = (await db.execute(select(Campania).order_by(Campania.fecha_inicio))).scalars().all()

    emp_map = {e.nombre: e for e in empresas}
    camp_map = {c.nombre: c for c in campanias}

    emp1 = emp_map["El Progreso SA"]
    emp2 = emp_map["Agropecuaria Del Sur SRL"]
    campaign_name_map, year_delta = build_campaign_template_map(date.today())
    camp_2223 = camp_map[campaign_name_map["2022/2023"]]
    camp_2324 = camp_map[campaign_name_map["2023/2024"]]
    camp_2425 = camp_map[campaign_name_map["2024/2025"]]

    flujos = []

    # ---- Generar flujo de caja mensual para 24 meses ----
    # El flujo refleja la estacionalidad agricola argentina:
    # - Jul-Nov: gastos de siembra (insumos, labores)
    # - Dic-Mar: cosecha y ventas de verano (soja, maiz)
    # - Abr-Jun: ventas de invierno (trigo)

    def make_flujos_empresa(empresa, meses_config):
        result = []
        for camp, year_start, month_ranges in meses_config:
            for mes_offset, (mes_num, ingresos_items, egresos_items) in enumerate(month_ranges):
                year = year_start + (1 if mes_num < month_ranges[0][0] and mes_offset > 0 else 0)
                # Simple approach: use absolute dates
                pass
        return result

    # Flujos para Empresa 1 (El Progreso SA) - 24 meses 2022-2024
    flujos_e1 = [
        # Campaña 2022/2023
        # Jul 2022 - Siembra de cultivos de invierno
        (emp1.id, camp_2223.id, date(2022, 7, 10), "egreso", "Compra semillas trigo Klein", 8500000, "insumos"),
        (emp1.id, camp_2223.id, date(2022, 7, 15), "egreso", "Labores siembra trigo - lote norte y sur", 12000000, "labores"),
        (emp1.id, camp_2223.id, date(2022, 7, 20), "egreso", "Gas oil agosto campana", 3800000, "insumos"),
        (emp1.id, camp_2223.id, date(2022, 7, 25), "egreso", "Salarios julio", 5200000, "salarios"),
        (emp1.id, camp_2223.id, date(2022, 7, 28), "egreso", "Alquiler campos adicionales", 4500000, "alquiler"),
        # Ago 2022
        (emp1.id, camp_2223.id, date(2022, 8, 5), "egreso", "Fertilizante MAP trigo", 15000000, "insumos"),
        (emp1.id, camp_2223.id, date(2022, 8, 10), "egreso", "Fumigacion trigo", 5500000, "labores"),
        (emp1.id, camp_2223.id, date(2022, 8, 25), "egreso", "Salarios agosto", 5200000, "salarios"),
        (emp1.id, None, date(2022, 8, 28), "ingreso", "Anticipos credito BNA campaña", 35000000, "credito"),
        # Sep 2022
        (emp1.id, camp_2223.id, date(2022, 9, 8), "egreso", "Compra semillas soja y maiz", 28000000, "insumos"),
        (emp1.id, camp_2223.id, date(2022, 9, 12), "egreso", "Compra herbicidas glifosato", 18000000, "insumos"),
        (emp1.id, camp_2223.id, date(2022, 9, 25), "egreso", "Salarios septiembre", 5200000, "salarios"),
        (emp1.id, None, date(2022, 9, 28), "egreso", "Anticipo impuesto a las ganancias", 8000000, "impuesto"),
        # Oct 2022
        (emp1.id, camp_2223.id, date(2022, 10, 5), "egreso", "Labores siembra maiz", 22000000, "labores"),
        (emp1.id, camp_2223.id, date(2022, 10, 10), "egreso", "Gas oil octubre", 5200000, "insumos"),
        (emp1.id, camp_2223.id, date(2022, 10, 20), "egreso", "Fumigacion herbicida maiz", 8500000, "labores"),
        (emp1.id, camp_2223.id, date(2022, 10, 25), "egreso", "Salarios octubre", 5500000, "salarios"),
        # Nov 2022
        (emp1.id, camp_2223.id, date(2022, 11, 3), "egreso", "Labores siembra soja", 28000000, "labores"),
        (emp1.id, camp_2223.id, date(2022, 11, 8), "egreso", "Fertilizante urea soja", 22000000, "insumos"),
        (emp1.id, camp_2223.id, date(2022, 11, 25), "egreso", "Salarios noviembre", 5500000, "salarios"),
        (emp1.id, None, date(2022, 11, 28), "egreso", "IVA compras insumos", 6000000, "impuesto"),
        # Dic 2022 - Cosecha trigo
        (emp1.id, camp_2223.id, date(2022, 12, 5), "ingreso", "Venta trigo - Molinos Rio de la Plata", 67200000, "venta"),
        (emp1.id, camp_2223.id, date(2022, 12, 8), "ingreso", "Venta trigo - Cooperativa Las Rosas", 57600000, "venta"),
        (emp1.id, camp_2223.id, date(2022, 12, 10), "egreso", "Labores cosecha trigo contratista", 18000000, "labores"),
        (emp1.id, camp_2223.id, date(2022, 12, 20), "egreso", "Flete cosecha trigo", 8500000, "labores"),
        (emp1.id, camp_2223.id, date(2022, 12, 25), "egreso", "Salarios diciembre + aguinaldo", 10500000, "salarios"),
        (emp1.id, None, date(2022, 12, 28), "egreso", "Impuesto bienes personales", 5500000, "impuesto"),
        # Ene 2023
        (emp1.id, camp_2223.id, date(2023, 1, 8), "egreso", "Fumigacion soja segunda aplicacion", 12000000, "labores"),
        (emp1.id, camp_2223.id, date(2023, 1, 12), "egreso", "Fungicida soja", 18500000, "insumos"),
        (emp1.id, camp_2223.id, date(2023, 1, 25), "egreso", "Salarios enero", 5800000, "salarios"),
        (emp1.id, None, date(2023, 1, 28), "egreso", "Cuota seguro campo", 4200000, "otro"),
        # Feb 2023 - Cosecha girasol
        (emp1.id, camp_2223.id, date(2023, 2, 10), "ingreso", "Venta girasol - Aceitera G. Deheza", 78750000, "venta"),
        (emp1.id, camp_2223.id, date(2023, 2, 15), "ingreso", "Venta girasol - Oleaginosa Moreno", 64260000, "venta"),
        (emp1.id, camp_2223.id, date(2023, 2, 18), "egreso", "Cosecha girasol contratista", 16000000, "labores"),
        (emp1.id, camp_2223.id, date(2023, 2, 25), "egreso", "Salarios febrero", 5800000, "salarios"),
        # Mar 2023
        (emp1.id, camp_2223.id, date(2023, 3, 10), "egreso", "Fungicida segunda aplicacion maiz", 14000000, "insumos"),
        (emp1.id, camp_2223.id, date(2023, 3, 20), "ingreso", "Venta sorgo - LDC Argentina", 40500000, "venta"),
        (emp1.id, camp_2223.id, date(2023, 3, 25), "egreso", "Salarios marzo", 6000000, "salarios"),
        (emp1.id, None, date(2023, 3, 28), "egreso", "IVA trimestral", 7500000, "impuesto"),
        # Abr 2023 - Cosecha maiz
        (emp1.id, camp_2223.id, date(2023, 4, 5), "ingreso", "Venta maiz - Bunge Argentina", 148500000, "venta"),
        (emp1.id, camp_2223.id, date(2023, 4, 10), "ingreso", "Venta maiz - LDC Argentina", 126000000, "venta"),
        (emp1.id, camp_2223.id, date(2023, 4, 15), "egreso", "Cosecha maiz - contratista Rodriguez", 32000000, "labores"),
        (emp1.id, camp_2223.id, date(2023, 4, 20), "egreso", "Flete maiz a puerto", 18000000, "labores"),
        (emp1.id, camp_2223.id, date(2023, 4, 25), "egreso", "Salarios abril", 6000000, "salarios"),
        (emp1.id, None, date(2023, 4, 28), "egreso", "Cuota prestamo banco", 12000000, "credito"),
        # May 2023 - Cosecha soja
        (emp1.id, camp_2223.id, date(2023, 5, 5), "ingreso", "Venta soja - Bunge Argentina", 156800000, "venta"),
        (emp1.id, camp_2223.id, date(2023, 5, 10), "ingreso", "Venta soja - Cargill SACI", 136000000, "venta"),
        (emp1.id, camp_2223.id, date(2023, 5, 15), "ingreso", "Venta soja - Cooperativa Las Rosas", 72750000, "venta"),
        (emp1.id, camp_2223.id, date(2023, 5, 18), "egreso", "Cosecha soja - contratista", 38000000, "labores"),
        (emp1.id, camp_2223.id, date(2023, 5, 22), "egreso", "Flete soja a acopio", 22000000, "labores"),
        (emp1.id, camp_2223.id, date(2023, 5, 25), "egreso", "Salarios mayo", 6200000, "salarios"),
        (emp1.id, None, date(2023, 5, 28), "egreso", "Impuesto a las ganancias 2do pago", 18000000, "impuesto"),
        # Jun 2023
        (emp1.id, camp_2223.id, date(2023, 6, 5), "ingreso", "Venta soja restante - Vicentin", 78750000, "venta"),
        (emp1.id, camp_2223.id, date(2023, 6, 25), "egreso", "Salarios junio + aguinaldo", 11500000, "salarios"),
        (emp1.id, None, date(2023, 6, 28), "egreso", "Ingresos brutos anual", 8000000, "impuesto"),

        # CAMPAÑA 2023/2024 - precios mas altos por inflacion
        # Jul 2023
        (emp1.id, camp_2324.id, date(2023, 7, 10), "egreso", "Compra semillas trigo campaña 2023/24", 22000000, "insumos"),
        (emp1.id, camp_2324.id, date(2023, 7, 15), "egreso", "Labores siembra trigo", 32000000, "labores"),
        (emp1.id, camp_2324.id, date(2023, 7, 20), "egreso", "Gas oil julio 2023", 9800000, "insumos"),
        (emp1.id, camp_2324.id, date(2023, 7, 25), "egreso", "Salarios julio 2023", 12500000, "salarios"),
        (emp1.id, camp_2324.id, date(2023, 7, 28), "egreso", "Alquiler campos", 11000000, "alquiler"),
        # Ago 2023
        (emp1.id, camp_2324.id, date(2023, 8, 5), "egreso", "Fertilizante MAP trigo 2023/24", 38000000, "insumos"),
        (emp1.id, camp_2324.id, date(2023, 8, 10), "egreso", "Fumigacion trigo 2023/24", 14500000, "labores"),
        (emp1.id, camp_2324.id, date(2023, 8, 25), "egreso", "Salarios agosto 2023", 12500000, "salarios"),
        (emp1.id, None, date(2023, 8, 28), "ingreso", "Credito BNA campaña 2023/24", 90000000, "credito"),
        # Sep 2023
        (emp1.id, camp_2324.id, date(2023, 9, 8), "egreso", "Compra semillas soja y maiz 2023/24", 72000000, "insumos"),
        (emp1.id, camp_2324.id, date(2023, 9, 12), "egreso", "Herbicidas glifosato", 45000000, "insumos"),
        (emp1.id, camp_2324.id, date(2023, 9, 25), "egreso", "Salarios septiembre 2023", 13000000, "salarios"),
        # Oct 2023
        (emp1.id, camp_2324.id, date(2023, 10, 5), "egreso", "Labores siembra maiz 2023/24", 58000000, "labores"),
        (emp1.id, camp_2324.id, date(2023, 10, 20), "egreso", "Fumigacion herbicida maiz", 22000000, "labores"),
        (emp1.id, camp_2324.id, date(2023, 10, 25), "egreso", "Salarios octubre 2023", 13500000, "salarios"),
        # Nov 2023
        (emp1.id, camp_2324.id, date(2023, 11, 3), "egreso", "Labores siembra soja 2023/24", 75000000, "labores"),
        (emp1.id, camp_2324.id, date(2023, 11, 8), "egreso", "Fertilizante urea soja", 58000000, "insumos"),
        (emp1.id, camp_2324.id, date(2023, 11, 25), "egreso", "Salarios noviembre 2023", 14000000, "salarios"),
        # Dic 2023 - Cosecha trigo 2023/24
        (emp1.id, camp_2324.id, date(2023, 12, 5), "ingreso", "Venta trigo - Molinos R. Plata", 181650000, "venta"),
        (emp1.id, camp_2324.id, date(2023, 12, 8), "ingreso", "Venta trigo - Cooperativa Las Rosas", 145600000, "venta"),
        (emp1.id, camp_2324.id, date(2023, 12, 15), "egreso", "Cosecha trigo contratista", 46000000, "labores"),
        (emp1.id, camp_2324.id, date(2023, 12, 25), "egreso", "Salarios diciembre + aguinaldo 2023", 27000000, "salarios"),
        # Ene 2024
        (emp1.id, camp_2324.id, date(2024, 1, 8), "egreso", "Fungicida soja segunda aplicacion", 32000000, "insumos"),
        (emp1.id, camp_2324.id, date(2024, 1, 25), "egreso", "Salarios enero 2024", 15000000, "salarios"),
        # Feb 2024 - Girasol
        (emp1.id, camp_2324.id, date(2024, 2, 10), "ingreso", "Venta girasol - Aceitera G. Deheza", 213500000, "venta"),
        (emp1.id, camp_2324.id, date(2024, 2, 20), "egreso", "Cosecha girasol", 42000000, "labores"),
        (emp1.id, camp_2324.id, date(2024, 2, 25), "egreso", "Salarios febrero 2024", 15500000, "salarios"),
        # Mar 2024
        (emp1.id, camp_2324.id, date(2024, 3, 15), "egreso", "Impuesto a ganancias 2023", 45000000, "impuesto"),
        (emp1.id, camp_2324.id, date(2024, 3, 25), "egreso", "Salarios marzo 2024", 16000000, "salarios"),
        # Abr 2024 - Cosecha maiz
        (emp1.id, camp_2324.id, date(2024, 4, 5), "ingreso", "Venta maiz - Bunge Argentina", 398400000, "venta"),
        (emp1.id, camp_2324.id, date(2024, 4, 10), "ingreso", "Venta maiz - LDC Argentina", 358400000, "venta"),
        (emp1.id, camp_2324.id, date(2024, 4, 15), "egreso", "Cosecha maiz contratista", 85000000, "labores"),
        (emp1.id, camp_2324.id, date(2024, 4, 25), "egreso", "Salarios abril 2024", 16500000, "salarios"),
        # May 2024 - Cosecha soja
        (emp1.id, camp_2324.id, date(2024, 5, 5), "ingreso", "Venta soja - Bunge Argentina", 426600000, "venta"),
        (emp1.id, camp_2324.id, date(2024, 5, 8), "ingreso", "Venta soja - Cargill SACI", 384000000, "venta"),
        (emp1.id, camp_2324.id, date(2024, 5, 12), "ingreso", "Venta soja - Vicentin SAIC", 258000000, "venta"),
        (emp1.id, camp_2324.id, date(2024, 5, 15), "egreso", "Cosecha soja contratista", 105000000, "labores"),
        (emp1.id, camp_2324.id, date(2024, 5, 25), "egreso", "Salarios mayo 2024", 17000000, "salarios"),
        (emp1.id, None, date(2024, 5, 28), "egreso", "Cancelacion credito BNA", 90000000, "credito"),
        # Jun 2024
        (emp1.id, camp_2324.id, date(2024, 6, 5), "ingreso", "Venta soja restante - Cooperativa", 213750000, "venta"),
        (emp1.id, camp_2324.id, date(2024, 6, 25), "egreso", "Salarios junio + aguinaldo 2024", 34000000, "salarios"),
        (emp1.id, None, date(2024, 6, 28), "egreso", "Ingresos brutos 2024", 22000000, "impuesto"),

        # CAMPAÑA 2024/2025 (parcial - primer semestre)
        # Jul 2024
        (emp1.id, camp_2425.id, date(2024, 7, 10), "egreso", "Semillas trigo campaña 2024/25", 38000000, "insumos"),
        (emp1.id, camp_2425.id, date(2024, 7, 15), "egreso", "Labores siembra trigo 2024/25", 55000000, "labores"),
        (emp1.id, camp_2425.id, date(2024, 7, 25), "egreso", "Salarios julio 2024", 19000000, "salarios"),
        (emp1.id, camp_2425.id, date(2024, 7, 28), "egreso", "Alquiler campos 2024/25", 18500000, "alquiler"),
        # Ago 2024
        (emp1.id, camp_2425.id, date(2024, 8, 5), "egreso", "Fertilizante MAP trigo 2024/25", 65000000, "insumos"),
        (emp1.id, camp_2425.id, date(2024, 8, 25), "egreso", "Salarios agosto 2024", 19500000, "salarios"),
        (emp1.id, None, date(2024, 8, 28), "ingreso", "Credito BNA campaña 2024/25", 150000000, "credito"),
        # Sep 2024
        (emp1.id, camp_2425.id, date(2024, 9, 8), "egreso", "Semillas soja y maiz 2024/25", 125000000, "insumos"),
        (emp1.id, camp_2425.id, date(2024, 9, 12), "egreso", "Herbicidas campaña 2024/25", 78000000, "insumos"),
        (emp1.id, camp_2425.id, date(2024, 9, 25), "egreso", "Salarios septiembre 2024", 20000000, "salarios"),
        # Oct 2024
        (emp1.id, camp_2425.id, date(2024, 10, 5), "egreso", "Labores siembra maiz 2024/25", 95000000, "labores"),
        (emp1.id, camp_2425.id, date(2024, 10, 25), "egreso", "Salarios octubre 2024", 20500000, "salarios"),
        # Nov 2024
        (emp1.id, camp_2425.id, date(2024, 11, 3), "egreso", "Labores siembra soja 2024/25", 128000000, "labores"),
        (emp1.id, camp_2425.id, date(2024, 11, 8), "egreso", "Fertilizante urea 2024/25", 98000000, "insumos"),
        (emp1.id, camp_2425.id, date(2024, 11, 25), "egreso", "Salarios noviembre 2024", 21000000, "salarios"),
        # Dic 2024 - Cosecha trigo 2024/25
        (emp1.id, camp_2425.id, date(2024, 12, 5), "ingreso", "Venta trigo - Molinos R. Plata 24/25", 285120000, "venta"),
        (emp1.id, camp_2425.id, date(2024, 12, 10), "ingreso", "Venta trigo - Cooperativa El Progreso", 238000000, "venta"),
        (emp1.id, camp_2425.id, date(2024, 12, 18), "egreso", "Cosecha trigo contratista 2024/25", 72000000, "labores"),
        (emp1.id, camp_2425.id, date(2024, 12, 25), "egreso", "Salarios diciembre + aguinaldo 2024", 42000000, "salarios"),
        (emp1.id, camp_2425.id, date(2025, 1, 12), "egreso", "Fungicida soja 2024/25", 54000000, "insumos"),
        (emp1.id, camp_2425.id, date(2025, 1, 25), "egreso", "Salarios enero 2025", 22500000, "salarios"),
        (emp1.id, camp_2425.id, date(2025, 2, 18), "ingreso", "Venta girasol 2024/25 - AGD", 64000000, "venta"),
        (emp1.id, camp_2425.id, date(2025, 2, 21), "egreso", "Cosecha girasol 2024/25", 34000000, "labores"),
        (emp1.id, camp_2425.id, date(2025, 2, 25), "egreso", "Salarios febrero 2025", 22500000, "salarios"),
        (emp1.id, camp_2425.id, date(2025, 3, 12), "ingreso", "Venta maiz temprano 2024/25", 171600000, "venta"),
        (emp1.id, camp_2425.id, date(2025, 3, 15), "egreso", "Cosecha maiz temprano 2024/25", 52000000, "labores"),
        (emp1.id, camp_2425.id, date(2025, 3, 20), "ingreso", "Anticipo soja disponible 2024/25", 74800000, "venta"),
        (emp1.id, camp_2425.id, date(2025, 3, 25), "egreso", "Salarios marzo 2025", 23500000, "salarios"),
    ]

    # Flujos para Empresa 2 (proporcional, 60% del volumen)
    flujos_e2_base = [
        (emp2.id, camp_2223.id, date(2022, 7, 12), "egreso", "Insumos siembra trigo", 9500000, "insumos"),
        (emp2.id, camp_2223.id, date(2022, 7, 25), "egreso", "Salarios julio", 4800000, "salarios"),
        (emp2.id, camp_2223.id, date(2022, 8, 8), "egreso", "Fertilizantes trigo", 16000000, "insumos"),
        (emp2.id, camp_2223.id, date(2022, 8, 28), "ingreso", "Anticipo credito Banco Nacion", 28000000, "credito"),
        (emp2.id, camp_2223.id, date(2022, 9, 10), "egreso", "Semillas soja y maiz", 25000000, "insumos"),
        (emp2.id, camp_2223.id, date(2022, 9, 15), "egreso", "Herbicidas glifosato", 16000000, "insumos"),
        (emp2.id, camp_2223.id, date(2022, 10, 8), "egreso", "Labores siembra maiz", 20000000, "labores"),
        (emp2.id, camp_2223.id, date(2022, 11, 5), "egreso", "Labores siembra soja", 25000000, "labores"),
        (emp2.id, camp_2223.id, date(2022, 12, 8), "ingreso", "Venta trigo cooperativa", 52500000, "venta"),
        (emp2.id, camp_2223.id, date(2023, 2, 12), "ingreso", "Venta girasol industria", 68250000, "venta"),
        (emp2.id, camp_2223.id, date(2023, 3, 20), "ingreso", "Venta sorgo", 36000000, "venta"),
        (emp2.id, camp_2223.id, date(2023, 4, 8), "ingreso", "Venta maiz - Bunge", 134400000, "venta"),
        (emp2.id, camp_2223.id, date(2023, 4, 18), "ingreso", "Venta maiz - LDC", 116400000, "venta"),
        (emp2.id, camp_2223.id, date(2023, 4, 22), "egreso", "Cosecha maiz contratista", 28000000, "labores"),
        (emp2.id, camp_2223.id, date(2023, 5, 8), "ingreso", "Venta soja - Bunge", 138600000, "venta"),
        (emp2.id, camp_2223.id, date(2023, 5, 15), "ingreso", "Venta soja - Cargill", 114750000, "venta"),
        (emp2.id, camp_2223.id, date(2023, 5, 20), "egreso", "Cosecha soja contratista", 34000000, "labores"),
        (emp2.id, camp_2223.id, date(2023, 6, 8), "ingreso", "Venta soja restante", 68250000, "venta"),
        # 2023/2024
        (emp2.id, camp_2324.id, date(2023, 7, 12), "egreso", "Insumos siembra 2023/24", 24000000, "insumos"),
        (emp2.id, camp_2324.id, date(2023, 8, 5), "egreso", "Fertilizantes 2023/24", 42000000, "insumos"),
        (emp2.id, camp_2324.id, date(2023, 8, 28), "ingreso", "Credito campaña 2023/24", 75000000, "credito"),
        (emp2.id, camp_2324.id, date(2023, 9, 10), "egreso", "Semillas soja y maiz 2023/24", 65000000, "insumos"),
        (emp2.id, camp_2324.id, date(2023, 10, 8), "egreso", "Labores siembra maiz 2023/24", 52000000, "labores"),
        (emp2.id, camp_2324.id, date(2023, 11, 5), "egreso", "Labores siembra soja 2023/24", 68000000, "labores"),
        (emp2.id, camp_2324.id, date(2023, 12, 8), "ingreso", "Venta trigo 2023/24 - Molinos", 157500000, "venta"),
        (emp2.id, camp_2324.id, date(2024, 2, 12), "ingreso", "Venta girasol 2023/24", 193750000, "venta"),
        (emp2.id, camp_2324.id, date(2024, 3, 20), "ingreso", "Venta sorgo 2023/24", 108000000, "venta"),
        (emp2.id, camp_2324.id, date(2024, 4, 8), "ingreso", "Venta maiz 2023/24 - Bunge", 358400000, "venta"),
        (emp2.id, camp_2324.id, date(2024, 4, 18), "ingreso", "Venta maiz 2023/24 - LDC", 326400000, "venta"),
        (emp2.id, camp_2324.id, date(2024, 4, 22), "egreso", "Cosecha maiz contratista 2023/24", 76000000, "labores"),
        (emp2.id, camp_2324.id, date(2024, 5, 8), "ingreso", "Venta soja 2023/24 - Bunge", 385200000, "venta"),
        (emp2.id, camp_2324.id, date(2024, 5, 15), "ingreso", "Venta soja 2023/24 - Cargill", 352800000, "venta"),
        (emp2.id, camp_2324.id, date(2024, 5, 20), "egreso", "Cosecha soja contratista 2023/24", 95000000, "labores"),
        (emp2.id, camp_2324.id, date(2024, 5, 28), "egreso", "Cancelacion credito BNA", 75000000, "credito"),
        (emp2.id, camp_2324.id, date(2024, 6, 8), "ingreso", "Venta soja restante 2023/24", 196350000, "venta"),
        # 2024/2025
        (emp2.id, camp_2425.id, date(2024, 7, 12), "egreso", "Insumos siembra 2024/25", 42000000, "insumos"),
        (emp2.id, camp_2425.id, date(2024, 8, 5), "egreso", "Fertilizantes 2024/25", 72000000, "insumos"),
        (emp2.id, camp_2425.id, date(2024, 8, 28), "ingreso", "Credito campaña 2024/25", 130000000, "credito"),
        (emp2.id, camp_2425.id, date(2024, 9, 10), "egreso", "Semillas soja y maiz 2024/25", 112000000, "insumos"),
        (emp2.id, camp_2425.id, date(2024, 10, 8), "egreso", "Labores siembra maiz 2024/25", 88000000, "labores"),
        (emp2.id, camp_2425.id, date(2024, 11, 5), "egreso", "Labores siembra soja 2024/25", 115000000, "labores"),
        (emp2.id, camp_2425.id, date(2024, 12, 8), "ingreso", "Venta trigo 2024/25 - Molinos", 250250000, "venta"),
        (emp2.id, camp_2425.id, date(2024, 12, 20), "ingreso", "Venta trigo 2024/25 - Cooperativa", 212500000, "venta"),
        (emp2.id, camp_2425.id, date(2025, 1, 14), "egreso", "Fungicida soja 2024/25", 47000000, "insumos"),
        (emp2.id, camp_2425.id, date(2025, 1, 26), "egreso", "Salarios enero 2025", 19800000, "salarios"),
        (emp2.id, camp_2425.id, date(2025, 2, 14), "ingreso", "Venta girasol 2024/25", 72000000, "venta"),
        (emp2.id, camp_2425.id, date(2025, 2, 19), "egreso", "Cosecha girasol 2024/25", 36000000, "labores"),
        (emp2.id, camp_2425.id, date(2025, 2, 26), "egreso", "Salarios febrero 2025", 20400000, "salarios"),
        (emp2.id, camp_2425.id, date(2025, 3, 10), "ingreso", "Venta maiz temprano 2024/25", 188500000, "venta"),
        (emp2.id, camp_2425.id, date(2025, 3, 15), "egreso", "Cosecha maiz temprano 2024/25", 54000000, "labores"),
        (emp2.id, camp_2425.id, date(2025, 3, 24), "egreso", "Salarios marzo 2025", 20800000, "salarios"),
    ]

    all_flujos_data = flujos_e1 + flujos_e2_base

    for (emp_id, camp_id, fecha, tipo, concepto, monto, categoria) in all_flujos_data:
        flujo = FlujoCaja(
            empresa_id=emp_id,
            campania_id=camp_id,
            fecha=shift_date_years(fecha, year_delta),
            tipo=tipo,
            concepto=concepto,
            monto=float(monto),
            categoria=categoria,
        )
        flujos.append(flujo)

    db.add_all(flujos)
    await db.flush()
