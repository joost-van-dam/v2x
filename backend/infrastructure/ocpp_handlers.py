"""Version-specifieke OCPP‑handler‑klassen met veilige defaults.

Alle inkomende OCPP‑acties waar een simulator/echte laadpaal standaard mee
komt, krijgen hier minimaal **één** handler.  Zo voorkomt de ocpp‑lib dat er
`NotImplementedError` gegooid wordt.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ocpp.routing import on                          # type: ignore
from ocpp.v16 import ChargePoint as _BaseV16         # type: ignore
from ocpp.v16 import call_result as _res16           # type: ignore
from ocpp.v201 import ChargePoint as _BaseV201       # type: ignore
from ocpp.v201 import call_result as _res201         # type: ignore

from application.event_bus import bus 

__all__ = ["V16Handler", "V201Handler"]
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OCPP 1.6
# ---------------------------------------------------------------------------
class V16Handler(_BaseV16):
    """Basisset met alle gangbare OCPP‑1.6 acties."""

    # ----------------------------------------------------------------- boot
    @on("BootNotification")
    async def on_boot_notification(
        self,
        charge_point_model: str,
        charge_point_vendor: str,
        **kw,
    ):
        logger.info("[OCPP‑1.6] BootNotification – model=%s vendor=%s", charge_point_model, charge_point_vendor)
        return _res16.BootNotification(current_time=datetime.utcnow().isoformat(), interval=10, status="Accepted")

    # ---------------------------------------------------------------- hb
    @on("Heartbeat")
    async def on_heartbeat(self):
        logger.debug("[OCPP‑1.6] Heartbeat from %s", self.id)
        return _res16.Heartbeat(current_time=datetime.utcnow().isoformat())

    # ---------------------------------------------------------------- auth
    @on("Authorize")
    async def on_authorize(self, id_tag: str):
        logger.debug("[OCPP‑1.6] Authorize – idTag=%s", id_tag)
        return _res16.Authorize(id_tag_info={"status": "Accepted"})

    # ------------------------------------------------------- tx start/stop
    @on("StartTransaction")
    async def on_start_transaction(
        self,
        connector_id: int,
        id_tag: str,
        meter_start: int,
        timestamp: str,
        **kw,
    ):
        logger.debug(
            "[OCPP‑1.6] StartTransaction – conn=%s idTag=%s meterStart=%s ts=%s",
            connector_id,
            id_tag,
            meter_start,
            timestamp,
        )
        return _res16.StartTransaction(transaction_id=1, id_tag_info={"status": "Accepted"})

    @on("StopTransaction")
    async def on_stop_transaction(
        self,
        meter_stop: int,
        timestamp: str,
        transaction_id: int,
        id_tag: str | None = None,
        reason: str | None = None,
        **kw,
    ):
        logger.debug(
            "[OCPP‑1.6] StopTransaction – txId=%s reason=%s meterStop=%s ts=%s",
            transaction_id,
            reason,
            meter_stop,
            timestamp,
        )
        return _res16.StopTransaction(id_tag_info={"status": "Accepted"})

    # ------------------------------------------------------- status / meter
    @on("StatusNotification")
    async def on_status_notification(self, **kw: Any):
        logger.debug("[OCPP‑1.6] StatusNotification – data=%s", kw)
        return _res16.StatusNotification()

    # ----------------------------------------------------------- MeterValues
    @on("MeterValues")
    async def on_meter_values(self, **kw: Any):
        logger.info("[OCPP‑1.6] MeterValues – %s", kw)
        # 1) dispatch event
        await bus.publish("MeterValues", charge_point_id=self.id, ocpp_version="1.6", payload=kw)
        # 2) ack
        return _res16.MeterValues()



# ---------------------------------------------------------------------------
# OCPP 2.0.1 – voor de volledigheid; hier wijzigt niets
# ---------------------------------------------------------------------------
class V201Handler(_BaseV201):
    """Minimale handler-set voor OCPP 2.0.1."""

    @on("BootNotification")
    async def on_boot_notification(self, charging_station, reason, **kw):
        logger.info("[OCPP‑2.0.1] BootNotification – reason=%s", reason)
        return _res201.BootNotification(current_time=datetime.utcnow().isoformat(), interval=10, status="Accepted")

    @on("Heartbeat")
    async def on_heartbeat(self):
        return _res201.Heartbeat(current_time=datetime.utcnow().isoformat())

    @on("StatusNotification")
    async def on_status_notification(self, **kw: Any):
        return _res201.StatusNotification()

    @on("MeterValues")
    async def on_meter_values(self, **kw: Any):
        logger.info("[OCPP‑2.0.1] MeterValues – %s", kw)
        await bus.publish("MeterValues", charge_point_id=self.id, ocpp_version="2.0.1", payload=kw)
        return _res201.MeterValues()
