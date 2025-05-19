"""Version-specifieke OCPP-handler-klassen + EventBus-bridge.

Fix (19 mei 2025)
-----------------
Voor OCPP 2.0.1 kwamen de configuratiewaarden steeds als `null` terug.
Dat bleek te liggen aan het feit dat sommige laadpunten (en enkele
implementaties van de Python-OCPP-lib) in `NotifyReport.reportData[*].
variableAttribute[*]` het veld **`attribute_value`** óf **`attributeValue`**
gebruiken in plaats van `value`.

In `V201Handler.on_notify_report()` wordt daarom nu robuust gekeken naar
alle drie de varianten:

    value = attr.get("value",
                     attr.get("attribute_value",
                              attr.get("attributeValue")))

Verder wordt een eventuele string `"null"` ook genegeerd, zodat alleen
echte waarden worden meegenomen.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from ocpp.routing import on                               # type: ignore
from ocpp.v16 import ChargePoint as _BaseV16              # type: ignore
from ocpp.v16 import call_result as _res16                # type: ignore
from ocpp.v201 import ChargePoint as _BaseV201            # type: ignore
from ocpp.v201 import call_result as _res201              # type: ignore

from application.event_bus import bus

__all__ = ["V16Handler", "V201Handler"]
log = logging.getLogger(__name__)


async def _publish(event: str, cp_id: str, ocpp_version: str, **payload):
    """Kleine helper om alles via de centrale EventBus weg te zetten."""
    await bus.publish(
        event, charge_point_id=cp_id, ocpp_version=ocpp_version, payload=payload
    )


# ------------------------------------------------------------------------------
# OCPP 1.6
# ------------------------------------------------------------------------------
class V16Handler(_BaseV16):
    """Basis-handlers voor OCPP 1.6 – ongewijzigd."""

    @on("BootNotification")
    async def on_boot_notification(self, charge_point_model, charge_point_vendor, **kw):
        await _publish(
            "BootNotification",
            self.id,
            "1.6",
            model=charge_point_model,
            vendor=charge_point_vendor,
        )
        return _res16.BootNotification(
            current_time=datetime.utcnow().isoformat(), interval=10, status="Accepted"
        )

    @on("Heartbeat")
    async def on_heartbeat(self):
        await _publish("Heartbeat", self.id, "1.6", ts=datetime.utcnow().isoformat())
        return _res16.Heartbeat(current_time=datetime.utcnow().isoformat())

    @on("Authorize")
    async def on_authorize(self, id_tag: str):
        await _publish("Authorize", self.id, "1.6", id_tag=id_tag)
        return _res16.Authorize(id_tag_info={"status": "Accepted"})

    @on("StartTransaction")
    async def on_start_transaction(
        self, connector_id, id_tag, meter_start, timestamp, **kw
    ):
        await _publish(
            "StartTransaction",
            self.id,
            "1.6",
            connector_id=connector_id,
            id_tag=id_tag,
            meter_start=meter_start,
            timestamp=timestamp,
        )
        return _res16.StartTransaction(
            transaction_id=1, id_tag_info={"status": "Accepted"}
        )

    @on("StopTransaction")
    async def on_stop_transaction(
        self, meter_stop, timestamp, transaction_id, id_tag=None, reason=None, **kw
    ):
        await _publish(
            "StopTransaction",
            self.id,
            "1.6",
            meter_stop=meter_stop,
            timestamp=timestamp,
            transaction_id=transaction_id,
            reason=reason,
        )
        return _res16.StopTransaction(id_tag_info={"status": "Accepted"})

    @on("StatusNotification")
    async def on_status_notification(self, **kw: Any):
        await _publish("StatusNotification", self.id, "1.6", **kw)
        return _res16.StatusNotification()

    @on("MeterValues")
    async def on_meter_values(self, **kw: Any):
        await _publish("MeterValues", self.id, "1.6", **kw)
        return _res16.MeterValues()


# ------------------------------------------------------------------------------
# OCPP 2.0.1
# ------------------------------------------------------------------------------
class V201Handler(_BaseV201):
    """
    Handler-set voor OCPP 2.0.1.

    •   Cacht `NotifyReport`-gegevens in `self.latest_config`.
    •   Zet `self.notify_report_done → True` zodra het laatste deel binnen is.
    •   **19-05-2025** – Nu ook compatibel met `attribute_value` / `attributeValue`.
    """

    # ---------- lifecycle -----------------------------------------------------
    @on("BootNotification")
    async def on_boot_notification(self, charging_station, reason, **kw):
        await _publish(
            "BootNotification",
            self.id,
            "2.0.1",
            reason=reason,
            station=charging_station,
        )
        return _res201.BootNotification(
            current_time=datetime.utcnow().isoformat(), interval=10, status="Accepted"
        )

    @on("Heartbeat")
    async def on_heartbeat(self):
        await _publish("Heartbeat", self.id, "2.0.1", ts=datetime.utcnow().isoformat())
        return _res201.Heartbeat(current_time=datetime.utcnow().isoformat())

    # ---------- status / tx / meter ------------------------------------------
    @on("StatusNotification")
    async def on_status_notification(self, **kw: Any):
        await _publish("StatusNotification", self.id, "2.0.1", **kw)
        return _res201.StatusNotification()

    @on("StartTransaction")
    async def on_start_transaction(self, **kw: Any):
        await _publish("StartTransaction", self.id, "2.0.1", **kw)
        return _res201.StartTransaction()

    @on("StopTransaction")
    async def on_stop_transaction(self, **kw: Any):
        await _publish("StopTransaction", self.id, "2.0.1", **kw)
        return _res201.StopTransaction()

    @on("MeterValues")
    async def on_meter_values(self, **kw: Any):
        await _publish("MeterValues", self.id, "2.0.1", **kw)
        return _res201.MeterValues()

    # ---------- events --------------------------------------------------------
    @on("NotifyEvent")
    async def on_notify_event(self, **kw: Any):
        await _publish("NotifyEvent", self.id, "2.0.1", **kw)
        return _res201.NotifyEvent()

    # ---------- NotifyReport (config) ----------------------------------------
    @on("NotifyReport")
    async def on_notify_report(
        self,
        generated_at: str,
        report_data: List[Dict[str, Any]],
        request_id: int,
        seq_no: int,
        tbc: bool,
        **kw,
    ):
        # 1) Cache initialiseren bij het eerste pakket
        if seq_no == 0 or not hasattr(self, "latest_config"):
            self.latest_config: List[Dict[str, Any]] = []  # type: ignore[attr-defined]
            self.notify_report_done = False  # type: ignore[attr-defined]

        rows: List[Dict[str, Any]] = []

        for entry in report_data:
            try:
                key = entry["variable"]["name"]

                # 2) Neem de eerste attribute met een bruikbare waarde
                value = None
                readonly = False

                for attr in entry.get("variableAttribute", []):
                    raw_val = attr.get(
                        "value",
                        attr.get(
                            "attribute_value",
                            attr.get("attributeValue"),
                        ),
                    )

                    # negeer lege / string "null"
                    if raw_val not in (None, "", "null"):
                        value = raw_val
                        readonly = attr.get("mutability", "ReadWrite") == "ReadOnly"
                        break

                rows.append({"key": key, "value": value, "readonly": readonly})
            except Exception as exc:  # pragma: no cover
                log.error("NotifyReport parse error: %s", exc, exc_info=True)

        # 3) Buffer uitbreiden
        self.latest_config.extend(rows)  # type: ignore[attr-defined]

        # 4) Laatste pakket?
        if not tbc:
            self.notify_report_done = True  # type: ignore[attr-defined]

        # 5) EventBus-melding + ACK
        await _publish(
            "NotifyReport",
            self.id,
            "2.0.1",
            seq_no=seq_no,
            tbc=tbc,
            generated_at=generated_at,
            data=rows,
        )
        return _res201.NotifyReport()
