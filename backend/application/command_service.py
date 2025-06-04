"""
Facade tussen REST-laag en OCPP-sessies.

Wijzigingen  • 4 jun 2025  
────────────
• Na een geslaagde ChangeConfiguration / SetVariables wordt er nu een
  **ConfigurationChanged**-event gepubliceerd op de EventBus.
• Kleine refactor: bus-import toegevoegd, zodat we overal central kunnen
  loggen/broadcasten.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import HTTPException

from application.connection_registry import ConnectionRegistryChargePoint
from application.event_bus import bus                  # ★  nieuw
from domain.chargepoint_session import ChargePointSession, OCPPVersion
from application.ocpp_command_strategy import (
    V16CommandStrategy,
    V201CommandStrategy,
)

log = logging.getLogger(__name__)


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

        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail="Charge-point did not respond (timeout).",
            ) from exc

        except RuntimeError as exc:
            # WebSocket is tijdens de call dichtgegaan
            await self._registry.deregister(session)
            raise HTTPException(
                status_code=503,
                detail="Charge-point disconnected while processing the request.",
            ) from exc

        # ............. event voor config-wijzigingen .....................
        if action in {"ChangeConfiguration", "SetVariables"}:
            try:
                await bus.publish(
                    "ConfigurationChanged",
                    charge_point_id=cp_id,
                    ocpp_action=action,
                    parameters=parameters,
                    result=str(result),
                )
            except Exception:  # pragma: no cover
                log.error("Unable to publish ConfigurationChanged", exc_info=True)

        return {"result": result}
