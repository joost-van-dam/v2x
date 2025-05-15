"""REST/RPC-router voor het eenvoudig aansturen van laadpalen.

Publieke endpoints (prefix **/api/v1/**):

| Methode | Pad | Omschrijving |
|---------|-----|--------------|
| POST | /charge-points/{id}/commands | generiek OCPP‑RPC‑doorstuurpunt |
| POST | /charge-points/{id}/start | remote‑start transaction (geen body) |
| POST | /charge-points/{id}/stop | remote‑stop transaction (geen body) |
| POST | /charge-points/{id}/charging-current | laadstroom (A) instellen |
| GET  | /charge-points/{id}/configuration | volledige configuratie |
| GET  | /get-all-charge-points | lijst verbonden laadpalen |
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from application.command_service import CommandService
from application.connection_registry import ConnectionRegistryChargePoint
from domain.chargepoint_session import ChargePointSession


class CommandRequest(BaseModel):
    action: str
    parameters: Dict[str, Any] = {}


def router(*, registry: ConnectionRegistryChargePoint, command_service: CommandService) -> APIRouter:
    r = APIRouter()

    # ------------------------------------------------ helpers
    async def _get(cp_id: str) -> ChargePointSession:
        cp = await registry.get(cp_id)
        if cp is None:
            raise HTTPException(status_code=404, detail="Charge-point not connected")
        return cp

    # ------------------------------------------------ generic
    @r.post("/charge-points/{cp_id}/commands")
    async def send_generic(cp_id: str, request: CommandRequest):
        return await command_service.send(cp_id, request.action, request.parameters)

    # ------------------------------------------------ remote start (no body)
    @r.post("/charge-points/{cp_id}/start", status_code=202)
    async def remote_start(cp_id: str):
        cp = await _get(cp_id)
        v201 = cp._settings.ocpp_version.startswith("2.")
        action = "RequestStartTransaction" if v201 else "RemoteStartTransaction"
        params = {"id_tag": "DEFAULT_TAG", **({"remote_start_id": 1234} if v201 else {"connector_id": 1})}
        return await command_service.send(cp_id, action, params)

    # ------------------------------------------------ remote stop (no body)
    @r.post("/charge-points/{cp_id}/stop", status_code=202)
    async def remote_stop(cp_id: str):
        cp = await _get(cp_id)
        v201 = cp._settings.ocpp_version.startswith("2.")
        action = "RequestStopTransaction" if v201 else "RemoteStopTransaction"
        params = {"transaction_id": 1}
        return await command_service.send(cp_id, action, params)

    # ------------------------------------------------ charging current
    @r.post("/charge-points/{cp_id}/charging-current")
    async def set_current(cp_id: str, current: int = Body(..., ge=1)):
        cp = await _get(cp_id)
        v201 = cp._settings.ocpp_version.startswith("2.")
        if v201:
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
        v201 = cp._settings.ocpp_version.startswith("2.")
        action = "GetBaseReport" if v201 else "GetConfiguration"
        params: Dict[str, Any] = {"requestId": 55, "reportBase": "FullInventory"} if v201 else {"key": []}
        return await command_service.send(cp_id, action, params)

    # ------------------------------------------------ list connected
    @r.get("/get-all-charge-points")
    async def list_cps():
        cps = await registry.get_all()
        return {"connected": [c.id for c in cps]}

    return r
