import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from application.event_bus import bus
from config import settings

log = logging.getLogger("InfluxDBService")


class InfluxDBService:
    """
    Luistert op alle EventBus-events en schrijft ze naar InfluxDB.
    – MeterValues  → per sampled_value een punt (numeriek ‘value’-veld)
    – ConfigurationChanged → numeriek of string, eigen measurement
    – Alle overige events → alleen veld ‘count’ = 1 (geen strings!)
    """

    _EVENTS: List[str] = [
        "MeterValues",
        "Heartbeat",
        "StatusNotification",
        "StartTransaction",
        "StopTransaction",
        "BootNotification",
        "Authorize",
        "ChargePointConnected",
        "ChargePointDisconnected",
        "ConfigurationChanged",
        "NotifyEvent",
        "SecurityEventNotification",
    ]

    # -------------------------------------------------------------- init
    def __init__(self) -> None:
        s = settings()

        self._client = InfluxDBClient(
            url=s.INFLUX_URL, token=s.INFLUX_TOKEN, org=s.INFLUX_ORG
        )
        self._write = self._client.write_api(write_options=SYNCHRONOUS)

        for evt in self._EVENTS:
            bus.subscribe(evt, self._make_handler(evt))

        log.info(
            "InfluxDBService ready → %s (org=%s, bucket=%s)",
            s.INFLUX_URL, s.INFLUX_ORG, s.INFLUX_BUCKET
        )

    # ------------------------------------------------------ handlers
    def _make_handler(self, evt_name: str):
        async def _handler(**payload):
            try:
                await self._process_event(evt_name, **payload)
            except Exception as exc:  # pragma: no cover
                log.error("Influx write failed: %s", exc, exc_info=True)

        return _handler

    async def _process_event(self, event: str, **payload) -> None:
        cp_id: str = payload.get("charge_point_id", "")
        ocpp_version: str = payload.get("ocpp_version", "")
        body: Dict[str, Any] = payload.get("payload", payload)

        if event == "MeterValues":
            await self._handle_meter_values(cp_id, ocpp_version, body)
            return

        if event == "ConfigurationChanged":
            await self._handle_config_change(cp_id, body)
            return

        # --- generieke events: alleen numeriek veld ‘count’ ----------------
        point = (
            Point(event)
            .tag("cp_id", cp_id)
            .tag("ocpp", ocpp_version)
            .field("count", 1)
            .time(datetime.now(timezone.utc), WritePrecision.NS)
        )
        # Wil je tóch de ruwe payload bewaren?  Zet de volgende regel aan:
        # point.tag("raw", json.dumps(body)[:250])   # max 250 chars als tag

        self._write.write(bucket=settings().INFLUX_BUCKET, record=point)

    # ------------------------------------------------ MeterValues
    async def _handle_meter_values(
        self, cp_id: str, ocpp_version: str, body: Dict[str, Any]
    ) -> None:
        connector = body.get("connector_id")
        for mv in body.get("meter_value", []):
            ts = _iso_to_datetime(mv.get("timestamp"))
            for sv in mv.get("sampled_value", []):
                try:
                    value_num = float(sv.get("value"))
                except (TypeError, ValueError):
                    continue  # skip non-numeric

                point = (
                    Point("meter_value")
                    .tag("cp_id", cp_id)
                    .tag("connector", str(connector))
                    .tag("measurand", sv.get("measurand", ""))
                    .tag("phase", sv.get("phase", ""))
                    .tag("location", sv.get("location", ""))
                    .tag("unit", sv.get("unit", ""))
                    .field("value", value_num)
                    .time(ts, WritePrecision.NS)
                )
                self._write.write(bucket=settings().INFLUX_BUCKET, record=point)

    # ------------------------------------------------ ConfigurationChanged
    async def _handle_config_change(
        self, cp_id: str, body: Dict[str, Any]
    ) -> None:
        p = body.get("parameters", {})
        key = p.get("key")
        raw_val = p.get("value")

        point = (
            Point("configuration_change")
            .tag("cp_id", cp_id)
            .tag("key", key)
            .time(datetime.now(timezone.utc), WritePrecision.NS)
        )

        try:
            point.field("value", float(raw_val))
        except (TypeError, ValueError):
            point.field("value_str", str(raw_val))

        self._write.write(bucket=settings().INFLUX_BUCKET, record=point)


# ---------------------------------------------------------- utils
def _iso_to_datetime(iso_str: str | None) -> datetime:
    if not iso_str:
        return datetime.now(timezone.utc)
    try:
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        return datetime.fromisoformat(iso_str).astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)
