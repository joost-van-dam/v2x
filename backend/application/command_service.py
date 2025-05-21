"""
Facade tussen REST-laag en OCPP-sessies.

Wijzigingen
-----------
• Extra checks zodat we *geen* RPC sturen zodra de WebSocket al dicht is
  (of de sessie al is beëindigd).  Dit voorkomt de RuntimeError én lost de
  race-condition op waarin het HTTP-request nog binnenkomt terwijl het
  backend-kanaal al aan het afsluiten is.
• Heldere HTTP-errors:
    - 404  – geen (actieve) sessie
    - 503  – sessie viel weg tijdens het verzoek
    - 504  – charge-point antwoordt niet (timeout)
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import HTTPException

from application.connection_registry import ConnectionRegistryChargePoint
from domain.chargepoint_session import ChargePointSession, OCPPVersion
from application.ocpp_command_strategy import V16CommandStrategy, V201CommandStrategy


class CommandService:
    """
    Vertaler van REST-/RPC-calls naar de juiste OCPP-call-objecten,
    inclusief versie-switching.
    """

    def __init__(self, registry: ConnectionRegistryChargePoint) -> None:
        self._registry = registry

    # ---------------------------------------------------------------- send
    async def send(self, cp_id: str, action: str, parameters: dict[str, Any]) -> Any:
        session: ChargePointSession | None = await self._registry.get(cp_id)

        # ............. bestaat-er-een-actieve sessie? ....................
        if session is None or not session._running:
            # defensief: mocht er nog een zombie-entry staan → opruimen
            if session:
                await self._registry.deregister(session)
            raise HTTPException(status_code=404, detail="Charge-point not connected")

        # ............. kies strategy per OCPP-versie .....................
        strategy = (
            V201CommandStrategy()
            if session._settings.ocpp_version is OCPPVersion.V201
            else V16CommandStrategy()
        )
        ocpp_call = strategy.build(action, parameters)

        # ............. stuur call & afvang fouten ........................
        try:
            result = await session.send_call(ocpp_call)

        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail="Charge-point did not respond (timeout).",
            ) from None

        except RuntimeError:
            # WebSocket is tijdens de call dichtgegaan
            await self._registry.deregister(session)
            raise HTTPException(
                status_code=503,
                detail="Charge-point disconnected while processing the request.",
            ) from None

        return {"result": result}
