"""
Thread-safe registries voor actieve connecties.

• `ConnectionRegistryChargePoint` – bewaart live `ChargePointSession`-objecten
• `ConnectionRegistryFrontend`    – bewaart open front-end WebSocket-sockets
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Protocol, TypeVar, Generic

__all__ = [
    "ConnectionRegistryChargePoint",
    "ConnectionRegistryFrontend",
]


# ------------------------------------------------------------------ helpers
class HasId(Protocol):
    """
    Alle items die we opslaan in een registry moeten een *unieke* `id`
    property hebben.  Dit kan een `ChargePointSession`, een FastAPI-WebSocket,
    of iets anders zijn.
    """

    id: str


T = TypeVar("T", bound=HasId)


# ------------------------------------------------------------------ generic
class _ConnectionRegistryBase(Generic[T]):
    """Draad-veilige map 〈id, item〉 met basic CRUD-helper-methodes."""

    def __init__(self) -> None:
        self._items: Dict[str, T] = {}
        self._lock = asyncio.Lock()

    # .................................................... modifiers
    async def register(self, item: T) -> None:
        async with self._lock:
            self._items[item.id] = item

    async def deregister(self, item: T) -> None:
        async with self._lock:
            self._items.pop(item.id, None)

    # .................................................... queries
    async def get(self, item_id: str) -> T | None:
        async with self._lock:
            return self._items.get(item_id)

    async def get_all(self) -> List[T]:
        async with self._lock:
            return list(self._items.values())


# ------------------------------------------------------------------ concrete
class ConnectionRegistryChargePoint(_ConnectionRegistryBase["ChargePointSession"]):  # type: ignore[name-defined]
    """
    Registry voor `ChargePointSession`-instantie­s.

    (De type-hint wordt pas bij runtime ‘ge-resolved’; de ignore is zodat
    mypy niet klaagt over een circulaire import.)
    """

    pass


class _WsLike(Protocol):
    async def send_text(self, data: str) -> None: ...
    async def close(self, code: int | None = None) -> None: ...


class ConnectionRegistryFrontend(_ConnectionRegistryBase[_WsLike]):  # type: ignore[type-var]
    """
    Registry voor ruwe WebSocket-objects richting de front-end.
    """

    pass
