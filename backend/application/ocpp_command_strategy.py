from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from fastapi import HTTPException

from ocpp.v16 import call as call16      # type: ignore
from ocpp.v201 import call as call201    # type: ignore


class CommandStrategy(ABC):
    @abstractmethod
    def build(self, action: str, params: Dict[str, Any]) -> Any: ...


# ---------------------------------------------------------------------------#
#  OCPP 1.6
# ---------------------------------------------------------------------------#
class V16CommandStrategy(CommandStrategy):
    def build(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "RemoteStartTransaction":
            return call16.RemoteStartTransaction(
                id_tag=params.get("id_tag", "UNKNOWN"),
                connector_id=params.get("connector_id"),
                charging_profile=params.get("charging_profile"),
            )

        if action == "RemoteStopTransaction":
            return call16.RemoteStopTransaction(transaction_id=params["transaction_id"])

        if action == "ChangeConfiguration":
            try:
                return call16.ChangeConfiguration(key=params["key"], value=params["value"])
            except KeyError:
                raise HTTPException(status_code=400, detail="Missing 'key' or 'value'")

        if action == "GetConfiguration":
            return call16.GetConfiguration(key=params.get("key", []))

        raise HTTPException(status_code=400, detail=f"Unknown OCPP 1.6 action: {action}")


# ---------------------------------------------------------------------------#
#  OCPP 2.0.1
# ---------------------------------------------------------------------------#
class V201CommandStrategy(CommandStrategy):
    def build(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "RequestStartTransaction":
            return call201.RequestStartTransaction(
                id_token={"idToken": params.get("id_tag", "UNKNOWN"), "type": "Central"},
                remote_start_id=params.get("remote_start_id", 1234),
            )

        if action == "RequestStopTransaction":
            return call201.RequestStopTransaction(transaction_id=params["transaction_id"])

        if action == "GetBaseReport":
            return call201.GetBaseReport(
                request_id=params.get("requestId", 55),
                report_base=params.get("reportBase", "FullInventory"),
            )

        if action == "GetVariables":
            key: List[Dict[str, Any]] = params.get("key", [])
            if not key:
                raise HTTPException(status_code=400, detail="'key' list required")
            return call201.GetVariables(get_variable_data=key)

        if action == "SetVariables":
            try:
                comp = params["key"]["component"]
                var_name = params["key"]["variable_name"]
                value = params["value"]
            except KeyError:
                raise HTTPException(status_code=400, detail="Missing key/value data")

            return call201.SetVariables(
                set_variable_data=[
                    {
                        "component": comp,
                        "variable": {"name": var_name},
                        "attribute_value": value,
                    }
                ]
            )

        raise HTTPException(status_code=400, detail=f"Unknown OCPP 2.0.1 action: {action}")
