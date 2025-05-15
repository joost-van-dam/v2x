from __future__ import annotations

from typing import Any, Dict, Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from application.connection_registry import ConnectionRegistryChargePoint
from application.command_service import CommandService


class CommandRequest(BaseModel):
    action: str
    parameters: Dict[str, Any] = {}


def router(
    registry: ConnectionRegistryChargePoint,
    command_service: CommandService,
) -> APIRouter:
    r = APIRouter()

    # ----------------------------------------------------------- queries
    @r.get("/charge-points", summary="List connected charge-points")
    async def list_chargepoints() -> dict[str, Any]:
        cps = await registry.get_all()
        return {"connected": [cp.id for cp in cps]}

    # ----------------------------------------------------------- commands
    @r.post("/charge-points/{cp_id}/commands", summary="Send OCPP command")
    async def send_command(cp_id: str, request: CommandRequest) -> Any:
        try:
            result = await command_service.send(cp_id, request.action, request.parameters)
            return {"result": result}
        except HTTPException as exc:
            raise exc

    return r
