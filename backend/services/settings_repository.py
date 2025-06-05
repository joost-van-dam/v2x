"""
Eenvoudige async-repository die ChargePointSettings persisteert
in Postgres (tabel `charge_point_settings`).
"""
from __future__ import annotations

import asyncpg
from typing import Dict, Any


class SettingsRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    # ---------------- lifecycle ----------------
    async def init(self) -> None:
        self._pool = await asyncpg.create_pool(dsn=self._dsn)
        async with self._pool.acquire() as con:
            await con.execute(
                """
                CREATE TABLE IF NOT EXISTS charge_point_settings (
                    id TEXT PRIMARY KEY,
                    alias TEXT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT FALSE,
                    ocpp_version TEXT
                );
                """
            )

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    # ---------------- CRUD ---------------------
    async def upsert(
        self,
        cp_id: str,
        alias: str | None,
        enabled: bool,
        ocpp_version: str,
    ) -> None:
        if not self._pool:
            raise RuntimeError("SettingsRepository not initialised")
        async with self._pool.acquire() as con:
            await con.execute(
                """
                INSERT INTO charge_point_settings (id, alias, enabled, ocpp_version)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE
                  SET alias = EXCLUDED.alias,
                      enabled = EXCLUDED.enabled,
                      ocpp_version = EXCLUDED.ocpp_version;
                """,
                cp_id,
                alias,
                enabled,
                ocpp_version,
            )

    async def load_all(self) -> Dict[str, Dict[str, Any]]:
        if not self._pool:
            raise RuntimeError("SettingsRepository not initialised")
        async with self._pool.acquire() as con:
            rows = await con.fetch(
                "SELECT id, alias, enabled, ocpp_version FROM charge_point_settings"
            )
            return {r["id"]: dict(r) for r in rows}
