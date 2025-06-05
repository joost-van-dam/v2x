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
    Luistert op *alle* EventBus-events en schrijft ze naar InfluxDB 2.x
    in bucket **v2x_bucket**.  MeterValues en ConfigurationChanged krijgen
    een wat uitgebreidere parsing zodat je straks mooie grafieken kunt
    maken per laadpaal.
    """

    _EVENTS: List[str] = [
        # core + extra
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

    # ------------------------------------------------------------------ init
    def __init__(self) -> None:
        s = settings()

        self._client = InfluxDBClient(
            url=s.INFLUX_URL, token=s.INFLUX_TOKEN, org=s.INFLUX_ORG
        )
        self._write = self._client.write_api(write_options=SYNCHRONOUS)

        # abonnementen op alle events
        for evt in self._EVENTS:
            bus.subscribe(evt, self._make_handler(evt))

        log.info(
            "InfluxDBService ready → writing to %s (org=%s, bucket=%s)",
            s.INFLUX_URL, s.INFLUX_ORG, s.INFLUX_BUCKET
        )

    # ---------------------------------------------------------------- helpers
    def _make_handler(self, evt_name: str):
        async def _handler(**payload):
            try:
                await self._process_event(evt_name, **payload)
            except Exception as exc:  # pragma: no cover
                log.error("Influx write failed: %s", exc, exc_info=True)

        return _handler

    # ---------------------------------------------------------------- writer
    async def _process_event(self, event: str, **payload) -> None:
        cp_id: str = payload.get("charge_point_id", "")
        occp_version: str = payload.get("ocpp_version", "")
        body: Dict[str, Any] = payload.get("payload", payload)

        if event == "MeterValues":
            await self._handle_meter_values(cp_id, occp_version, body)
            return

        if event == "ConfigurationChanged":
            await self._handle_config_change(cp_id, body)
            return

        # generic fallback – plaatst hele payload als JSON-string
        point = (
            Point(event)
            .tag("cp_id", cp_id)
            .tag("ocpp", occp_version)
            .field("data", json.dumps(body))
            .time(datetime.now(timezone.utc), WritePrecision.NS)
        )
        self._write.write(bucket=settings().INFLUX_BUCKET, record=point)

    # ---------------------------------------------------- specialised events
    async def _handle_meter_values(
        self, cp_id: str, occp_version: str, body: Dict[str, Any]
    ) -> None:
        connector = body.get("connector_id")
        for mv in body.get("meter_value", []):
            ts = _iso_to_datetime(mv.get("timestamp"))
            for sv in mv.get("sampled_value", []):
                value_raw = sv.get("value")
                try:
                    value_num = float(value_raw)
                except (TypeError, ValueError):
                    # niet-numeriek → skip (grafieken hebben nummers nodig)
                    continue

                point = (
                    Point("meter_value")
                    .tag("cp_id", cp_id)
                    .tag("connector", str(connector))
                    .tag("measurand", sv.get("measurand", "Unknown"))
                    .tag("phase", sv.get("phase", ""))
                    .tag("location", sv.get("location", ""))
                    .tag("unit", sv.get("unit", ""))
                    .field("value", value_num)
                    .time(ts, WritePrecision.NS)
                )
                self._write.write(bucket=settings().INFLUX_BUCKET, record=point)

    async def _handle_config_change(
        self, cp_id: str, body: Dict[str, Any]
    ) -> None:
        params = body.get("parameters", {})
        key = params.get("key")
        val_raw = params.get("value")
        try:
            val = float(val_raw)
        except (TypeError, ValueError):
            # prima om als string te bewaren voor non-numerieke waarden
            point = (
                Point("configuration_change")
                .tag("cp_id", cp_id)
                .tag("key", key)
                .field("value_str", str(val_raw))
                .time(datetime.now(timezone.utc), WritePrecision.NS)
            )
        else:
            point = (
                Point("configuration_change")
                .tag("cp_id", cp_id)
                .tag("key", key)
                .field("value", val)
                .time(datetime.now(timezone.utc), WritePrecision.NS)
            )
        self._write.write(bucket=settings().INFLUX_BUCKET, record=point)


# ---------------------------------------------------------------- utilities
def _iso_to_datetime(iso_str: str | None) -> datetime:
    """ISO → `datetime`, fallback naar *nu* bij ongeldige input."""
    if not iso_str:
        return datetime.now(timezone.utc)
    try:
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        return datetime.fromisoformat(iso_str).astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)
