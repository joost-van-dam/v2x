from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from fastapi import HTTPException

from ocpp.v16 import call as call16      # type: ignore
from ocpp.v201 import call as call201    # type: ignore


class CommandStrategy(ABC):
    """Strategy-interface: vertaal een generic *action + parameters*
    naar een concreet `ocpp.call.*` object dat door `ChargePoint.call()` kan.
    """

    @abstractmethod
    def build(self, action: str, params: dict[str, Any]) -> Any: ...


# ---------------------------------------------------------------------
# Concrete strategieën
# ---------------------------------------------------------------------
class V16CommandStrategy(CommandStrategy):
    """Mapping voor OCPP 1.6."""

    def build(self, action: str, params: dict[str, Any]) -> Any:
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


class V201CommandStrategy(CommandStrategy):
    """Mapping voor OCPP 2.0.1."""

    def build(self, action: str, params: dict[str, Any]) -> Any:
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
            return call201.GetVariablesRequest(
                get_variable_data=params.get("key", [])
            )

        if action == "SetVariables":
            return call201.SetVariablesRequest(
                set_variable_data={
                    "key": params.get("key"),
                    "value": params.get("value"),
                }
            )

        raise HTTPException(
            status_code=400, detail=f"Unknown OCPP 2.0.1 action: {action}"
        )
