from __future__ import annotations

import json
import logging
from typing import Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from application.connection_registry import ConnectionRegistryFrontend


def router(registry: ConnectionRegistryFrontend) -> APIRouter:
    r = APIRouter()
    log = logging.getLogger("frontend-ws")

    # ----------------------------------------------------------- endpoint
    @r.websocket("/frontend")
    async def frontend_ws(ws: WebSocket) -> None:
        await ws.accept()
        ws.id = str(id(ws))  # type: ignore[attr-defined]
        await registry.register(ws)  # type: ignore[arg-type]
        log.info("Front-end connected: %s", ws.id)

        try:
            while True:
                # We ontvangen momenteel geen RPC’s vanuit FE,
                # maar houden de verbinding open voor events.
                await ws.receive_text()
        except WebSocketDisconnect:
            log.info("Front-end %s disconnected", ws.id)
        finally:
            await registry.deregister(ws)  # type: ignore[arg-type]

    # ----------------------------------------------------------- helper
    async def broadcast(message: dict) -> None:
        """Publiceer event naar alle ingeschreven FE-sockets."""
        for fe in await registry.get_all():
            try:
                await fe.send_text(json.dumps(message))
            except Exception as exc:  # pragma: no cover
                log.error("FE-socket error: %s", exc)
                await registry.deregister(fe)  # type: ignore[arg-type]

    # handigheidje zodat andere modules eenvoudig kunnen importeren:
    r.broadcast = broadcast  # type: ignore[attr-defined]

    return r
