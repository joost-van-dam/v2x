import sys
import os

# Voeg de parent-directory (de backend-folder) toe aan sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from typing import Any, Dict, List

from fastapi import HTTPException

# Importeer de strategieklassen vanuit jouw module
from application.ocpp_command_strategy import V16CommandStrategy, V201CommandStrategy

from ocpp.v16.call import (
    RemoteStartTransaction as V16RemoteStart,
    RemoteStopTransaction as V16RemoteStop,
    ChangeConfiguration as V16ChangeConfiguration,
    GetConfiguration as V16GetConfiguration,
    # SecurityBootNotification bestaat in jouw ocpp-versie niet
)
from ocpp.v201.call import (
    RequestStartTransaction as V201RequestStart,
    RequestStopTransaction as V201RequestStop,
    GetBaseReport as V201GetBaseReport,
    GetVariables as V201GetVariables,
    SetVariables as V201SetVariables,
)


# --------------------------- V16 Tests ---------------------------

@pytest.fixture
def v16_strategy():
    return V16CommandStrategy()


def test_v16_remote_start_default(v16_strategy):
    action = "RemoteStartTransaction"
    params: Dict[str, Any] = {}
    result = v16_strategy.build(action, params)

    # Controleer dat het object de juiste klasse heeft
    assert isinstance(result, V16RemoteStart)
    assert result.id_tag == "UNKNOWN"
    # connector_id en charging_profile bestaan, maar zijn None
    assert result.connector_id is None
    assert result.charging_profile is None


def test_v16_remote_start_with_optional_fields(v16_strategy):
    action = "RemoteStartTransaction"
    params = {"id_tag": "TAG123", "connector_id": 5, "charging_profile": {"cp": "data"}}
    result = v16_strategy.build(action, params)

    assert isinstance(result, V16RemoteStart)
    assert result.id_tag == "TAG123"
    assert result.connector_id == 5
    assert result.charging_profile == {"cp": "data"}


def test_v16_remote_stop_success(v16_strategy):
    action = "RemoteStopTransaction"
    params = {"transaction_id": 42}
    result = v16_strategy.build(action, params)

    assert isinstance(result, V16RemoteStop)
    assert result.transaction_id == 42


def test_v16_remote_stop_missing_transaction_id(v16_strategy):
    action = "RemoteStopTransaction"
    with pytest.raises(HTTPException) as exc:
        v16_strategy.build(action, {})
    assert exc.value.status_code == 400
    assert "Missing 'transaction_id'" in exc.value.detail


def test_v16_change_configuration_success(v16_strategy):
    action = "ChangeConfiguration"
    params = {"key": "MaxPower", "value": "32"}
    result = v16_strategy.build(action, params)

    assert isinstance(result, V16ChangeConfiguration)
    assert result.key == "MaxPower"
    assert result.value == "32"


def test_v16_change_configuration_missing_key_or_value(v16_strategy):
    action = "ChangeConfiguration"
    # Ontbreekt 'value'
    params_missing_value = {"key": "MaxPower"}
    with pytest.raises(HTTPException) as exc1:
        v16_strategy.build(action, params_missing_value)
    assert exc1.value.status_code == 400
    assert "Missing 'key' or 'value'" in exc1.value.detail

    # Ontbreekt 'key'
    params_missing_key = {"value": "16"}
    with pytest.raises(HTTPException) as exc2:
        v16_strategy.build(action, params_missing_key)
    assert exc2.value.status_code == 400
    assert "Missing 'key' or 'value'" in exc2.value.detail


def test_v16_get_configuration_default_and_override(v16_strategy):
    action = "GetConfiguration"

    # Standaard: lege key-lijst
    result_default = v16_strategy.build(action, {})
    assert isinstance(result_default, V16GetConfiguration)
    assert result_default.key == []

    # Override met een lijst
    result_override = v16_strategy.build(action, {"key": ["cfg1", "cfg2"]})
    assert isinstance(result_override, V16GetConfiguration)
    assert result_override.key == ["cfg1", "cfg2"]


def test_v16_security_boot_notification_raises_attribute_error(v16_strategy):
    # Omdat SecurityBootNotification niet bestaat in ocpp.v16.call,
    # verwachten we nu een AttributeError wanneer we proberen te bouwen.
    with pytest.raises(AttributeError):
        v16_strategy.build("SecurityBootNotification", {})

    with pytest.raises(AttributeError):
        v16_strategy.build("SecurityBootNotification", {
            "charge_box_serial_number": "SN123",
            "firmware_version": "FW1.0",
            "iccid": "ICCID123",
            "imsi": "IMSI456",
            "meter_type": "TypeX",
            "meter_serial_number": "MSN789",
        })


