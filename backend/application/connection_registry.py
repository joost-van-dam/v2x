"""
Thread-safe registries voor actieve connecties.

Wijzigingen
-----------
• Alias-cache zodat een Charge Point zijn alias bewaart ook wanneer hij later
  met een andere OCPP-versie opnieuw verbindt.
• Public helper `remember_alias()` – wordt gebruikt door het REST-endpoint
  `/set-alias`, maar kan ook elders worden aangeroepen.
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Protocol, TypeVar, Generic

__all__ = [
    "ConnectionRegistryChargePoint",
    "ConnectionRegistryFrontend",
]

# -------------------------------------------------------------------- helpers
class HasId(Protocol):
    id: str            # unieke key in de registry
    _settings: object  # voor ChargePointSession zit alias hierin


T = TypeVar("T", bound=HasId)


# -------------------------------------------------------------------- basis-registry
class _ConnectionRegistryBase(Generic[T]):
    """Asynchrone, thread-veilige dict 〈id → item〉 met simpele CRUD-helper­s."""

    def __init__(self) -> None:
        self._items: Dict[str, T] = {}
        self._lock = asyncio.Lock()

    # ........................................................ modifiers
    async def register(self, item: T) -> None:
        async with self._lock:
            self._items[item.id] = item

    async def deregister(self, item: T) -> None:
        async with self._lock:
            self._items.pop(item.id, None)

    # ........................................................ queries
    async def get(self, item_id: str) -> T | None:
        async with self._lock:
            return self._items.get(item_id)

    async def get_all(self) -> List[T]:
        async with self._lock:
            return list(self._items.values())


# -------------------------------------------------------------------- charge-point-registry
class ConnectionRegistryChargePoint(_ConnectionRegistryBase["ChargePointSession"]):  # type: ignore[name-defined]
    """
    Registry voor `ChargePointSession`-objecten.

    Extra: alias-cache zodat de Friendly-Name behouden blijft over reconnects.
    """

    def __init__(self) -> None:
        super().__init__()
        self._aliases: Dict[str, str | None] = {}

    # ........................ alias-logic .............................
    async def register(self, item: "ChargePointSession") -> None:      # type: ignore[name-defined]
        # alias uit cache injecteren vóór opslag
        if item.id in self._aliases:
            item._settings.alias = self._aliases[item.id]
        await super().register(item)

    async def deregister(self, item: "ChargePointSession") -> None:    # type: ignore[name-defined]
        # alias terugschrijven naar cache
        self._aliases[item.id] = item._settings.alias
        await super().deregister(item)

    async def remember_alias(self, cp_id: str, alias: str | None) -> None:
        """
        Opslaan/aanpassen van alias, ongeacht of er een live sessie is.
        """
        async with self._lock:
            self._aliases[cp_id] = alias
            # live sessie syncen
            sess = self._items.get(cp_id)
            if sess:
                sess._settings.alias = alias


# -------------------------------------------------------------------- front-end-registry
class _WsLike(Protocol):
    async def send_text(self, data: str) -> None: ...
    async def close(self, code: int | None = None) -> None: ...


class ConnectionRegistryFrontend(_ConnectionRegistryBase[_WsLike]):  # type: ignore[type-var]
    """Registry voor open FE-WebSockets."""
    pass
