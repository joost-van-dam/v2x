"""
Thread-safe registries voor actieve connecties + alias-persistentie
in Postgres.
"""
from __future__ import annotations

import asyncio
from typing import Dict, List, Protocol, TypeVar, Generic

from services.settings_repository import SettingsRepository   # ← nieuw import

__all__ = [
    "ConnectionRegistryChargePoint",
    "ConnectionRegistryFrontend",
]

# ---------------- helper-interfaces ----------------
class HasId(Protocol):
    id: str
    _settings: object


T = TypeVar("T", bound=HasId)


class _ConnectionRegistryBase(Generic[T]):
    """Asynchrone, thread-veilige dict 〈id → item〉."""
    def __init__(self) -> None:
        self._items: Dict[str, T] = {}
        self._lock = asyncio.Lock()

    # ---------- modifiers ----------
    async def register(self, item: T) -> None:
        async with self._lock:
            self._items[item.id] = item

    async def deregister(self, item: T) -> None:
        async with self._lock:
            self._items.pop(item.id, None)

    # ---------- queries ------------
    async def get(self, item_id: str) -> T | None:
        async with self._lock:
            return self._items.get(item_id)

    async def get_all(self) -> List[T]:
        async with self._lock:
            return list(self._items.values())


# ================= Charge-Point registry =================
class ConnectionRegistryChargePoint(      # type: ignore[name-defined]
    _ConnectionRegistryBase["ChargePointSession"]
):
    """
    Registry voor `ChargePointSession`-objecten.
    • Alias-cache wordt nu *persistent* bewaard in Postgres.
    """

    def __init__(self, repo: SettingsRepository) -> None:
        super().__init__()
        self._repo = repo
        self._aliases: Dict[str, str | None] = {}

    # ----------- bootstrap (bij opstart) -------------
    def preload_aliases(self, cache: Dict[str, str | None]) -> None:
        self._aliases = cache.copy()

    # ----------- alias-logic -------------------------
    async def register(self, item: "ChargePointSession") -> None:      # type: ignore
        # alias uit cache injecteren vóór opslag
        if item.id in self._aliases:
            item._settings.alias = self._aliases[item.id]
        await super().register(item)

        # persist current settings
        await self._repo.upsert(
            item.id,
            item._settings.alias,
            item._settings.enabled,
            item._settings.ocpp_version.value,
        )

    async def deregister(self, item: "ChargePointSession") -> None:    # type: ignore
        self._aliases[item.id] = item._settings.alias
        await super().deregister(item)
        await self._repo.upsert(
            item.id,
            item._settings.alias,
            item._settings.enabled,
            item._settings.ocpp_version.value,
        )

    async def remember_alias(self, cp_id: str, alias: str | None) -> None:
        async with self._lock:
            self._aliases[cp_id] = alias
            sess = self._items.get(cp_id)
            if sess:
                sess._settings.alias = alias
            # → persist
            await self._repo.upsert(
                cp_id,
                alias,
                sess._settings.enabled if sess else False,
                sess._settings.ocpp_version.value if sess else "1.6",
            )


# ================= Front-end registry ====================
class _WsLike(Protocol):
    async def send_text(self, data: str) -> None: ...
    async def close(self, code: int | None = None) -> None: ...


class ConnectionRegistryFrontend(_ConnectionRegistryBase[_WsLike]):   # type: ignore[type-var]
    """Registry voor open FE-sockets."""
    pass
