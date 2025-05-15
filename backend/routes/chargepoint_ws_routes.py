from __future__ import annotations

import logging
from typing import Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from domain.chargepoint_session import ChargePointSession, ChargePointSettings
from infrastructure.websocket_gateway import WebSocketGateway
from application.connection_registry import ConnectionRegistryChargePoint
from infrastructure.fastapi_websocket_adapter import FastAPIWebSocketAdapter  # for parser factory

from ocpp.v16 import ChargePoint as CPv16      # type: ignore
from ocpp.v201 import ChargePoint as CPv201    # type: ignore

from infrastructure.ocpp_handlers import V16Handler, V201Handler  # ⬅️ nieuw

# ---------------------------------------------------------------
def router(registry: ConnectionRegistryChargePoint,
           *, gateway: WebSocketGateway | None = None) -> APIRouter:
    gw = gateway or WebSocketGateway()
    r = APIRouter()
    log = logging.getLogger("chargepoint-ws")

    @r.websocket("/ocpp{client_path:path}")
    async def cp_ws(ws: WebSocket, client_path: str = ""):
        channel = await gw.accept(ws)
        subproto = ws.headers.get("sec-websocket-protocol", "")
        cp_id = f"cp-{id(ws)}"

        if "2.0.1" in subproto:
            cp_parser = V201Handler(cp_id, channel)
            version = "2.0.1"
        else:
            cp_parser = V16Handler(cp_id, channel)
            version = "1.6"

        settings = ChargePointSettings()
        settings.ocpp_version = version

        session = ChargePointSession(cp_parser.id, channel, cp_parser, settings)
        await registry.register(session)

        try:
            await session.listen()
        finally:
            await registry.deregister(session)

    return r

