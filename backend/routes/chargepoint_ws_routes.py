# routes/chargepoint_ws_routes.py
"""WebSocket‑router voor OCPP‑laadpalen.

Belangrijkste wijziging:
• We bepalen het **Charge Point‑ID** aan de hand van de path‑segmenten in de
  WebSocket‑URL in plaats van een willekeurig runtime‑id.  Hiermee herkent
  de backend een laadpaal bij herverbindingen én blijft het ID stabiel.
• Komt er nog een sessie met hetzelfde ID binnen? Dan verbreken we de oude
  sessie om ‘hijacking’ binnen dezelfde ID te voorkomen.
"""

from __future__ import annotations

import logging
from typing import Optional

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


# ----------------------------------------------------------------------------
# Router‑factory
# ----------------------------------------------------------------------------

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
        """Afhandelen van een **enkele** WebSocket‑verbinding met een laadpaal.

        * Het **laatste path‑segment** (na /ocpp/…) wordt gezien als de
          *ChargePoint‑Identity* (conform OCPP‑specificatie).  Levert de
          laadpaal dus opnieuw dezelfde URI, dan krijgt‑’ie ook exact
          hetzelfde `cp_id` en kunnen we de vorige sessie beëindigen.
        * Valt het path weg of is het leeg, dan genereren we – als back‑up –
          een uniek runtime‑id.
        * We bepalen de OCPP‑versie via het sub‑protocol‑header.
        """

        # Handshake & channel‑adaptatie
        channel = await gw.accept(ws)

        # ------------------- ChargePoint‑ID bepalen -----------------------
        raw_id = client_path.lstrip("/").strip()
        cp_id = raw_id or f"cp-{id(ws)}"

        # Bestaat er al een sessie met dit ID?  Sluit die eerst af zodat we
        # nooit twee actieve verbindingen voor hetzelfde laadpaal‑ID hebben.
        existing = await registry.get(cp_id)
        if existing is not None:
            log.warning("Duplicate connection for %s – closing previous session", cp_id)
            try:
                await existing.disconnect()
            finally:
                await registry.deregister(existing)

        # ------------------- OCPP‑versie bepalen --------------------------
        subproto = (ws.headers.get("sec-websocket-protocol") or "").lower()
        if "2.0.1" in subproto:
            cp_parser = V201Handler(cp_id, channel)
            version = OCPPVersion.V201
        elif "1.6" in subproto or "ocpp1.6" in subproto:
            cp_parser = V16Handler(cp_id, channel)
            version = OCPPVersion.V16
        else:
            # Fallback: treat as 1.6 maar log het afwijkende sub‑protocol
            log.warning("Unknown sub‑protocol '%s' → defaulting to OCPP 1.6", subproto)
            cp_parser = V16Handler(cp_id, channel)
            version = OCPPVersion.V16

        # ------------------- sessie‑object opbouwen -----------------------
        settings = ChargePointSettings()
        settings.ocpp_version = version

        session = ChargePointSession(cp_id, channel, cp_parser, settings)
        await registry.register(session)
        log.info("Charge‑point connected: id=%s  proto=%s", cp_id, version.value)

        try:
            await session.listen()
        finally:
            await registry.deregister(session)
            log.info("Charge‑point disconnected: id=%s", cp_id)

    # ------------------------------------------------------------------
    return r
