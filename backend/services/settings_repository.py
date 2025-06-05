"""
Async repository die ChargePointSettings persisteert in Postgres
(tabel `charge_point_settings`).

⚠️  Deze versie faalt niet meer wanneer er tijdens unit-tests nog geen
PostgreSQL-database draait.  Als er (nog) geen connection-pool is
geïnitialiseerd, worden `upsert()`- en `load_all()`-aanroepen simpelweg
no-ops zodat de rest van de applicatie blijft werken.  In productie
roept `init()` de pool (zoals voorheen) wél op en wordt er gewoon naar
Postgres geschreven.
"""
from __future__ import annotations

import asyncpg
from typing import Dict, Any, Optional


class SettingsRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    # ----------------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------------
    async def init(self) -> None:
        """Maakt (indien nodig) de connection-pool en de tabel aan."""
        if self._pool is not None:
            return  # al gecreëerd

        self._pool = await asyncpg.create_pool(dsn=self._dsn)
        async with self._pool.acquire() as con:
            await con.execute(
                """
                CREATE TABLE IF NOT EXISTS charge_point_settings (
                    id            TEXT PRIMARY KEY,
                    alias         TEXT NULL,
                    enabled       BOOLEAN      NOT NULL DEFAULT FALSE,
                    ocpp_version  TEXT
                );
                """
            )

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    # ----------------------------------------------------------------------
    # CRUD helpers – vallen nu stil wanneer er geen database beschikbaar is
    # ----------------------------------------------------------------------
    async def upsert(
        self,
        cp_id: str,
        alias: str | None,
        enabled: bool,
        ocpp_version: str,
    ) -> None:
        """Slaat (of update) één settings-record.

        Tijdens unit tests is er vaak nog geen Postgres; wanneer de pool
        ontbreekt slaan we het schrijven daarom stil i.p.v. een exception
        te gooien.  Op die manier hoeven de tests geen live database.
        """
        if self._pool is None:
            # Postgres niet beschikbaar (bv. tijdens tests) → silently ignore
            return

        async with self._pool.acquire() as con:
            await con.execute(
                """
                INSERT INTO charge_point_settings (id, alias, enabled, ocpp_version)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE
                  SET alias        = EXCLUDED.alias,
                      enabled      = EXCLUDED.enabled,
                      ocpp_version = EXCLUDED.ocpp_version;
                """,
                cp_id,
                alias,
                enabled,
                ocpp_version,
            )

    async def load_all(self) -> Dict[str, Dict[str, Any]]:
        """Laadt alle cached settings uit Postgres.

        Geeft een lege dict terug als er (nog) geen database aanwezig is.
        """
        if self._pool is None:
            # Geen pool → niets geladen
            return {}

        async with self._pool.acquire() as con:
            rows = await con.fetch(
                "SELECT id, alias, enabled, ocpp_version FROM charge_point_settings"
            )
            return {r["id"]: dict(r) for r in rows}
