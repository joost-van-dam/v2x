"""Version-specifieke OCPP-handler-klassen + EventBus-bridge."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ocpp.routing import on                            # type: ignore
from ocpp.v16 import ChargePoint as _BaseV16           # type: ignore
from ocpp.v16 import call_result as _res16             # type: ignore
from ocpp.v201 import ChargePoint as _BaseV201         # type: ignore
from ocpp.v201 import call_result as _res201           # type: ignore

from application.event_bus import bus

__all__ = ["V16Handler", "V201Handler"]
log = logging.getLogger(__name__)


async def _publish(event: str, cp_id: str, ocpp_version: str, **payload):
    await bus.publish(
        event,
        charge_point_id=cp_id,
        ocpp_version=ocpp_version,
        payload=payload,
    )


# ---------------------------------------------------------------------------
# OCPP 1.6
# ---------------------------------------------------------------------------
class V16Handler(_BaseV16):
    """Basis-handlers voor OCPP 1.6."""

    # ---------------- BootNotification
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
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status="Accepted",
        )

    # ---------------- Heartbeat
    @on("Heartbeat")
    async def on_heartbeat(self):
        await _publish("Heartbeat", self.id, "1.6", ts=datetime.utcnow().isoformat())
        return _res16.Heartbeat(current_time=datetime.utcnow().isoformat())

    # ---------------- Authorize
    @on("Authorize")
    async def on_authorize(self, id_tag: str):
        await _publish("Authorize", self.id, "1.6", id_tag=id_tag)
        return _res16.Authorize(id_tag_info={"status": "Accepted"})

    # ---------------- Start / StopTransaction
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
        self,
        meter_stop,
        timestamp,
        transaction_id,
        id_tag=None,
        reason=None,
        **kw,
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

    # ---------------- StatusNotification
    @on("StatusNotification")
    async def on_status_notification(self, **kw: Any):
        await _publish("StatusNotification", self.id, "1.6", **kw)
        return _res16.StatusNotification()

    # ---------------- MeterValues
    @on("MeterValues")
    async def on_meter_values(self, **kw: Any):
        await _publish("MeterValues", self.id, "1.6", **kw)
        return _res16.MeterValues()


# ---------------------------------------------------------------------------
# OCPP 2.0.1
# ---------------------------------------------------------------------------
class V201Handler(_BaseV201):
    """
    Handler-set voor OCPP 2.0.1.
    • Cachet alle NotifyReport-delen in `self.latest_config`
    • Zet `self.notify_report_done` True zodra *tbc == False*
    """

    # ---------------- BootNotification
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
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status="Accepted",
        )

    # ---------------- Heartbeat
    @on("Heartbeat")
    async def on_heartbeat(self):
        await _publish("Heartbeat", self.id, "2.0.1", ts=datetime.utcnow().isoformat())
        return _res201.Heartbeat(current_time=datetime.utcnow().isoformat())

    # ---------------- Status / Tx / Meter
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

    # ---------------- NotifyEvent
    @on("NotifyEvent")
    async def on_notify_event(self, **kw: Any):
        await _publish("NotifyEvent", self.id, "2.0.1", **kw)
        return _res201.NotifyEvent()

    # ---------------- NotifyReport  (belangrijk!)
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
        # Initialiseer cache bij start
        if seq_no == 0 or not hasattr(self, "latest_config"):
            self.latest_config: List[Dict[str, Any]] = []
            self.notify_report_done = False  # type: ignore[attr-defined]

        # Parse elk report-item
        for entry in report_data:
            try:
                name: str = entry["variable"]["name"]
                component: Dict[str, Any] = entry.get("component", {})
                characteristics: Dict[str, Any] = entry.get(
                    "variableCharacteristics", {}
                )
                attrs: List[Dict[str, Any]] = entry.get("variableAttribute", [])

                # kies de *beste* attribute:
                best_attr: Optional[Dict[str, Any]] = next(
                    (a for a in attrs if a.get("value") is not None), None
                )
                if best_attr is None:
                    best_attr = attrs[0] if attrs else {}

                self.latest_config.append(
                    {
                        "key": name,
                        "value": best_attr.get("value"),
                        "readonly": best_attr.get("mutability", "ReadOnly")
                        == "ReadOnly",
                        # extra velden voor debugging / UI
                        "mutability": best_attr.get("mutability"),
                        "persistent": best_attr.get("persistent"),
                        "constant": best_attr.get("constant"),
                        "attribute_type": best_attr.get("type"),
                        "data_type": characteristics.get("dataType"),
                        "unit": characteristics.get("unit"),
                        "values_list": characteristics.get("valuesList"),
                        "component": component,
                    }
                )
            except Exception as exc:  # pragma: no cover
                log.error("NotifyReport-parse error: %s", exc, exc_info=True)

        # laatste deel?
        if not tbc:
            self.notify_report_done = True  # type: ignore[attr-defined]

        # ==== DEBUG-logging =================================================
        try:
            log.debug(
                "[NotifyReport] CP=%s  seqNo=%s  tbc=%s  items=%s",
                self.id,
                seq_no,
                tbc,
                len(report_data),
            )
            # log alléén 1e item om spam te voorkomen
            if report_data:
                log.debug("[NotifyReport] first item: %s", json.dumps(report_data[0], indent=2)[:400])
        except Exception:  # pragma: no cover
            pass
        # ====================================================================

        await _publish(
            "NotifyReport",
            self.id,
            "2.0.1",
            seq_no=seq_no,
            tbc=tbc,
            generated_at=generated_at,
        )
        return _res201.NotifyReport()
