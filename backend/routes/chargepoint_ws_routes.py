from __future__ import annotations

import logging
from typing import Callable

from fastapi import APIRouter, WebSocket

from application.connection_registry import ConnectionRegistryChargePoint
from domain.chargepoint_session import (
    ChargePointSession,
    ChargePointSettings,
    OCPPVersion,
)
from infrastructure.fastapi_websocket_adapter import FastAPIWebSocketAdapter
from infrastructure.ocpp_handlers import V16Handler, V201Handler
from infrastructure.websocket_gateway import WebSocketGateway

# ---------------------------------------------------------------
def router(
    registry: ConnectionRegistryChargePoint,
    *,
    gateway: WebSocketGateway | None = None,
) -> APIRouter:
    gw = gateway or WebSocketGateway()
    r = APIRouter()
    log = logging.getLogger("chargepoint-ws")

    @r.websocket("/ocpp{client_path:path}")
    async def cp_ws(ws: WebSocket, client_path: str = ""):
        """
        Eén fysieke WebSocket-verbinding met een laadpaal.
        Het SUB-PROTOCOL geeft de OCPP-versie aan.
        """
        channel = await gw.accept(ws)
        subproto = (ws.headers.get("sec-websocket-protocol") or "").lower()
        cp_id = f"cp-{id(ws)}"

        # -------- detecteer versie op basis van sub-protocol -------------
        if "2.0.1" in subproto:
            cp_parser = V201Handler(cp_id, channel)
            version = OCPPVersion.V201
        elif "1.6" in subproto or "ocpp1.6" in subproto:
            cp_parser = V16Handler(cp_id, channel)
            version = OCPPVersion.V16
        else:
            # fallback: probeer 1.6
            log.warning("Unknown sub-protocol '%s' → defaulting to OCPP 1.6", subproto)
            cp_parser = V16Handler(cp_id, channel)
            version = OCPPVersion.V16

        settings = ChargePointSettings()
        settings.ocpp_version = version

        session = ChargePointSession(cp_parser.id, channel, cp_parser, settings)
        await registry.register(session)

        try:
            await session.listen()
        finally:
            await registry.deregister(session)

    return r
