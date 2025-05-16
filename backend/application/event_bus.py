from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List

log = logging.getLogger("event-bus")


class EventBus:
    """Simpel pub/sub-mechanisme (in-process)."""

    def __init__(self) -> None:
        self._subs: Dict[str, List[Callable[..., Awaitable[Any] | Any]]] = defaultdict(list)

    # ---------------------------------------------------------------- subscribe
    def subscribe(self, event: str, handler: Callable[..., Awaitable[Any] | Any]) -> None:
        self._subs[event].append(handler)

    # ---------------------------------------------------------------- publish
    async def publish(self, event: str, **payload) -> None:
        for h in self._subs[event]:
            try:
                rv = h(**payload)
                if asyncio.iscoroutine(rv):
                    await rv
            except Exception as exc:  # pragma: no cover
                log.error("handler error for %s: %s", event, exc, exc_info=True)


# Singleton
bus: EventBus = EventBus()
