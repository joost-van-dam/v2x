"""REST/RPC-router voor het aansturen van laadpalen."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from application.command_service import CommandService
from application.connection_registry import ConnectionRegistryChargePoint
from domain.chargepoint_session import ChargePointSession, OCPPVersion


class CommandRequest(BaseModel):
    action: str
    parameters: Dict[str, Any] = {}


# ------------------------------------------------------------------------------
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

    def _unwrap_result(obj: Any) -> Any:
        """Zet dict|object om naar het 'result' object c.q. laat origineel staan."""
        if isinstance(obj, dict):
            return obj.get("result", obj)
        return getattr(obj, "result", obj)

    def _field(d_or_obj: Any, snake: str, camel: str) -> Any:
        """Levert veld terug ongeacht snake/camel of dict/object."""
        if isinstance(d_or_obj, dict):
            return d_or_obj.get(snake) or d_or_obj.get(camel)
        return getattr(d_or_obj, snake, None) or getattr(d_or_obj, camel, None)

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
        params = {
            "id_tag": "DEFAULT_TAG",
            **({"remote_start_id": 1234} if v201 else {"connector_id": 1}),
        }
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
                cp_id,
                "SetVariables",
                {
                    "key": {
                        "component": {"name": "SmartChargingCtrlr"},
                        "variable_name": "ChargingCurrent",
                    },
                    "value": str(current),
                },
            )
        return await command_service.send(
            cp_id,
            "ChangeConfiguration",
            {"key": "MaxChargingCurrent", "value": str(current)},
        )

    # ---------------------------------------------------------------- configuration
    @r.get("/charge-points/{cp_id}/configuration")
    async def configuration(cp_id: str):
        """
        – 1.6:  GetConfiguration
        – 2.0.1: GetBaseReport → NotifyReport → (bulk) GetVariables
        """
        cp = await _get(cp_id)

        # ----------------------------- OCPP 1.6 -----------------------------
        if cp._settings.ocpp_version is not OCPPVersion.V201:
            return await command_service.send(cp_id, "GetConfiguration", {"key": []})

        # ----------------------------- OCPP 2.0.1 ---------------------------
        # buffers leegmaken
        if hasattr(cp._cp, "latest_config"):
            cp._cp.latest_config.clear()          # type: ignore[attr-defined]
        cp._cp.notify_report_done = False         # type: ignore[attr-defined]

        # FullInventory-report opvragen
        base_resp = await command_service.send(
            cp_id,
            "GetBaseReport",
            {"requestId": 55, "reportBase": "FullInventory"},
        )

        # wachten op NotifyReport-einden
        for _ in range(100):                      # 10 s timeout
            if getattr(cp._cp, "notify_report_done", False):   # type: ignore[attr-defined]
                break
            await asyncio.sleep(0.1)

        raw: List[Dict[str, Any]] = getattr(cp._cp, "latest_config", [])  # type: ignore[attr-defined]

        # dedupliceren
        uniq: Dict[str, Dict[str, Any]] = {}
        for itm in raw:
            key = itm.get("key")
            if not key:
                continue
            if key not in uniq or (uniq[key].get("value") is None and itm.get("value") is not None):
                uniq[key] = itm
        cfg_list: List[Dict[str, Any]] = list(uniq.values())

        # ontbrekende values ophalen
        missing = [c for c in cfg_list if c.get("value") is None]
        if missing:
            CHUNK = 24
            for i in range(0, len(missing), CHUNK):
                batch = missing[i : i + CHUNK]
                keys_payload = [
                    {"component": itm.get("component", {}), "variable": {"name": itm["key"]}}
                    for itm in batch
                ]
                gv_wrap = await command_service.send(cp_id, "GetVariables", {"key": keys_payload})
                gv_res = _unwrap_result(gv_wrap)

                results = (
                    gv_res.get("get_variable_result", [])
                    if isinstance(gv_res, dict)
                    else getattr(gv_res, "get_variable_result", [])
                )
                for res in results:
                    name = _field(_field(res, "variable", "variable"), "name", "name")
                    val = _field(res, "attribute_value", "attributeValue")
                    status = _field(res, "attribute_status", "attributeStatus") or "Rejected"
                    for itm in batch:
                        if itm["key"] == name and itm.get("value") is None:
                            itm["value"] = val
                            if status in {"Rejected", "NotSupported"}:
                                itm["readonly"] = True

        # schrijfbaarheid bepalen via Target-attribute
        CHUNK = 24
        for i in range(0, len(cfg_list), CHUNK):
            batch = cfg_list[i : i + CHUNK]
            keys_payload = [
                {
                    "component": itm.get("component", {}),
                    "variable": {"name": itm["key"]},
                    "attributeType": "Target",
                }
                for itm in batch
            ]
            gv_wrap = await command_service.send(cp_id, "GetVariables", {"key": keys_payload})
            gv_res = _unwrap_result(gv_wrap)

            results = (
                gv_res.get("get_variable_result", [])
                if isinstance(gv_res, dict)
                else getattr(gv_res, "get_variable_result", [])
            )
            for res in results:
                name = _field(_field(res, "variable", "variable"), "name", "name")
                status = _field(res, "attribute_status", "attributeStatus") or "Rejected"
                for itm in batch:
                    if itm["key"] == name:
                        itm["readonly"] = status != "Accepted"

        for itm in cfg_list:          # default naar read-only = True
            itm.setdefault("readonly", True)

        cfg_list.sort(key=lambda x: str(x["key"]).lower())

        # ---- >>> bugfix hier: eerst unwrap, dán status bepalen ------------
        result_obj = _unwrap_result(base_resp)
        if isinstance(result_obj, dict):
            status_val = result_obj.get("status", "Accepted")
        else:
            status_val = getattr(result_obj, "status", "Accepted")
        # -------------------------------------------------------------------

        return {
            "status": status_val,
            "configuration_key": cfg_list,
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