def test_v16_unknown_action_raises(v16_strategy):
    with pytest.raises(HTTPException) as exc:
        v16_strategy.build("NonExistentAction", {})
    assert exc.value.status_code == 400
    assert "Unknown OCPP 1.6 action" in exc.value.detail


# --------------------------- V201 Tests ---------------------------

@pytest.fixture
def v201_strategy():
    return V201CommandStrategy()


def test_v201_request_start_transaction_default(v201_strategy):
    action = "RequestStartTransaction"
    result = v201_strategy.build(action, {})

    assert isinstance(result, V201RequestStart)
    # Standaard id_token-structuur
    assert result.id_token == {"idToken": "UNKNOWN", "type": "Central"}
    assert result.remote_start_id == 1234


def test_v201_request_start_transaction_override(v201_strategy):
    action = "RequestStartTransaction"
    params = {"id_tag": "USER_TAG", "remote_start_id": 999}
    result = v201_strategy.build(action, params)

    assert isinstance(result, V201RequestStart)
    assert result.id_token == {"idToken": "USER_TAG", "type": "Central"}
    assert result.remote_start_id == 999


def test_v201_request_stop_transaction_success(v201_strategy):
    action = "RequestStopTransaction"
    params = {"transaction_id": 77}
    result = v201_strategy.build(action, params)

    assert isinstance(result, V201RequestStop)
    assert result.transaction_id == 77


def test_v201_request_stop_transaction_missing(v201_strategy):
    action = "RequestStopTransaction"
    with pytest.raises(HTTPException) as exc:
        v201_strategy.build(action, {})
    assert exc.value.status_code == 400
    assert "Missing 'transaction_id'" in exc.value.detail


def test_v201_get_base_report_default_and_override(v201_strategy):
    action = "GetBaseReport"

    result_default = v201_strategy.build(action, {})
    assert isinstance(result_default, V201GetBaseReport)
    assert result_default.request_id == 55
    assert result_default.report_base == "FullInventory"

    params_override = {"requestId": 7, "reportBase": "CustomReport"}
    result_override = v201_strategy.build(action, params_override)
    assert isinstance(result_override, V201GetBaseReport)
    assert result_override.request_id == 7
    assert result_override.report_base == "CustomReport"


def test_v201_get_variables_success(v201_strategy):
    action = "GetVariables"
    keys_payload: List[Dict[str, Any]] = [
        {"component": {"name": "CompA"}, "variable": {"name": "VarA"}},
        {"component": {"name": "CompB"}, "variable": {"name": "VarB"}},
    ]
    params = {"key": keys_payload}
    result = v201_strategy.build(action, params)

    assert isinstance(result, V201GetVariables)
    assert result.get_variable_data == keys_payload


def test_v201_get_variables_missing_key(v201_strategy):
    action = "GetVariables"
    with pytest.raises(HTTPException) as exc:
        v201_strategy.build(action, {})
    assert exc.value.status_code == 400
    assert "'key' list required" in exc.value.detail


def test_v201_set_variables_success(v201_strategy):
    action = "SetVariables"
    key_dict = {"component": {"name": "CompX"}, "variable_name": "VarX"}
    params = {"key": key_dict, "value": "ValueX"}
    result = v201_strategy.build(action, params)

    assert isinstance(result, V201SetVariables)
    # Er wordt één entry in set_variable_data aangemaakt
    assert isinstance(result.set_variable_data, list) and len(result.set_variable_data) == 1
    entry = result.set_variable_data[0]
    assert entry["component"] == {"name": "CompX"}
    assert entry["variable"] == {"name": "VarX"}
    assert entry["attribute_value"] == "ValueX"


def test_v201_set_variables_missing_key_or_value(v201_strategy):
    action = "SetVariables"
    # Ontbreekt 'value'
    params_missing_value = {"key": {"component": {}, "variable_name": "Var"}}
    with pytest.raises(HTTPException) as exc1:
        v201_strategy.build(action, params_missing_value)
    assert exc1.value.status_code == 400
    assert "Missing key/value data" in exc1.value.detail

    # Ontbreekt 'key'
    params_missing_key = {"value": "ValueOnly"}
    with pytest.raises(HTTPException) as exc2:
        v201_strategy.build(action, params_missing_key)
    assert exc2.value.status_code == 400
    assert "Missing key/value data" in exc2.value.detail


def test_v201_unknown_action_raises(v201_strategy):
    with pytest.raises(HTTPException) as exc:
        v201_strategy.build("NonExistentAction", {})
    assert exc.value.status_code == 400
    assert "Unknown OCPP 2.0.1 action" in exc.value.detail
