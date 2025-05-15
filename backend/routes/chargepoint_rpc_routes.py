"""REST/RPC-router voor het eenvoudig aansturen van laadpalen.

Publieke endpoints (allemaal onder **/api/v1/**):

| Methode | Pad | Omschrijving |
|---------|-----|--------------|
| POST | **/charge-points/{id}/commands** | generiek OCPP-RPC-doorstuurpunt |
| POST | **/charge-points/{id}/start** | remote-start transaction |
| POST | **/charge-points/{id}/stop** | remote-stop transaction |
| POST | **/charge-points/{id}/charging-current** | laadstroom (A) instellen |
| GET  | **/charge-points/{id}/configuration** | volledige configuratie |
| GET  | **/get-all-charge-points** | lijst van verbonden laadpalen |

De router verwacht:
    • `registry` – `ConnectionRegistryChargePoint`
    • `command_service` – `CommandService`
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
    """Geeft een APIRouter met alle REST-eindpunten terug."""

    r = APIRouter()  # → géén prefix; wordt in main.py '/api/v1' gemount

    # ------------------------------------------------ helpers
    async def _get_session_or_404(cp_id: str) -> ChargePointSession:
        cp = await registry.get(cp_id)
        if cp is None:
            raise HTTPException(status_code=404, detail="Charge-point not connected")
        return cp

    # ------------------------------------------------ generic command
    @r.post("/charge-points/{cp_id}/commands", summary="Send arbitrary OCPP command")
    async def send_generic_command(cp_id: str, request: CommandRequest):
        return await command_service.send(cp_id, request.action, request.parameters)

    # ------------------------------------------------ remote start
    @r.post("/charge-points/{cp_id}/start", summary="Remote start transaction")
    async def remote_start(cp_id: str, id_tag: str = Body("DEFAULT_TAG")):
        cp = await _get_session_or_404(cp_id)
        is_v201 = cp._settings.ocpp_version.startswith("2.")
        action = "RequestStartTransaction" if is_v201 else "RemoteStartTransaction"
        params = ({"id_tag": id_tag, "remote_start_id": 1234} if is_v201 else {"id_tag": id_tag, "connector_id": 1})
        return await command_service.send(cp_id, action, params)

    # ------------------------------------------------ remote stop
    @r.post("/charge-points/{cp_id}/stop", summary="Remote stop transaction")
    async def remote_stop(cp_id: str, transaction_id: int = Body(1)):
        cp = await _get_session_or_404(cp_id)
        is_v201 = cp._settings.ocpp_version.startswith("2.")
        action = "RequestStopTransaction" if is_v201 else "RemoteStopTransaction"
        params = {"transaction_id": transaction_id}
        return await command_service.send(cp_id, action, params)

    # ------------------------------------------------ charging current
    @r.post("/charge-points/{cp_id}/charging-current", summary="Set max charging current (A)")
    async def set_charging_current(cp_id: str, current: int = Body(..., ge=1)):
        cp = await _get_session_or_404(cp_id)
        is_v201 = cp._settings.ocpp_version.startswith("2.")
        if is_v201:
            action = "SetVariables"
            params = {"key": "ChargingCurrent", "value": str(current)}
        else:
            action = "ChangeConfiguration"
            params = {"key": "MaxChargingCurrent", "value": str(current)}
        return await command_service.send(cp_id, action, params)

    # ------------------------------------------------ configuration
    @r.get("/charge-points/{cp_id}/configuration", summary="Fetch full configuration")
    async def get_configuration(cp_id: str):
        cp = await _get_session_or_404(cp_id)
        is_v201 = cp._settings.ocpp_version.startswith("2.")
        action = "GetBaseReport" if is_v201 else "GetConfiguration"
        params: Dict[str, Any] = {"requestId": 55, "reportBase": "FullInventory"} if is_v201 else {"key": []}
        return await command_service.send(cp_id, action, params)

    # ------------------------------------------------ list connected
    @r.get("/get-all-charge-points", summary="List connected charge-points")
    async def list_connected():
        cps = await registry.get_all()
        return {"connected": [c.id for c in cps]}

    return r