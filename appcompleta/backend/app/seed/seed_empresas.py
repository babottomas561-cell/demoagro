import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.models.empresa import Empresa
from app.models.establecimiento import Establecimiento
from app.models.campania import Campania
from app.models.cultivo import Cultivo
from app.models.cliente import Cliente
from app.models.proveedor import Proveedor
from app.models.producto import Producto
from app.models.insumo import Insumo
from app.models.usuario import Usuario
from app.seed.campaign_utils import campaign_name, current_campaign_start_year


def hash_password(pwd: str) -> str:
    """Hash password for seed data using bcrypt if available, sha256 fallback."""
    try:
        from passlib.context import CryptContext
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return ctx.hash(pwd)
    except Exception:
        salt = "demoagro_fixed_salt_2024"
        digest = hashlib.sha256(f"{salt}:{pwd}".encode()).hexdigest()
        # Return a fake bcrypt-format hash - only used for demo seed data
        return f"$2b$12${digest[:22]}{digest[22:75]}"


async def seed_empresas(db: AsyncSession):
    # ---- Empresas ----
    empresa1 = Empresa(
        nombre="El Progreso SA",
        cuit="30-71234567-8",
        razon_social="El Progreso Sociedad Anonima",
        tipo="SA",
        activa=True,
    )
    empresa2 = Empresa(
        nombre="Agropecuaria Del Sur SRL",
        cuit="30-68901234-5",
        razon_social="Agropecuaria Del Sur Sociedad de Responsabilidad Limitada",
        tipo="SRL",
        activa=True,
    )
    db.add_all([empresa1, empresa2])
    await db.flush()

    # ---- Establecimientos Empresa 1 (El Progreso SA) ----
    # Zona: Sur de Córdoba / Norte de Buenos Aires
    establecimientos_e1 = [
        Establecimiento(
            empresa_id=empresa1.id,
            nombre="El Progreso - Lote Norte",
            ubicacion="Ruta 9 km 350, Marcos Juarez",
            provincia="Córdoba",
            lat=-32.6989,
            lon=-62.1059,
            hectareas_totales=850.0,
        ),
        Establecimiento(
            empresa_id=empresa1.id,
            nombre="El Progreso - Lote Sur",
            ubicacion="Acceso Est. Las Maravillas, Venado Tuerto",
            provincia="Santa Fe",
            lat=-33.7450,
            lon=-61.9645,
            hectareas_totales=1200.0,
        ),
        Establecimiento(
            empresa_id=empresa1.id,
            nombre="El Progreso - Campo Pampeano",
            ubicacion="Ruta 188 km 45, General Villegas",
            provincia="Buenos Aires",
            lat=-34.9890,
            lon=-62.9994,
            hectareas_totales=680.0,
        ),
        Establecimiento(
            empresa_id=empresa1.id,
            nombre="El Progreso - Est. La Esperanza",
            ubicacion="Camino vecinal km 12, Las Rosas",
            provincia="Santa Fe",
            lat=-32.4780,
            lon=-61.5730,
            hectareas_totales=520.0,
        ),
    ]
    db.add_all(establecimientos_e1)

    # ---- Establecimientos Empresa 2 (Agropecuaria Del Sur) ----
    # Zona: Sud de Buenos Aires / La Pampa
    establecimientos_e2 = [
        Establecimiento(
            empresa_id=empresa2.id,
            nombre="Del Sur - Est. San Carlos",
            ubicacion="Ruta 33 km 120, Trenque Lauquen",
            provincia="Buenos Aires",
            lat=-35.9710,
            lon=-62.7260,
            hectareas_totales=960.0,
        ),
        Establecimiento(
            empresa_id=empresa2.id,
            nombre="Del Sur - Campo Meridional",
            ubicacion="Acceso s/n, Pehuajo",
            provincia="Buenos Aires",
            lat=-35.8103,
            lon=-61.8952,
            hectareas_totales=750.0,
        ),
        Establecimiento(
            empresa_id=empresa2.id,
            nombre="Del Sur - La Pampa Norte",
            ubicacion="Ruta 35 km 220, Santa Rosa",
            provincia="La Pampa",
            lat=-36.6188,
            lon=-64.2912,
            hectareas_totales=1100.0,
        ),
        Establecimiento(
            empresa_id=empresa2.id,
            nombre="Del Sur - Est. El Amanecer",
            ubicacion="Camino vecinal km 8, Henderson",
            provincia="Buenos Aires",
            lat=-36.2978,
            lon=-61.7168,
            hectareas_totales=430.0,
        ),
        Establecimiento(
            empresa_id=empresa2.id,
            nombre="Del Sur - Loma Negra",
            ubicacion="Ruta 60 km 90, Coronel Suarez",
            provincia="Buenos Aires",
            lat=-37.4600,
            lon=-61.9370,
            hectareas_totales=580.0,
        ),
    ]
    db.add_all(establecimientos_e2)
    await db.flush()

    # ---- Campañas ----
    current_start_year = current_campaign_start_year(date.today())
    campaign_years = [
        current_start_year - 2,
        current_start_year - 1,
        current_start_year,
        current_start_year + 1,
    ]
    campanias = [
        Campania(
            nombre=campaign_name(start_year),
            fecha_inicio=date(start_year, 7, 1),
            fecha_fin=date(start_year + 1, 6, 30),
            activa=start_year == current_start_year,
        )
        for start_year in campaign_years
    ]
    db.add_all(campanias)
    await db.flush()

    # ---- Cultivos ----
    cultivos = [
        Cultivo(nombre="Soja", unidad="tn"),
        Cultivo(nombre="Maiz", unidad="tn"),
        Cultivo(nombre="Trigo", unidad="tn"),
        Cultivo(nombre="Girasol", unidad="tn"),
        Cultivo(nombre="Sorgo", unidad="tn"),
    ]
    db.add_all(cultivos)
    await db.flush()

    # ---- Clientes ----
    clientes = [
        Cliente(nombre="Bunge Argentina SA", cuit="30-51417559-0", provincia="Buenos Aires", tipo="exportador"),
        Cliente(nombre="Cargill SACI", cuit="30-50029514-7", provincia="Buenos Aires", tipo="exportador"),
        Cliente(nombre="LDC Argentina SA", cuit="30-70920421-7", provincia="Buenos Aires", tipo="exportador"),
        Cliente(nombre="Cooperativa Agraria de Las Rosas", cuit="30-53012345-1", provincia="Santa Fe", tipo="cooperativa"),
        Cliente(nombre="Molinos Rio de la Plata", cuit="30-50009616-8", provincia="Buenos Aires", tipo="molino"),
        Cliente(nombre="Aceitera General Deheza", cuit="30-50001122-3", provincia="Córdoba", tipo="industria"),
        Cliente(nombre="Acopio Fernandez Hermanos", cuit="20-18765432-6", provincia="Córdoba", tipo="acopio"),
        Cliente(nombre="Vicentin SAIC", cuit="30-56543210-9", provincia="Santa Fe", tipo="exportador"),
        Cliente(nombre="Oleaginosa Moreno", cuit="30-52876543-2", provincia="Santa Fe", tipo="industria"),
        Cliente(nombre="Cooperativa El Progreso Ltda", cuit="30-54312876-4", provincia="Buenos Aires", tipo="cooperativa"),
    ]
    db.add_all(clientes)
    await db.flush()

    # ---- Proveedores ----
    proveedores = [
        Proveedor(nombre="Monsanto Argentina", cuit="30-68901234-1", tipo="insumos"),
        Proveedor(nombre="Agro Norte SA", cuit="30-71234500-2", tipo="insumos"),
        Proveedor(nombre="John Deere Argentina", cuit="30-53456789-3", tipo="maquinaria"),
        Proveedor(nombre="Contratista Rural Gimenez", cuit="20-25678901-4", tipo="servicios"),
        Proveedor(nombre="YPF Agro", cuit="30-54667812-5", tipo="insumos"),
        Proveedor(nombre="Syngenta Argentina", cuit="30-69012345-6", tipo="insumos"),
    ]
    db.add_all(proveedores)
    await db.flush()

    # ---- Productos (relacionados a cultivos) ----
    # Fetch cultivos para relacionar
    from sqlalchemy import select
    from app.models.cultivo import Cultivo as CultivoModel
    cult_result = await db.execute(select(CultivoModel))
    cult_list = cult_result.scalars().all()
    cult_map = {c.nombre: c.id for c in cult_list}

    # Precios en ARS/tn (referencia 2024, con inflacion)
    productos = [
        Producto(nombre="Soja", cultivo_id=cult_map["Soja"], unidad="tn", precio_referencia=252000),
        Producto(nombre="Maiz", cultivo_id=cult_map["Maiz"], unidad="tn", precio_referencia=149000),
        Producto(nombre="Trigo", cultivo_id=cult_map["Trigo"], unidad="tn", precio_referencia=188000),
        Producto(nombre="Girasol", cultivo_id=cult_map["Girasol"], unidad="tn", precio_referencia=337000),
        Producto(nombre="Sorgo", cultivo_id=cult_map["Sorgo"], unidad="tn", precio_referencia=120000),
        Producto(nombre="Soja Premium", cultivo_id=cult_map["Soja"], unidad="tn", precio_referencia=265000),
        Producto(nombre="Maiz Pisingallo", cultivo_id=cult_map["Maiz"], unidad="tn", precio_referencia=175000),
    ]
    db.add_all(productos)
    await db.flush()

    # ---- Insumos ----
    insumos = [
        Insumo(nombre="Roundup (Glifosato 48%)", tipo="herbicida", unidad="lt", precio_unitario=1850),
        Insumo(nombre="2,4-D Amina 72%", tipo="herbicida", unidad="lt", precio_unitario=2100),
        Insumo(nombre="Atrazina 90%", tipo="herbicida", unidad="kg", precio_unitario=3200),
        Insumo(nombre="Carbendazim + Tebuconazol", tipo="fungicida", unidad="lt", precio_unitario=8500),
        Insumo(nombre="Azoxistrobina + Ciproconazol", tipo="fungicida", unidad="lt", precio_unitario=12000),
        Insumo(nombre="Urea Granulada", tipo="fertilizante", unidad="tn", precio_unitario=520000),
        Insumo(nombre="MAP (Monoamonio Fosfato)", tipo="fertilizante", unidad="tn", precio_unitario=680000),
        Insumo(nombre="UAN Solucion 32%", tipo="fertilizante", unidad="lt", precio_unitario=280),
        Insumo(nombre="Soja RR1 Intacta", tipo="semilla", unidad="kg", precio_unitario=5200),
        Insumo(nombre="Maiz DK 7010 VT3P", tipo="semilla", unidad="bolsa", precio_unitario=48000),
        Insumo(nombre="Trigo Klein Liebre", tipo="semilla", unidad="kg", precio_unitario=1850),
        Insumo(nombre="Girasol Paraiso 20", tipo="semilla", unidad="bolsa", precio_unitario=36000),
        Insumo(nombre="Sorgo Hib. EM Pampa", tipo="semilla", unidad="bolsa", precio_unitario=22000),
        Insumo(nombre="Gas Oil", tipo="combustible", unidad="lt", precio_unitario=980),
        Insumo(nombre="Aceite Motor 15W40", tipo="combustible", unidad="lt", precio_unitario=4500),
    ]
    db.add_all(insumos)
    await db.flush()

    # ---- Usuarios ----
    usuarios = [
        Usuario(
            empresa_id=empresa1.id,
            nombre="Admin Sistema",
            email="admin@demoagro.com",
            hashed_password=hash_password("admin123"),
            rol="admin",
            activo=True,
        ),
        Usuario(
            empresa_id=empresa1.id,
            nombre="Juan Fernandez",
            email="jfernandez@elprogreso.com",
            hashed_password=hash_password("progreso123"),
            rol="gerente",
            activo=True,
        ),
        Usuario(
            empresa_id=empresa1.id,
            nombre="Maria Lopez",
            email="mlopez@elprogreso.com",
            hashed_password=hash_password("progreso123"),
            rol="operativo",
            activo=True,
        ),
        Usuario(
            empresa_id=empresa2.id,
            nombre="Carlos Rodriguez",
            email="crodriguez@agrodelsur.com",
            hashed_password=hash_password("delsur123"),
            rol="gerente",
            activo=True,
        ),
        Usuario(
            empresa_id=empresa2.id,
            nombre="Ana Martinez",
            email="amartinez@agrodelsur.com",
            hashed_password=hash_password("delsur123"),
            rol="operativo",
            activo=True,
        ),
    ]
    db.add_all(usuarios)
    await db.flush()
