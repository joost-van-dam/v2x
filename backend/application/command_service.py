from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException

from application.connection_registry import ConnectionRegistryChargePoint
from domain.chargepoint_session import ChargePointSession


from application.ocpp_command_strategy import (
    V16CommandStrategy,
    V201CommandStrategy,
)

# ---------------------------------------------------------------
class CommandService:
    """
    Facade voor de REST/RPC-laag: stuurt commando’s naar
    de juiste laadpaal via de *versie-specifieke* strategy.
    """

    def __init__(self, registry: ConnectionRegistryChargePoint) -> None:
        self._registry = registry

    async def send(self, cp_id: str, action: str, parameters: dict[str, Any]) -> Any:
        session: ChargePointSession | None = await self._registry.get(cp_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Charge-point not connected")

        # -------- kies juiste strategy o.b.v. CP-instellingen
        if session._settings.ocpp_version.startswith("2."):
            strategy = V201CommandStrategy()
        else:
            strategy = V16CommandStrategy()

        ocpp_call = strategy.build(action, parameters)
        result = await session.send_call(ocpp_call)
        return {"result": result}
