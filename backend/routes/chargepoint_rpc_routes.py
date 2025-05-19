"""REST/RPC-router voor het aansturen van laadpalen."""
from __future__ import annotations

import asyncio
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
    *, registry: ConnectionRegistryChargePoint, command_service: CommandService
) -> APIRouter:
    r = APIRouter()

    # ---------------------------------------------------------------- helpers
    async def _get(cp_id: str) -> ChargePointSession:
        cp = await registry.get(cp_id)
        if cp is None:
            raise HTTPException(status_code=404, detail="Charge-point not connected")
        return cp

    # ---------------------------------------------------------------- generic command
    @r.post("/charge-points/{cp_id}/commands")
    async def send_generic(cp_id: str, request: CommandRequest):
        return await command_service.send(cp_id, request.action, request.parameters)

    # ---------------------------------------------------------------- enable / disable
    @r.post("/charge-points/{cp_id}/enable")
    async def enable(cp_id: str):
        cp = await _get(cp_id)
        cp._settings.enabled = True
        return {"id": cp.id, "active": True}

    @r.post("/charge-points/{cp_id}/disable")
    async def disable(cp_id: str):
        cp = await _get(cp_id)
        cp._settings.enabled = False
        return {"id": cp.id, "active": False}

    # ---------------------------------------------------------------- remote start / stop
    @r.post("/charge-points/{cp_id}/start", status_code=202)
    async def remote_start(cp_id: str):
        cp = await _get(cp_id)
        v201 = cp._settings.ocpp_version is OCPPVersion.V201
        action = "RequestStartTransaction" if v201 else "RemoteStartTransaction"
        params = {"id_tag": "DEFAULT_TAG",
                  **({"remote_start_id": 1234} if v201 else {"connector_id": 1})}
        return await command_service.send(cp_id, action, params)

    @r.post("/charge-points/{cp_id}/stop", status_code=202)
    async def remote_stop(cp_id: str):
        cp = await _get(cp_id)
        v201 = cp._settings.ocpp_version is OCPPVersion.V201
        action = "RequestStopTransaction" if v201 else "RemoteStopTransaction"
        return await command_service.send(cp_id, action, {"transaction_id": 1})

    # ---------------------------------------------------------------- charging current
    @r.post("/charge-points/{cp_id}/charging-current")
    async def set_current(cp_id: str, current: int = Body(..., ge=1)):
        cp = await _get(cp_id)
        v201 = cp._settings.ocpp_version is OCPPVersion.V201
        if v201:
            return await command_service.send(
                cp_id, "SetVariables",
                {"key": "ChargingCurrent", "value": str(current)}
            )
        return await command_service.send(
            cp_id, "ChangeConfiguration",
            {"key": "MaxChargingCurrent", "value": str(current)}
        )

    # ---------------------------------------------------------------- configuration  (dedup + timeout)
    @r.get("/charge-points/{cp_id}/configuration")
    async def configuration(cp_id: str):
        cp = await _get(cp_id)

        # ============== OCPP 1.6  – simpel =============================
        if cp._settings.ocpp_version is not OCPPVersion.V201:
            return await command_service.send(cp_id, "GetConfiguration", {"key": []})

        # ============== OCPP 2.0.1  – NotifyReport flow ===============
        # 1) reset lokale buffers
        if hasattr(cp._cp, "latest_config"):
            cp._cp.latest_config.clear()          # type: ignore[attr-defined]
        cp._cp.notify_report_done = False         # type: ignore[attr-defined]

        # 2) vraag volledige inventaris aan
        base_resp = await command_service.send(
            cp_id,
            "GetBaseReport",
            {"requestId": 55, "reportBase": "FullInventory"},
        )

        # 3) wacht (max 10 s) tot alle NotifyReport-delen binnen zijn
        for _ in range(100):          # 100 × 0.1 s = 10 s
            if getattr(cp._cp, "notify_report_done", False):   # type: ignore[attr-defined]
                break
            await asyncio.sleep(0.1)

        raw_list = getattr(cp._cp, "latest_config", [])        # type: ignore[attr-defined]

        # 4) DEDUPLICATE  -------------------------------
        unique: Dict[str, Dict[str, Any]] = {}
        for entry in raw_list:
            key = entry.get("key")
            if key is None:
                continue
            if key not in unique:
                unique[key] = entry
            else:
                # vervang als nieuwe entry een waarde heeft en eerdere niet
                if unique[key].get("value") is None and entry.get("value") is not None:
                    unique[key] = entry

        clean_list = list(unique.values())
        clean_list.sort(key=lambda x: str(x["key"]).lower())

        # 5) response
        return {
            "status": getattr(base_resp, "status", "Accepted"),
            "configuration_key": clean_list,
        }

    # ---------------------------------------------------------------- list connected
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
