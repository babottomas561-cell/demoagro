from __future__ import annotations

import sqlite3
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_sqlite_path() -> Path:
    return project_root() / "data" / "demoagro.sqlite"


def ensure_parent_dir(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)


def connect_sqlite(
    db_path: str | Path | None = None,
    *,
    foreign_keys: bool = True,
) -> sqlite3.Connection:
    resolved_path = Path(db_path) if db_path else default_sqlite_path()
    ensure_parent_dir(resolved_path)
    connection = sqlite3.connect(resolved_path)
    connection.execute(f"PRAGMA foreign_keys = {'ON' if foreign_keys else 'OFF'};")
    connection.execute("PRAGMA journal_mode = WAL;")
    return connection
