from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta

from app.models.empresa import Empresa
from app.models.campania import Campania
from app.models.cultivo import Cultivo
from app.models.cliente import Cliente
from app.models.producto import Producto
from app.models.venta import Venta
from app.models.contrato import Contrato
from app.models.stock import Stock
from app.models.establecimiento import Establecimiento
from app.seed.campaign_utils import build_campaign_template_map, shift_date_years


async def seed_comercial(db: AsyncSession):
    empresas = (await db.execute(select(Empresa))).scalars().all()
    campanias = (await db.execute(select(Campania).order_by(Campania.fecha_inicio))).scalars().all()
    cultivos = (await db.execute(select(Cultivo))).scalars().all()
    clientes = (await db.execute(select(Cliente))).scalars().all()
    productos = (await db.execute(select(Producto))).scalars().all()
    ests = (await db.execute(select(Establecimiento))).scalars().all()

    emp_map = {e.nombre: e for e in empresas}
    camp_map = {c.nombre: c for c in campanias}
    cult_map = {c.nombre: c for c in cultivos}
    cli_list = clientes
    prod_map = {p.nombre: p for p in productos}

    emp1 = emp_map["El Progreso SA"]
    emp2 = emp_map["Agropecuaria Del Sur SRL"]
    campaign_name_map, year_delta = build_campaign_template_map(date.today())

    # ---- Precios historicos ARS/tn por campania (inflacion argentina) ----
    # Campaña 2022/23: dolar a ~$200, soja ~$70k/tn, maiz ~$35k/tn
    # Campaña 2023/24: dolar a ~$500-800, soja ~$200-300k/tn
    # Campaña 2024/25: dolar a ~$900, soja ~$252k/tn

    precios_soja = {
        "2022/2023": [68000, 72000, 75000, 78000, 82000],
        "2023/2024": [195000, 210000, 225000, 240000, 258000],
        "2024/2025": [248000, 255000, 262000, 270000, 252000],
    }
    precios_maiz = {
        "2022/2023": [32000, 34000, 36000, 38000, 35000],
        "2023/2024": [110000, 125000, 138000, 148000, 155000],
        "2024/2025": [145000, 150000, 155000, 149000, 152000],
    }
    precios_trigo = {
        "2022/2023": [42000, 45000, 48000, 50000, 47000],
        "2023/2024": [145000, 158000, 165000, 172000, 168000],
        "2024/2025": [180000, 185000, 188000, 192000, 188000],
    }
    precios_girasol = {
        "2022/2023": [95000, 100000, 105000, 110000, 102000],
        "2023/2024": [265000, 280000, 295000, 310000, 300000],
        "2024/2025": [325000, 335000, 342000, 337000, 330000],
    }
    precios_sorgo = {
        "2022/2023": [25000, 27000, 29000, 28000, 26000],
        "2023/2024": [90000, 100000, 110000, 108000, 115000],
        "2024/2025": [118000, 122000, 125000, 120000, 118000],
    }

    def get_precio(cultivo_nombre, campania_nombre, idx):
        precio_maps = {
            "Soja": precios_soja,
            "Maiz": precios_maiz,
            "Trigo": precios_trigo,
            "Girasol": precios_girasol,
            "Sorgo": precios_sorgo,
        }
        precios = precio_maps.get(cultivo_nombre, precios_soja)
        lista = precios.get(campania_nombre, [200000])
        return lista[idx % len(lista)]

    ventas = []

    # ---- Ventas Empresa 1 - Campañas 2022/23 y 2023/24 ----
    ventas_data_e1 = [
        # (campania, cultivo_nombre, cliente_idx, fecha, volumen)
        # 2022/2023
        ("2022/2023", "Soja", 0, date(2023, 5, 10), 320),
        ("2022/2023", "Soja", 1, date(2023, 5, 25), 280),
        ("2022/2023", "Soja", 3, date(2023, 6, 8), 150),
        ("2022/2023", "Maiz", 2, date(2023, 4, 15), 450),
        ("2022/2023", "Maiz", 0, date(2023, 4, 28), 380),
        ("2022/2023", "Girasol", 4, date(2023, 2, 20), 180),
        ("2022/2023", "Girasol", 5, date(2023, 3, 5), 210),
        ("2022/2023", "Trigo", 4, date(2022, 12, 15), 280),
        ("2022/2023", "Trigo", 3, date(2023, 1, 10), 320),
        ("2022/2023", "Sorgo", 2, date(2023, 3, 20), 150),
        # 2023/2024
        ("2023/2024", "Soja", 0, date(2024, 4, 12), 420),
        ("2023/2024", "Soja", 1, date(2024, 4, 25), 380),
        ("2023/2024", "Soja", 7, date(2024, 5, 8), 250),
        ("2023/2024", "Soja", 3, date(2024, 5, 20), 300),
        ("2023/2024", "Maiz", 2, date(2024, 4, 5), 520),
        ("2023/2024", "Maiz", 0, date(2024, 3, 28), 480),
        ("2023/2024", "Maiz", 6, date(2024, 4, 18), 360),
        ("2023/2024", "Trigo", 4, date(2023, 12, 10), 350),
        ("2023/2024", "Trigo", 5, date(2024, 1, 15), 280),
        ("2023/2024", "Girasol", 8, date(2024, 2, 28), 220),
        ("2023/2024", "Girasol", 4, date(2024, 3, 12), 180),
        # 2024/2025 (parcial)
        ("2024/2025", "Trigo", 4, date(2024, 12, 5), 320),
        ("2024/2025", "Trigo", 3, date(2024, 12, 18), 280),
        ("2024/2025", "Girasol", 8, date(2025, 2, 18), 165),
        ("2024/2025", "Maiz", 0, date(2025, 3, 12), 240),
        ("2024/2025", "Soja", 1, date(2025, 3, 19), 110),
    ]

    for camp_nombre, cult_nombre, cli_idx, fecha, volumen in ventas_data_e1:
        mapped_campaign_name = campaign_name_map.get(camp_nombre, camp_nombre)
        camp = camp_map.get(mapped_campaign_name)
        cult = cult_map.get(cult_nombre)
        cli = cli_list[cli_idx % len(cli_list)]
        prod = prod_map.get(cult_nombre)
        if not all([camp, cult, cli, prod]):
            continue
        precio = get_precio(cult_nombre, camp_nombre, cli_idx)
        total = precio * volumen
        fecha_real = shift_date_years(fecha, year_delta)
        venta = Venta(
            empresa_id=emp1.id,
            producto_id=prod.id,
            cliente_id=cli.id,
            campania_id=camp.id,
            fecha=fecha_real,
            volumen=volumen,
            precio_tn=precio,
            total=total,
            estado="entregada" if fecha_real <= date.today() else "confirmada",
        )
        ventas.append(venta)

    # ---- Ventas Empresa 2 ----
    ventas_data_e2 = [
        ("2022/2023", "Soja", 1, date(2023, 5, 5), 380),
        ("2022/2023", "Soja", 9, date(2023, 5, 18), 250),
        ("2022/2023", "Maiz", 0, date(2023, 4, 10), 480),
        ("2022/2023", "Maiz", 2, date(2023, 4, 22), 420),
        ("2022/2023", "Girasol", 5, date(2023, 2, 25), 190),
        ("2022/2023", "Sorgo", 6, date(2023, 3, 15), 200),
        ("2023/2024", "Soja", 0, date(2024, 4, 8), 450),
        ("2023/2024", "Soja", 1, date(2024, 4, 20), 420),
        ("2023/2024", "Soja", 7, date(2024, 5, 5), 280),
        ("2023/2024", "Maiz", 2, date(2024, 3, 25), 560),
        ("2023/2024", "Maiz", 0, date(2024, 4, 8), 480),
        ("2023/2024", "Girasol", 5, date(2024, 2, 20), 250),
        ("2023/2024", "Trigo", 4, date(2023, 12, 5), 300),
        ("2023/2024", "Sorgo", 8, date(2024, 3, 18), 180),
        ("2024/2025", "Trigo", 3, date(2024, 12, 8), 295),
        ("2024/2025", "Trigo", 4, date(2024, 12, 20), 250),
        ("2024/2025", "Girasol", 5, date(2025, 2, 14), 180),
        ("2024/2025", "Maiz", 2, date(2025, 3, 10), 265),
        ("2024/2025", "Soja", 7, date(2025, 3, 17), 125),
    ]

    for camp_nombre, cult_nombre, cli_idx, fecha, volumen in ventas_data_e2:
        mapped_campaign_name = campaign_name_map.get(camp_nombre, camp_nombre)
        camp = camp_map.get(mapped_campaign_name)
        cult = cult_map.get(cult_nombre)
        cli = cli_list[cli_idx % len(cli_list)]
        prod = prod_map.get(cult_nombre)
        if not all([camp, cult, cli, prod]):
            continue
        precio = get_precio(cult_nombre, camp_nombre, cli_idx + 2)
        total = precio * volumen
        fecha_real = shift_date_years(fecha, year_delta)
        venta = Venta(
            empresa_id=emp2.id,
            producto_id=prod.id,
            cliente_id=cli.id,
            campania_id=camp.id,
            fecha=fecha_real,
            volumen=volumen,
            precio_tn=precio,
            total=total,
            estado="entregada" if fecha_real <= date.today() else "confirmada",
        )
        ventas.append(venta)

    db.add_all(ventas)
    await db.flush()

    # ---- Contratos ----
    contratos = []
    contratos_data = [
        # (empresa, campania, cultivo, cliente_idx, volumen, precio_fijado, precio_a_fijar, dias_entrega, estado)
        (emp1.id, "2024/2025", "Soja", 0, 800, 255000, None, 25, "vigente"),
        (emp1.id, "2024/2025", "Soja", 1, 600, None, 248000, 55, "vigente"),
        (emp1.id, "2024/2025", "Maiz", 2, 1000, 150000, None, 18, "vigente"),
        (emp1.id, "2024/2025", "Maiz", 0, 500, None, 145000, 75, "vigente"),
        (emp1.id, "2023/2024", "Soja", 3, 700, 235000, None, 0, "cumplido"),
        (emp1.id, "2023/2024", "Maiz", 0, 800, 148000, None, 0, "cumplido"),
        (emp2.id, "2024/2025", "Soja", 1, 900, 258000, None, 22, "vigente"),
        (emp2.id, "2024/2025", "Soja", 7, 700, None, 252000, 48, "vigente"),
        (emp2.id, "2024/2025", "Maiz", 2, 1100, 152000, None, 14, "vigente"),
        (emp2.id, "2023/2024", "Girasol", 5, 400, 295000, None, 0, "cumplido"),
        (emp2.id, "2023/2024", "Soja", 0, 850, 240000, None, 0, "cumplido"),
        (emp1.id, "2025/2026", "Trigo", 4, 420, None, 192000, 190, "vigente"),
        (emp1.id, "2025/2026", "Soja", 1, 780, None, 252000, 240, "vigente"),
        (emp2.id, "2025/2026", "Maiz", 2, 860, None, 152000, 210, "vigente"),
        (emp2.id, "2025/2026", "Girasol", 5, 280, None, 335000, 165, "vigente"),
    ]

    for emp_id, camp_nombre, cult_nombre, cli_idx, vol, p_fijado, p_a_fijar, dias_entrega, estado in contratos_data:
        mapped_campaign_name = campaign_name_map.get(camp_nombre, camp_nombre)
        camp = camp_map.get(mapped_campaign_name)
        cult = cult_map.get(cult_nombre)
        cli = cli_list[cli_idx % len(cli_list)]
        if not all([camp, cult, cli]):
            continue
        fecha_entrega = (
            date.today() + timedelta(days=dias_entrega)
            if dias_entrega > 0
            else min(camp.fecha_fin - timedelta(days=30), date.today() - timedelta(days=20))
        )
        contrato = Contrato(
            empresa_id=emp_id,
            cultivo_id=cult.id,
            cliente_id=cli.id,
            campania_id=camp.id,
            volumen_contratado=vol,
            precio_fijado=p_fijado,
            precio_a_fijar=p_a_fijar,
            fecha_entrega=fecha_entrega,
            estado=estado,
        )
        contratos.append(contrato)

    db.add_all(contratos)
    await db.flush()

    # ---- Stock ----
    stocks = []
    prod_soja = prod_map.get("Soja")
    prod_maiz = prod_map.get("Maiz")
    prod_trigo = prod_map.get("Trigo")
    prod_girasol = prod_map.get("Girasol")
    prod_sorgo = prod_map.get("Sorgo")

    ests_e1 = [e for e in ests if e.empresa_id == emp1.id]
    ests_e2 = [e for e in ests if e.empresa_id == emp2.id]

    stock_configs_e1 = [
        (ests_e1[0], prod_soja, 450, 320, 200),
        (ests_e1[0], prod_maiz, 280, 450, 150),
        (ests_e1[1], prod_soja, 680, 380, 300),
        (ests_e1[1], prod_maiz, 520, 480, 200),
        (ests_e1[1], prod_girasol, 210, 180, 100),
        (ests_e1[2], prod_soja, 320, 280, 120),
        (ests_e1[2], prod_maiz, 380, 220, 180),
        (ests_e1[3], prod_soja, 280, 150, 130),
        (ests_e1[3], prod_trigo, 250, 350, 80),
    ]

    stock_configs_e2 = [
        (ests_e2[0], prod_soja, 520, 300, 250),
        (ests_e2[0], prod_maiz, 420, 480, 180),
        (ests_e2[0], prod_girasol, 190, 150, 90),
        (ests_e2[1], prod_soja, 380, 280, 200),
        (ests_e2[1], prod_sorgo, 200, 180, 80),
        (ests_e2[2], prod_soja, 480, 350, 220),
        (ests_e2[2], prod_maiz, 550, 480, 300),
        (ests_e2[2], prod_girasol, 250, 250, 120),
        (ests_e2[3], prod_soja, 320, 200, 150),
        (ests_e2[3], prod_trigo, 200, 300, 60),
        (ests_e2[4], prod_soja, 280, 220, 120),
        (ests_e2[4], prod_sorgo, 180, 180, 80),
    ]

    from datetime import datetime
    for configs in [stock_configs_e1, stock_configs_e2]:
        for est, prod, disponible, vendido, comprometido in configs:
            if not prod:
                continue
            stocks.append(Stock(
                establecimiento_id=est.id,
                producto_id=prod.id,
                volumen_disponible=disponible,
                volumen_vendido=vendido,
                volumen_comprometido=comprometido,
                fecha_actualizacion=datetime.utcnow(),
            ))

    db.add_all(stocks)
    await db.flush()
