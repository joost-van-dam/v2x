"""WebSocket-router voor OCPP-laadpalen."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, WebSocket

from application.connection_registry import ConnectionRegistryChargePoint
from application.event_bus import bus
from domain.chargepoint_session import (
    ChargePointSession,
    ChargePointSettings,
    OCPPVersion,
)
from infrastructure.fastapi_websocket_adapter import FastAPIWebSocketAdapter
from infrastructure.ocpp_handlers import V16Handler, V201Handler
from infrastructure.websocket_gateway import WebSocketGateway


def router(
    registry: ConnectionRegistryChargePoint,
    *,
    gateway: Optional[WebSocketGateway] = None,
) -> APIRouter:
    gw = gateway or WebSocketGateway()
    r = APIRouter()
    log = logging.getLogger("chargepoint-ws")

    # ----------------------------------------------------------------------
    @r.websocket("/ocpp{client_path:path}")
    async def cp_ws(ws: WebSocket, client_path: str = "") -> None:
        """
        Eén WebSocket-verbinding met een laadpaal (1.6 of 2.0.1).

        • Het laatste path-segment (= CP-identity) is het ID.
        • Bij reconnect met hetzelfde ID laten we nooit twee sessies tegelijk leven.
        • Publiceert **ChargePointConnected / -Disconnected** events via EventBus.
        """
        channel = await gw.accept(ws)

        # ------------------- ID bepalen -------------------
        raw_id = client_path.lstrip("/").strip()
        cp_id = raw_id or f"cp-{id(ws)}"

        # Bestaat er al een live sessie?  Sluit die eerst af + event.
        existing = await registry.get(cp_id)
        if existing is not None:
            log.warning("Duplicate connection for %s – closing previous session", cp_id)
            await bus.publish("ChargePointDisconnected", charge_point_id=cp_id)
            try:
                await existing.disconnect()
            finally:
                await registry.deregister(existing)

        # ------------------- OCPP-versie -------------------
        subproto = (ws.headers.get("sec-websocket-protocol") or "").lower()
        if "2.0.1" in subproto:
            cp_parser = V201Handler(cp_id, channel)
            version = OCPPVersion.V201
        elif "1.6" in subproto or "ocpp1.6" in subproto:
            cp_parser = V16Handler(cp_id, channel)
            version = OCPPVersion.V16
        else:
            log.warning("Unknown sub-protocol '%s' → defaulting to OCPP 1.6", subproto)
            cp_parser = V16Handler(cp_id, channel)
            version = OCPPVersion.V16

        # ------------------- sessie opbouwen ---------------
        settings = ChargePointSettings()
        settings.ocpp_version = version

        session = ChargePointSession(cp_id, channel, cp_parser, settings)
        await registry.register(session)
        log.info("Charge-point connected: id=%s  proto=%s", cp_id, version.value)

        # <-- Event naar alle front-ends
        await bus.publish(
            "ChargePointConnected",
            charge_point_id=cp_id,
            ocpp_version=version.value,
        )

        try:
            await session.listen()
        finally:
            await registry.deregister(session)
            log.info("Charge-point disconnected: id=%s", cp_id)
            await bus.publish("ChargePointDisconnected", charge_point_id=cp_id)

    return r
