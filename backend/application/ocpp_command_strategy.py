from __future__ import annotations

from typing import Any, Dict, List

from fastapi import HTTPException

from ocpp.v16 import call as call16          # type: ignore
from ocpp.v201 import call as call201        # type: ignore


class CommandStrategy:
    """
    Abstracte basis – iedere OCPP-versie heeft zijn eigen concrete strategy-klasse.
    """
    def build(self, action: str, params: Dict[str, Any]) -> Any:       # pragma: no cover
        raise NotImplementedError


# --------------------------------------------------------------------------- #
#  OCPP 1.6
# --------------------------------------------------------------------------- #
class V16CommandStrategy(CommandStrategy):
    """
    Bouwt Call-objecten voor OCPP 1.6 (J-profiel) op basis van een
    {action, params}-paar afkomstig uit de REST-laag.
    """

    def build(self, action: str, params: Dict[str, Any]) -> Any:
        # ---------------- RemoteStartTransaction ----------------
        if action == "RemoteStartTransaction":
            # connectorId is optioneel; alleen doorgeven als er een geldige waarde
            kwargs: Dict[str, Any] = {
                "id_tag": params.get("id_tag", "UNKNOWN"),
            }
            if params.get("connector_id") is not None:
                kwargs["connector_id"] = params["connector_id"]
            if params.get("charging_profile") is not None:
                kwargs["charging_profile"] = params["charging_profile"]

            return call16.RemoteStartTransaction(**kwargs)

        # ---------------- RemoteStopTransaction -----------------
        if action == "RemoteStopTransaction":
            try:
                return call16.RemoteStopTransaction(
                    transaction_id=params["transaction_id"]
                )
            except KeyError:
                raise HTTPException(
                    status_code=400, detail="Missing 'transaction_id'"
                ) from None

        # ---------------- ChangeConfiguration -------------------
        if action == "ChangeConfiguration":
            try:
                return call16.ChangeConfiguration(
                    key=params["key"], value=params["value"]
                )
            except KeyError:
                raise HTTPException(
                    status_code=400, detail="Missing 'key' or 'value'"
                ) from None

        # ---------------- GetConfiguration ----------------------
        if action == "GetConfiguration":
            return call16.GetConfiguration(key=params.get("key", []))

        # ---------------- SecurityBootNotification --------------
        if action == "SecurityBootNotification":
            return call16.SecurityBootNotification(
                charge_box_serial_number=params.get("charge_box_serial_number", "UNKNOWN"),
                firmware_version=params.get("firmware_version", "UNKNOWN"),
                iccid=params.get("iccid", "UNKNOWN"),
                imsi=params.get("imsi", "UNKNOWN"),
                meter_type=params.get("meter_type", "UNKNOWN"),
                meter_serial_number=params.get("meter_serial_number", "UNKNOWN"),
            )

        # --------------------------------------------------------
        raise HTTPException(status_code=400, detail=f"Unknown OCPP 1.6 action: {action}")


# --------------------------------------------------------------------------- #
#  OCPP 2.0.1
# --------------------------------------------------------------------------- #
class V201CommandStrategy(CommandStrategy):
    """
    Bouwt Call-objecten voor OCPP 2.0.1 (JSON schema 2021-06).
    """

    def build(self, action: str, params: Dict[str, Any]) -> Any:
        # ---------------- RequestStartTransaction ---------------
        if action == "RequestStartTransaction":
            return call201.RequestStartTransaction(
                id_token={
                    "idToken": params.get("id_tag", "UNKNOWN"),
                    "type": "Central",
                },
                remote_start_id=params.get("remote_start_id", 1234),
            )

        # ---------------- RequestStopTransaction ----------------
        if action == "RequestStopTransaction":
            try:
                return call201.RequestStopTransaction(
                    transaction_id=params["transaction_id"]
                )
            except KeyError:
                raise HTTPException(
                    status_code=400, detail="Missing 'transaction_id'"
                ) from None

        # ---------------- GetBaseReport -------------------------
        if action == "GetBaseReport":
            return call201.GetBaseReport(
                request_id=params.get("requestId", 55),
                report_base=params.get("reportBase", "FullInventory"),
            )

        # ---------------- GetVariables --------------------------
        if action == "GetVariables":
            key: List[Dict[str, Any]] = params.get("key", [])
            if not key:
                raise HTTPException(status_code=400, detail="'key' list required")
            return call201.GetVariables(get_variable_data=key)

        # ---------------- SetVariables --------------------------
        if action == "SetVariables":
            try:
                comp = params["key"]["component"]
                var_name = params["key"]["variable_name"]
                value = params["value"]
            except KeyError:
                raise HTTPException(status_code=400, detail="Missing key/value data") from None

            return call201.SetVariables(
                set_variable_data=[
                    {
                        "component": comp,
                        "variable": {"name": var_name},
                        "attribute_value": value,
                    }
                ]
            )

        # --------------------------------------------------------
        raise HTTPException(status_code=400, detail=f"Unknown OCPP 2.0.1 action: {action}")
