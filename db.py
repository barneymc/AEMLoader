"""
db.py — MS SQL Server token cache (read/write aem_token_cache table).
        Not called when AEM_MOCK_MODE=true.
"""
import logging
from datetime import datetime, timezone

import pyodbc

from config import Config

log = logging.getLogger(__name__)


def _connect(cfg: Config):
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={cfg.db_server};"
        f"DATABASE={cfg.db_name};"
        f"UID={cfg.db_user};"
        f"PWD={cfg.db_password};"
    )
    try:
        return pyodbc.connect(conn_str)
    except pyodbc.Error as e:
        log.error(f"[DB] Connection failed: {e}")
        raise SystemExit(1)


def ensure_table(cfg: Config) -> None:
    """Create the token cache table if it does not already exist."""
    sql = f"""
        IF NOT EXISTS (
            SELECT * FROM sysobjects
            WHERE name = '{cfg.db_table}' AND xtype = 'U'
        )
        CREATE TABLE {cfg.db_table} (
            id           INT           PRIMARY KEY DEFAULT 1,
            access_token NVARCHAR(MAX) NOT NULL,
            expires_at   DATETIME2     NOT NULL,
            created_at   DATETIME2     DEFAULT GETDATE()
        )
    """
    conn = _connect(cfg)
    try:
        conn.execute(sql)
        conn.commit()
    except pyodbc.Error as e:
        log.error(f"[DB] Failed to create token table: {e}")
        raise SystemExit(1)
    finally:
        conn.close()


def load_token(cfg: Config) -> tuple[str | None, datetime | None]:
    """Return (access_token, expires_at) from cache, or (None, None) if empty."""
    conn = _connect(cfg)
    try:
        row = conn.execute(
            f"SELECT access_token, expires_at FROM {cfg.db_table} WHERE id = 1"
        ).fetchone()
        if row:
            return row[0], row[1]
        return None, None
    except pyodbc.Error as e:
        log.error(f"[DB] Failed to load token: {e}")
        raise SystemExit(1)
    finally:
        conn.close()


def save_token(cfg: Config, access_token: str, expires_at: datetime) -> None:
    """Upsert the token record (single-row cache, id = 1)."""
    conn = _connect(cfg)
    try:
        conn.execute(
            f"""
            MERGE {cfg.db_table} AS target
            USING (SELECT 1 AS id) AS src ON target.id = src.id
            WHEN MATCHED THEN
                UPDATE SET access_token = ?, expires_at = ?, created_at = GETDATE()
            WHEN NOT MATCHED THEN
                INSERT (id, access_token, expires_at) VALUES (1, ?, ?);
            """,
            access_token, expires_at, access_token, expires_at,
        )
        conn.commit()
    except pyodbc.Error as e:
        log.error(f"[DB] Failed to save token: {e}")
        raise SystemExit(1)
    finally:
        conn.close()
