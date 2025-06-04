import pytest
import asyncio
import json
from datetime import datetime, timezone

# Omdat we pytest vanuit de repo‐root draaien, is “backend” het package‐niveau
import backend.application.event_bus as event_bus_module
import backend.infrastructure.ocpp_handlers as handlers_module
from backend.infrastructure.ocpp_handlers import V16Handler, V201Handler


@pytest.fixture(autouse=True)
def capture_publish_calls(monkeypatch):
    """
    Mokken van bus.publish op twee plekken:
      • backend.application.event_bus.bus.publish
      • backend.infrastructure.ocpp_handlers.bus.publish
    zodat alle interne calls in handlers worden opgevangen.
    """
    calls: list[tuple[str, dict]] = []

    async def fake_publish(event_name, **kwargs):
        calls.append((event_name, kwargs))

    monkeypatch.setattr(event_bus_module.bus, "publish", fake_publish)
    monkeypatch.setattr(handlers_module.bus, "publish", fake_publish)
    return calls


@pytest.mark.asyncio
async def test_v16_handlers_publish_and_response(capture_publish_calls):
    """
    Test alle on_... methods in V16Handler:
      • Controleer dat bus.publish telkens met de juiste payload wordt aangeroepen.
      • Controleer dat het return‐object de verwachte velden bevat.
    """
    handler = V16Handler("CP1", None)

    # --- BootNotification ---
    resp = await handler.on_boot_notification("ModelX", "VendorY")
    assert capture_publish_calls[-1][0] == "BootNotification"
    _, payload = capture_publish_calls[-1]
    assert payload["charge_point_id"] == "CP1"
    assert payload["ocpp_version"] == "1.6"
    assert payload["payload"]["model"] == "ModelX"
    assert payload["payload"]["vendor"] == "VendorY"
    assert hasattr(resp, "current_time")
    assert hasattr(resp, "interval")
    assert resp.status == "Accepted"

    # --- Heartbeat ---
    resp = await handler.on_heartbeat()
    assert capture_publish_calls[-1][0] == "Heartbeat"
    _, payload = capture_publish_calls[-1]
    assert "ts" in payload["payload"] and payload["payload"]["ts"]
    assert hasattr(resp, "current_time")

    # --- Authorize ---
    resp = await handler.on_authorize("TAG123")
    assert capture_publish_calls[-1][0] == "Authorize"
    _, payload = capture_publish_calls[-1]
    assert payload["payload"]["id_tag"] == "TAG123"
    assert resp.id_tag_info["status"] == "Accepted"

    # --- StartTransaction ---
    now_iso = datetime.now(timezone.utc).isoformat()
    resp = await handler.on_start_transaction(
        connector_id=5, id_tag="TAG5", meter_start=100, timestamp=now_iso
    )
    assert capture_publish_calls[-1][0] == "StartTransaction"
    _, payload = capture_publish_calls[-1]
    assert payload["payload"]["connector_id"] == 5
    assert payload["payload"]["id_tag"] == "TAG5"
    assert payload["payload"]["meter_start"] == 100
    assert payload["payload"]["timestamp"] == now_iso
    assert resp.transaction_id == 1
    assert resp.id_tag_info["status"] == "Accepted"

    # --- StopTransaction ---
    resp = await handler.on_stop_transaction(
        meter_stop=200, timestamp=now_iso, transaction_id=1, reason="Finished"
    )
    assert capture_publish_calls[-1][0] == "StopTransaction"
    _, payload = capture_publish_calls[-1]
    assert payload["payload"]["meter_stop"] == 200
    assert payload["payload"]["transaction_id"] == 1
    assert payload["payload"]["reason"] == "Finished"
    assert resp.id_tag_info["status"] == "Accepted"

    # --- StatusNotification ---
    status_kwargs = {"status": "Available", "error_code": "NoError"}
    resp = await handler.on_status_notification(**status_kwargs)
    assert capture_publish_calls[-1][0] == "StatusNotification"
    _, payload = capture_publish_calls[-1]
    for k, v in status_kwargs.items():
        assert payload["payload"][k] == v
    assert resp

    # --- MeterValues ---
    meter_kwargs = {"meter_value": [{"timestamp": now_iso, "value": 123}]}
    resp = await handler.on_meter_values(**meter_kwargs)
    assert capture_publish_calls[-1][0] == "MeterValues"
    _, payload = capture_publish_calls[-1]
    assert payload["payload"]["meter_value"][0]["value"] == 123
    assert resp


