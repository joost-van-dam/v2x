from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from fastapi import HTTPException

from ocpp.v16 import call as call16          # type: ignore
from ocpp.v201 import call as call201        # type: ignore


class CommandStrategy(ABC):
    """
    Strategy-interface: vertaal een *action + parameters*-dict
    naar een concreet `ocpp.vXX.call.*` object.
    """

    @abstractmethod
    def build(self, action: str, params: Dict[str, Any]) -> Any: ...


# ---------------------------------------------------------------------
# OCPP 1.6
# ---------------------------------------------------------------------
class V16CommandStrategy(CommandStrategy):
    def build(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "RemoteStartTransaction":
            return call16.RemoteStartTransaction(
                id_tag=params.get("id_tag", "UNKNOWN"),
                connector_id=params.get("connector_id"),
                charging_profile=params.get("charging_profile"),
            )

        if action == "RemoteStopTransaction":
            return call16.RemoteStopTransaction(
                transaction_id=params["transaction_id"]
            )

        if action == "ChangeConfiguration":
            try:
                return call16.ChangeConfiguration(
                    key=params["key"], value=params["value"]
                )
            except KeyError:  # pragma: no cover
                raise HTTPException(
                    status_code=400, detail="Missing 'key' or 'value' parameter"
                )

        if action == "GetConfiguration":
            return call16.GetConfiguration(key=params.get("key", []))

        raise HTTPException(
            status_code=400, detail=f"Unknown OCPP 1.6 action: {action}"
        )


# ---------------------------------------------------------------------
# OCPP 2.0.1
# ---------------------------------------------------------------------
class V201CommandStrategy(CommandStrategy):
    """
    Mapping voor OCPP 2.0.1.

    Let op: de klassen heten *GetVariables* / *SetVariables* (zonder *Request*).
    """

    # ---------- helpers -------------------------------------------------
    @staticmethod
    def _build_set_variables(params: Dict[str, Any]) -> Any:
        """
        Ondersteunt twee input-vormen:

        1. `set_variable_data=[{component,variable,value,...}, ...]`   (volgens spec)
        2. Vereenvoudigd:  `key`, `value` (+ option. `component`)       (handig voor UI)
        """
        if "set_variable_data" in params:
            data: List[Dict[str, Any]] = params["set_variable_data"]
        else:
            component = params.get("component", {"name": "ChargingStation"})
            key = params.get("key")
            if key is None:
                raise HTTPException(
                    status_code=400,
                    detail="Missing 'key' for SetVariables",
                )
            data = [
                {
                    "component": component,
                    "variable": {"name": key},
                    "attributeType": "Actual",
                    "value": params.get("value"),
                }
            ]
        return call201.SetVariables(set_variable_data=data)

    # ---------- main dispatcher ----------------------------------------
    def build(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "RequestStartTransaction":
            return call201.RequestStartTransaction(
                id_token={"idToken": params.get("id_tag", "UNKNOWN"), "type": "Central"},
                remote_start_id=params.get("remote_start_id", 1234),
            )

        if action == "RequestStopTransaction":
            return call201.RequestStopTransaction(
                transaction_id=params["transaction_id"]
            )

        if action == "GetBaseReport":
            return call201.GetBaseReport(
                request_id=params.get("requestId", 55),
                report_base=params.get("reportBase", "FullInventory"),
            )

        if action == "GetVariables":
            # spec: get_variable_data           -> lijst met dicts
            return call201.GetVariables(
                get_variable_data=params.get("key", [])
            )

        if action == "SetVariables":
            return self._build_set_variables(params)

        raise HTTPException(
            status_code=400, detail=f"Unknown OCPP 2.0.1 action: {action}"
        )
