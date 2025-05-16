"""REST/RPC-router voor het aansturen van laadpalen."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel

from application.command_service import CommandService
from application.connection_registry import ConnectionRegistryChargePoint
from domain.chargepoint_session import ChargePointSession, OCPPVersion


class CommandRequest(BaseModel):
    action: str
    parameters: Dict[str, Any] = {}


def router(
    *,
    registry: ConnectionRegistryChargePoint,
    command_service: CommandService,
) -> APIRouter:
    r = APIRouter()

    # ------------------------------------------------ helpers
    async def _get(cp_id: str) -> ChargePointSession:
        cp = await registry.get(cp_id)
        if cp is None:
            raise HTTPException(status_code=404, detail="Charge-point not connected")
        return cp

    # ------------------------------------------------ generic command
    @r.post("/charge-points/{cp_id}/commands")
    async def send_generic(cp_id: str, request: CommandRequest):
        return await command_service.send(cp_id, request.action, request.parameters)

    # ------------------------------------------------ enable / disable
    @r.post("/charge-points/{cp_id}/enable", status_code=status.HTTP_200_OK)
    async def enable_cp(cp_id: str):
        cp = await _get(cp_id)
        cp._settings.enabled = True
        return {"id": cp.id, "active": True}

    @r.post("/charge-points/{cp_id}/disable", status_code=status.HTTP_200_OK)
    async def disable_cp(cp_id: str):
        cp = await _get(cp_id)
        cp._settings.enabled = False
        return {"id": cp.id, "active": False}

    # ------------------------------------------------ remote start / stop
    @r.post("/charge-points/{cp_id}/start", status_code=202)
    async def remote_start(cp_id: str):
        cp = await _get(cp_id)
        is_v201 = cp._settings.ocpp_version is OCPPVersion.V201
        action = "RequestStartTransaction" if is_v201 else "RemoteStartTransaction"
        params = {
            "id_tag": "DEFAULT_TAG",
            **({"remote_start_id": 1234} if is_v201 else {"connector_id": 1}),
        }
        return await command_service.send(cp_id, action, params)

    @r.post("/charge-points/{cp_id}/stop", status_code=202)
    async def remote_stop(cp_id: str):
        cp = await _get(cp_id)
        is_v201 = cp._settings.ocpp_version is OCPPVersion.V201
        action = "RequestStopTransaction" if is_v201 else "RemoteStopTransaction"
        params = {"transaction_id": 1}
        return await command_service.send(cp_id, action, params)

    # ------------------------------------------------ charging current
    @r.post("/charge-points/{cp_id}/charging-current")
    async def set_current(cp_id: str, current: int = Body(..., ge=1)):
        cp = await _get(cp_id)
        is_v201 = cp._settings.ocpp_version is OCPPVersion.V201
        if is_v201:
            action = "SetVariables"
            params = {"key": "ChargingCurrent", "value": str(current)}
        else:
            action = "ChangeConfiguration"
            params = {"key": "MaxChargingCurrent", "value": str(current)}
        return await command_service.send(cp_id, action, params)

    # ------------------------------------------------ configuration
    @r.get("/charge-points/{cp_id}/configuration")
    async def configuration(cp_id: str):
        cp = await _get(cp_id)
        is_v201 = cp._settings.ocpp_version is OCPPVersion.V201
        action = "GetBaseReport" if is_v201 else "GetConfiguration"
        params: Dict[str, Any] = (
            {"requestId": 55, "reportBase": "FullInventory"} if is_v201 else {"key": []}
        )
        return await command_service.send(cp_id, action, params)

    # ------------------------------------------------ list connected
    @r.get("/get-all-charge-points")
    async def list_cps():
        cps = await registry.get_all()
        return {
            "connected": [
                {
                    "id": c.id,
                    "ocpp_version": c._settings.ocpp_version.value,
                    "active": c._settings.enabled,
                }
                for c in cps
            ]
        }

    return r