@pytest.mark.asyncio
async def test_v201_handlers_publish_and_response(capture_publish_calls):
    """
    Test alle on_... methods in V201Handler:
      • Controleer dat bus.publish telkens met de juiste payload wordt aangeroepen.
      • Voor StartTransaction en StopTransaction verwachten we AttributeError omdat
        _res201.StartTransaction/StopTransaction niet bestaan.
      • Voor MeterValues verwachten we een geldig return‐object en geen exception.
    """
    handler = V201Handler("CP2", None)

    # --- BootNotification ---
    resp = await handler.on_boot_notification(charging_station="StationA", reason="PowerUp")
    assert capture_publish_calls[-1][0] == "BootNotification"
    _, payload = capture_publish_calls[-1]
    assert payload["charge_point_id"] == "CP2"
    assert payload["ocpp_version"] == "2.0.1"
    assert payload["payload"]["station"] == "StationA"
    assert payload["payload"]["reason"] == "PowerUp"
    assert hasattr(resp, "current_time") and resp.status == "Accepted"

    # --- Heartbeat ---
    resp = await handler.on_heartbeat()
    assert capture_publish_calls[-1][0] == "Heartbeat"
    _, payload = capture_publish_calls[-1]
    assert "ts" in payload["payload"] and payload["payload"]["ts"]
    assert hasattr(resp, "current_time")

    # --- StatusNotification ---
    status_kwargs = {"status": "Unavailable", "error_code": "EvError"}
    resp = await handler.on_status_notification(**status_kwargs)
    assert capture_publish_calls[-1][0] == "StatusNotification"
    _, payload = capture_publish_calls[-1]
    assert payload["payload"]["status"] == "Unavailable"
    assert resp

    # --- StartTransaction → verwacht AttributeError ---
    now_iso = datetime.now(timezone.utc).isoformat()
    start_kwargs = {"connector_id": 1, "id_tag": "USER", "timestamp": now_iso}
    with pytest.raises(AttributeError):
        await handler.on_start_transaction(**start_kwargs)
    assert capture_publish_calls[-1][0] == "StartTransaction"

    # --- StopTransaction → verwacht AttributeError ---
    stop_kwargs = {"meter_stop": 300, "timestamp": now_iso, "transaction_id": 2}
    with pytest.raises(AttributeError):
        await handler.on_stop_transaction(**stop_kwargs)
    assert capture_publish_calls[-1][0] == "StopTransaction"

    # --- MeterValues → wél een geldig return‐object, géén exception ---
    meter_kwargs = {"meter_value": [{"timestamp": now_iso, "value": 456}]}
    resp = await handler.on_meter_values(**meter_kwargs)
    assert capture_publish_calls[-1][0] == "MeterValues"
    _, payload = capture_publish_calls[-1]
    assert payload["payload"]["meter_value"][0]["value"] == 456
    assert resp  # object bestaat

    # --- NotifyEvent ---
    event_kwargs = {"event_data": {"key": "val"}}
    resp = await handler.on_notify_event(**event_kwargs)
    assert capture_publish_calls[-1][0] == "NotifyEvent"
    _, payload = capture_publish_calls[-1]
    assert payload["payload"]["event_data"] == {"key": "val"}
    assert resp


@pytest.mark.asyncio
async def test_v201_notify_report_multiple_conditions(capture_publish_calls):
    """
    Test de on_notify_report-logica in V201Handler:
      • seq_no=0 met variableAttribute die wél een “value” bevat.
      • seq_no=1 met lege variableAttribute (geen attrs).
      • tbc=True → notify_report_done blijft False.
      • tbc=False → notify_report_done wordt True.
    """
    handler = V201Handler("CP3", None)

    # --- Eerste report: seq_no=0, attrs met ‘value’ ---
    entry1 = {
        "variable": {"name": "Key1"},
        "component": {"name": "Comp1"},
        "variableCharacteristics": {
            "dataType": "Integer",
            "unit": "A",
            "valuesList": [1, 2, 3],
        },
        "variableAttribute": [
            {
                "value": "Val1",
                "mutability": "ReadWrite",
                "persistent": True,
                "constant": False,
                "type": "TypeX",
            }
        ],
    }
    generated_at = "2025-06-04T12:00:00Z"
    await handler.on_notify_report(
        generated_at=generated_at,
        report_data=[entry1],
        request_id=10,
        seq_no=0,
        tbc=True,
    )

    # Controleer eerste cache-item
    assert len(handler.latest_config) == 1
    item = handler.latest_config[0]
    assert item["key"] == "Key1"
    assert item["value"] == "Val1"
    assert item["readonly"] is False
    assert item["data_type"] == "Integer"
    assert item["unit"] == "A"
    assert item["values_list"] == [1, 2, 3]
    assert handler.notify_report_done is False

    # Controleer publicatie
    assert capture_publish_calls[-1][0] == "NotifyReport"
    _, payload = capture_publish_calls[-1]
    assert payload["payload"]["seq_no"] == 0
    assert payload["payload"]["tbc"] is True
    assert payload["payload"]["generated_at"] == generated_at

    # --- Tweede report: seq_no=1, lege attrs, tbc=False ---
    entry2 = {
        "variable": {"name": "Key2"},
        "component": {},
        "variableCharacteristics": {},
        "variableAttribute": [],
    }
    await handler.on_notify_report(
        generated_at=generated_at,
        report_data=[entry2],
        request_id=10,
        seq_no=1,
        tbc=False,
    )

    # Controleer tweede cache-item en tbc-flag
    assert len(handler.latest_config) == 2
    item2 = handler.latest_config[1]
    assert item2["key"] == "Key2"
    assert item2["value"] is None
    # Lege variableAttribute → default mutability="ReadOnly" → readonly=True
    assert item2["readonly"] is True
    assert handler.notify_report_done is True

    # Nogmaals publicatiecontrole
    assert capture_publish_calls[-1][0] == "NotifyReport"
    _, payload2 = capture_publish_calls[-1]
    assert payload2["payload"]["seq_no"] == 1
    assert payload2["payload"]["tbc"] is False
    assert payload2["payload"]["generated_at"] == generated_at
