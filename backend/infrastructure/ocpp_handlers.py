"""Version-specifieke OCPP-handler-klassen met veilige defaults + EventBus-bridge."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ocpp.routing import on                            # type: ignore
from ocpp.v16 import ChargePoint as _BaseV16           # type: ignore
from ocpp.v16 import call_result as _res16             # type: ignore
from ocpp.v201 import ChargePoint as _BaseV201         # type: ignore
from ocpp.v201 import call_result as _res201           # type: ignore

from application.event_bus import bus

__all__ = ["V16Handler", "V201Handler"]
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper om events uniform te pushen
# ---------------------------------------------------------------------------
async def _publish(event: str, cp_id: str, ocpp_version: str, **payload):
    """Dispatch één event naar de in-process EventBus."""
    await bus.publish(
        event, charge_point_id=cp_id, ocpp_version=ocpp_version, payload=payload
    )


# ---------------------------------------------------------------------------
# OCPP 1.6 – basisset handlers
# ---------------------------------------------------------------------------
class V16Handler(_BaseV16):
    """Handlerset voor OCPP 1.6‐berichten."""

    # BootNotification -------------------------------------------------
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

    # Heartbeat --------------------------------------------------------
    @on("Heartbeat")
    async def on_heartbeat(self):
        await _publish("Heartbeat", self.id, "1.6", ts=datetime.utcnow().isoformat())
        return _res16.Heartbeat(current_time=datetime.utcnow().isoformat())

    # Authorize --------------------------------------------------------
    @on("Authorize")
    async def on_authorize(self, id_tag: str):
        await _publish("Authorize", self.id, "1.6", id_tag=id_tag)
        return _res16.Authorize(id_tag_info={"status": "Accepted"})

    # StartTransaction / StopTransaction ------------------------------
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

    # StatusNotification ----------------------------------------------
    @on("StatusNotification")
    async def on_status_notification(self, **kw: Any):
        await _publish("StatusNotification", self.id, "1.6", **kw)
        return _res16.StatusNotification()

    # MeterValues ------------------------------------------------------
    @on("MeterValues")
    async def on_meter_values(self, **kw: Any):
        await _publish("MeterValues", self.id, "1.6", **kw)
        return _res16.MeterValues()


# ---------------------------------------------------------------------------
# OCPP 2.0.1 – basisset handlers
# ---------------------------------------------------------------------------
class V201Handler(_BaseV201):
    """Handlerset voor OCPP 2.0.1‐berichten."""

    # BootNotification -------------------------------------------------
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

    # Heartbeat --------------------------------------------------------
    @on("Heartbeat")
    async def on_heartbeat(self):
        await _publish("Heartbeat", self.id, "2.0.1", ts=datetime.utcnow().isoformat())
        return _res201.Heartbeat(current_time=datetime.utcnow().isoformat())

    # StatusNotification ----------------------------------------------
    @on("StatusNotification")
    async def on_status_notification(self, **kw: Any):
        await _publish("StatusNotification", self.id, "2.0.1", **kw)
        return _res201.StatusNotification()

    # StartTransaction / StopTransaction ------------------------------
    @on("StartTransaction")
    async def on_start_transaction(self, **kw: Any):
        await _publish("StartTransaction", self.id, "2.0.1", **kw)
        return _res201.StartTransaction()

    @on("StopTransaction")
    async def on_stop_transaction(self, **kw: Any):
        await _publish("StopTransaction", self.id, "2.0.1", **kw)
        return _res201.StopTransaction()

    # MeterValues ------------------------------------------------------
    @on("MeterValues")
    async def on_meter_values(self, **kw: Any):
        await _publish("MeterValues", self.id, "2.0.1", **kw)
        return _res201.MeterValues()

    # NotifyEvent ------------------------------------------------------  (al toegevoegd)
    @on("NotifyEvent")
    async def on_notify_event(self, **kw: Any):
        await _publish("NotifyEvent", self.id, "2.0.1", **kw)
        return _res201.NotifyEvent()

    # NotifyReport -----------------------------------------------------  ←  NIEUW
    @on("NotifyReport")
    async def on_notify_report(self, **kw: Any):
        """
        Handler voor NotifyReport – antwoord op GetBaseReport / GetReport.
        Schrijft het ruwe bericht naar de EventBus & stuurt een lege ACK.
        """
        await _publish("NotifyReport", self.id, "2.0.1", **kw)
        return _res201.NotifyReport()
