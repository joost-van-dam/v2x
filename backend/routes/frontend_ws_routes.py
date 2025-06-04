from __future__ import annotations

import json
import logging
from typing import Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from application.connection_registry import ConnectionRegistryFrontend
from application.event_bus import bus

log = logging.getLogger("frontend-ws")


def router(registry: ConnectionRegistryFrontend) -> APIRouter:
    r = APIRouter()

    # ---------------------------------------------------- FE-socket endpoint
    @r.websocket("/frontend")
    async def frontend_ws(ws: WebSocket) -> None:
        await ws.accept()
        ws.id = str(id(ws))            # type: ignore[attr-defined]
        await registry.register(ws)    # type: ignore[arg-type]
        log.info("Front-end connected: %s", ws.id)

        try:
            while True:
                await ws.receive_text()  # FE stuurt (nog) niets terug
        except WebSocketDisconnect:
            log.info("Front-end %s disconnected", ws.id)
        finally:
            await registry.deregister(ws)  # type: ignore[arg-type]

    # ---------------------------------------------------- helper: broadcast
    async def _broadcast(message: dict) -> None:
        for fe in await registry.get_all():
            try:
                await fe.send_text(json.dumps(message))
            except Exception:
                await registry.deregister(fe)  # type: ignore[arg-type]

    # ---------------------------------------------------- EventBus-bridge
    def _make_handler(evt_name: str) -> Callable[..., None]:
        async def _handler(**payload):
            await _broadcast({"event": evt_name, **payload})
        return _handler

    for _evt in (
        # OCPP-core events
        "MeterValues",
        "Heartbeat",
        "StatusNotification",
        "StartTransaction",
        "StopTransaction",
        "BootNotification",
        "Authorize",
        "ChargePointConnected",
        "ChargePointDisconnected",
        "ConfigurationChanged",
    ):
        bus.subscribe(_evt, _make_handler(_evt))

    return r
