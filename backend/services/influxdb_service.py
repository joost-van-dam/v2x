import logging
from application.event_bus import bus

log = logging.getLogger("InfluxDBService")


class InfluxDBService:
    """Subscribe op MeterValues; voorlopig alleen console-log."""

    def __init__(self) -> None:
        bus.subscribe("MeterValues", self._on_meter_values)

    # ---------------------------------------------------------- handler
    def _on_meter_values(self, **payload) -> None:
        log.info("[InfluxDBService] %s", payload)
