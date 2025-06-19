import pytest
from fastapi.testclient import TestClient

from backend.main import app

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="module")
def ws(client):
    """
    Open een WebSocket-sessie als laadpaal CP-2 met OCPP 1.6.
    Deze fixture wordt hergebruikt in alle tests.
    """
    with client.websocket_connect(
        "/api/ws/ocpp/CP-2",
        subprotocols=["ocpp1.6"]
    ) as websocket:
        yield websocket

def test_boot_notification(ws):
    # BootNotification
    ws.send_json([
        2,               # MessageTypeId = CALL
        "boot-42",       # Unique call ID
        "BootNotification",
        {
            "chargePointVendor": "TestVendor",
            "chargePointModel": "TestModel"
        }
    ])
    resp = ws.receive_json()
    assert isinstance(resp, list)
    assert resp[0] == 3          # MessageTypeId = CALLRESULT
    assert resp[1] == "boot-42"
    assert resp[2]["status"] == "Accepted"
    assert "currentTime" in resp[2]
    assert resp[2]["interval"] == 10

def test_heartbeat(ws):
    # Heartbeat
    ws.send_json([
        2,
        "hb-1",
        "Heartbeat",
        {}
    ])
    resp = ws.receive_json()
    assert resp[0] == 3
    assert resp[1] == "hb-1"
    # Heartbeat geeft currentTime
    assert "currentTime" in resp[2]

def test_authorize(ws):
    # Authorize
    ws.send_json([
        2,
        "auth-1",
        "Authorize",
        {"idTag": "ABC123"}
    ])
    resp = ws.receive_json()
    assert resp[0] == 3
    assert resp[1] == "auth-1"
    assert resp[2]["idTagInfo"]["status"] == "Accepted"

def test_start_and_stop_transaction(ws):
    # StartTransaction
    ws.send_json([
        2,
        "start-1",
        "StartTransaction",
        {
            "connectorId": 1,
            "idTag": "ABC123",
            "meterStart": 100,
            "timestamp": "2025-05-26T12:00:00Z"
        }
    ])
    resp_start = ws.receive_json()
    assert resp_start[0] == 3
    assert resp_start[1] == "start-1"
    assert resp_start[2]["transactionId"] == 1
    assert resp_start[2]["idTagInfo"]["status"] == "Accepted"

    # StopTransaction
    ws.send_json([
        2,
        "stop-1",
        "StopTransaction",
        {
            "transactionId": 1,
            "meterStop": 150,
            "timestamp": "2025-05-26T12:05:00Z"
        }
    ])
    resp_stop = ws.receive_json()
    assert resp_stop[0] == 3
    assert resp_stop[1] == "stop-1"
    assert resp_stop[2]["idTagInfo"]["status"] == "Accepted"

def test_status_notification(ws):
    # StatusNotification
    sample_status = {
        "connectorId": 1,
        "status": "Available",
        "errorCode": "NoError",
        "timestamp": "2025-05-26T12:10:00Z"
    }
    ws.send_json([
        2,
        "status-1",
        "StatusNotification",
        sample_status
    ])
    resp = ws.receive_json()
    assert resp[0] == 3
    assert resp[1] == "status-1"
    # de CALLRESULT heeft geen payload behalve lege {} 
    assert isinstance(resp[2], dict)

def test_meter_values(ws):
    # MeterValues
    sample_meter = {
        "connectorId": 1,
        "meterValue": [
            {
                "timestamp": "2025-05-26T12:15:00Z",
                "sampledValue": [
                    {"value": "10.5", "unit": "kWh"},
                    {"value": "220", "unit": "V"}
                ]
            }
        ]
    }
    ws.send_json([
        2,
        "meter-1",
        "MeterValues",
        sample_meter
    ])
    resp = ws.receive_json()
    assert resp[0] == 3
    assert resp[1] == "meter-1"
    assert isinstance(resp[2], dict)
