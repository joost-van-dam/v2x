from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from application.connection_registry import ConnectionRegistryFrontend
from application.event_bus import bus

log = logging.getLogger("frontend-ws")


def router(registry: ConnectionRegistryFrontend) -> APIRouter:
    r = APIRouter()

    # ---------------------------------------------------------------- endpoint
    @r.websocket("/frontend")
    async def frontend_ws(ws: WebSocket) -> None:
        await ws.accept()
        ws.id = str(id(ws))  # type: ignore[attr-defined]
        await registry.register(ws)  # type: ignore[arg-type]
        log.info("Front-end connected: %s", ws.id)

        try:
            while True:
                # front-end stuurt voorlopig niets
                await ws.receive_text()
        except WebSocketDisconnect:
            log.info("Front-end %s disconnected", ws.id)
        finally:
            await registry.deregister(ws)  # type: ignore[arg-type]

    # ---------------------------------------------------------------- broadcast-helper
    async def _broadcast(message: dict) -> None:
        """Stuur JSON-event naar alle FE-sockets."""
        for fe in await registry.get_all():
            try:
                await fe.send_text(json.dumps(message))
            except Exception:
                await registry.deregister(fe)  # type: ignore[arg-type]

    # ---------------------------------------------------------------- event-bridge
    async def _on_meter_values(**payload):
        await _broadcast({"event": "MeterValues", **payload})

    bus.subscribe("MeterValues", _on_meter_values)

    return r
