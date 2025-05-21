"""
Thread-safe registries voor actieve connecties.

Wijzigingen
-----------
• Alias-cache toegevoegd zodat een Charge Point zijn **alias bewaart**
  over meerdere sessies heen (bijv. eerst v2.0.1, daarna v1.6).
  –  Eén dict `_aliases[id] = alias`
  –  Bij `register()` alias uit cache injecteren in Session-settings.
  –  Bij `deregister()` alias uit Session terugschrijven.

• Publieke helper `remember_alias()` om via REST direct te updaten
  zonder dat er per se een live sessie nodig is.
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
    id: str            # unieke identifier (session.id / socket.id)
    _settings: object  # voor ChargePointSession zit alias hierin


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


# ------------------------------------------------------------------ Charge-Point registry
class ConnectionRegistryChargePoint(_ConnectionRegistryBase["ChargePointSession"]):  # type: ignore[name-defined]
    """
    Registry voor `ChargePointSession`-objecten.

    Extra functionaliteit:
    •  Alias-cache zodat een CP bij herverbinden z’n alias behoudt.
    """

    def __init__(self) -> None:
        super().__init__()
        self._aliases: Dict[str, str | None] = {}

    # ............... override register / deregister ................
    async def register(self, item: "ChargePointSession") -> None:  # type: ignore[name-defined]
        # alias uit cache injecteren
        cached = self._aliases.get(item.id)
        if cached is not None:
            item._settings.alias = cached
        # standaard-logica
        await super().register(item)

    async def deregister(self, item: "ChargePointSession") -> None:  # type: ignore[name-defined]
        # alias terugschrijven
        self._aliases[item.id] = item._settings.alias
        await super().deregister(item)

    # ............... public helper ................................
    async def remember_alias(self, cp_id: str, alias: str | None) -> None:
        """Bewaar alias expliciet (bijv. vanuit REST call)."""
        async with self._lock:
            self._aliases[cp_id] = alias
            # is er een live sessie? → direct syncen
            sess = self._items.get(cp_id)
            if sess:
                sess._settings.alias = alias


# ------------------------------------------------------------------ Front-end registry
class _WsLike(Protocol):
    async def send_text(self, data: str) -> None: ...
    async def close(self, code: int | None = None) -> None: ...


class ConnectionRegistryFrontend(_ConnectionRegistryBase[_WsLike]):  # type: ignore[type-var]
    """Registry voor ruwe WebSocket-objects richting de front-end."""
    pass
