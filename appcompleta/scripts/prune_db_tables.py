#!/usr/bin/env python3
"""
Deja la base SQLite solo con el esquema activo de Lemon BI.

- hace backup del archivo actual
- migra `usuarios` para desacoplarla del FK legado a `empresas`
- elimina tablas fuera del set activo
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "backend" / "demoagro.db"
BACKUP_PATH = ROOT / "backend" / f"demoagro.db.pre_prune_{datetime.now().strftime('%Y%m%d_%H%M%S')}.backup"

KEEP_TABLES = {
    "usuarios",
    "empresa_dim",
    "campania_dim",
    "establecimiento_dim",
    "campo_dim",
    "lote_dim",
    "variedad_dim",
    "cliente_dim",
    "mercado_dim",
    "canal_dim",
    "destino_fruta_dim",
    "calibre_dim",
    "defecto_dim",
    "linea_empaque_dim",
    "turno_dim",
    "plaga_dim",
    "enfermedad_dim",
    "deposito_dim",
    "fecha_dim",
    "lote_campania_fact",
    "cosecha_fact",
    "rendimiento_lote_fact",
    "rendimiento_ambiente_fact",
    "scouting_fact",
    "aplicacion_fitosanitaria_fact",
    "riego_fact",
    "fertirriego_fact",
    "requerimiento_hidrico_fact",
    "et0_fact",
    "recepcion_fruta_fact",
    "clasificacion_calidad_fact",
    "packout_fact",
    "rechazo_fact",
    "packhouse_turno_fact",
    "downtime_packhouse_fact",
    "mano_obra_packhouse_fact",
    "consumo_packhouse_fact",
    "mantenimiento_packhouse_fact",
    "contrato_venta_fact",
    "embarque_fact",
    "precio_venta_fact",
    "liquidacion_fact",
    "stock_final_fact",
    "presupuesto_lote_fact",
    "costos_directos_fact",
    "costos_indirectos_fact",
    "cuentas_cobrar_fact",
    "cobranzas_fact",
    "clima_diario_fact",
    "macro_series_fact",
    "tipo_cambio_fact",
    "precio_exportacion_fact",
    "costo_energia_fact",
    "costo_flete_fact",
}


def existing_tables(conn: sqlite3.Connection) -> list[str]:
    return [
        row[0]
        for row in conn.execute(
            "select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name"
        ).fetchall()
    ]


def _hash_password(password: str) -> str:
    import bcrypt

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def rebuild_users(conn: sqlite3.Connection) -> None:
    tables = set(existing_tables(conn))
    if "usuarios" not in tables:
        return

    conn.execute("drop table if exists usuarios_new")
    conn.execute(
        """
        create table if not exists usuarios_new (
            id integer primary key,
            empresa_id integer,
            nombre varchar(200) not null,
            email varchar(200) not null unique,
            hashed_password varchar(300) not null,
            rol varchar(50) not null,
            activo boolean not null,
            created_at datetime not null,
            updated_at datetime not null
        )
        """
    )
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    users = [
        (1, 1, "Admin Lemon BI", "admin@demoagro.com", _hash_password("admin123"), "admin", 1, now, now),
        (2, 1, "Gerencia Lemon BI", "gerencia@lemonbi.com", _hash_password("gerencia123"), "gerente", 1, now, now),
        (3, 1, "Operaciones Lemon BI", "operaciones@lemonbi.com", _hash_password("operaciones123"), "operativo", 1, now, now),
    ]
    conn.executemany(
        """
        insert into usuarios_new (id, empresa_id, nombre, email, hashed_password, rol, activo, created_at, updated_at)
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        users,
    )
    conn.execute("drop table usuarios")
    conn.execute("alter table usuarios_new rename to usuarios")
    conn.execute("create unique index if not exists ix_usuarios_email on usuarios(email)")
    conn.execute("create index if not exists ix_usuarios_id on usuarios(id)")
    conn.execute("create index if not exists ix_usuarios_empresa_id on usuarios(empresa_id)")


def main() -> int:
    if not DB_PATH.exists():
        raise SystemExit(f"No existe la base: {DB_PATH}")

    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"Backup creado: {BACKUP_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("pragma foreign_keys=off")
        rebuild_users(conn)

        current = existing_tables(conn)
        drop_tables = [name for name in current if name not in KEEP_TABLES]
        for table in drop_tables:
            conn.execute(f'drop table if exists "{table}"')

        conn.commit()
        conn.execute("vacuum")
        print(f"Tablas conservadas: {len(KEEP_TABLES)}")
        print(f"Tablas eliminadas: {len(drop_tables)}")
        for table in drop_tables:
            print(f" - {table}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
