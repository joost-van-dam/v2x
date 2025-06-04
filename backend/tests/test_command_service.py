import pytest
import asyncio
import inspect
from fastapi import HTTPException

from application.command_service import CommandService
from domain.chargepoint_session import OCPPVersion

# Mokken van bus.publish
import application.event_bus as event_bus_module


class DummySettings:
    def __init__(self, version, running=True):
        self.ocpp_version = version
        self.enabled = True
        self.alias = None


class FakeSession:
    """
    Simuleert een ChargePointSession:
    - _settings.ocpp_version bepaalt welke OCPP-versie er actief is.
    - _running bepaalt of de sessie 'actief' is.
    - send_call(...) kan een resultaat, een exception of een coroutine-return opleveren.
    """

    def __init__(self, ocpp_version, running=True, send_behavior=None):
        self._settings = DummySettings(ocpp_version)
        self._running = running
        self._send_behavior = send_behavior
        self._sent_call = None

    async def send_call(self, ocpp_call):
        self._sent_call = ocpp_call

        # 1) Als send_behavior een Exception is, gooi rechtstreeks
        if isinstance(self._send_behavior, Exception):
            raise self._send_behavior

        # 2) Als send_behavior een coroutine‐functie is, await die met het call‐object
        if inspect.iscoroutinefunction(self._send_behavior):
            return await self._send_behavior(ocpp_call)

        # 3) Als send_behavior een coroutine‐instance is (bijv. direct een Coroutine object),
        #    await het dan ook:
        if asyncio.iscoroutine(self._send_behavior):
            return await self._send_behavior

        # 4) Als send_behavior een gewone callable is, roep 'm aan en return de waarde
        if callable(self._send_behavior):
            return self._send_behavior(ocpp_call)

        # 5) Anders: return de waarde direct (bijv. een dict)
        return self._send_behavior


class FakeRegistry:
    """
    Simuleert ConnectionRegistryChargePoint:
    - get(cp_id) returns wat we in de constructor opgeven.
    - deregister markeert dat het is aangeroepen.
    """

    def __init__(self, session=None):
        self._session = session
        self.deregister_called = False

    async def get(self, cp_id):
        return self._session

    async def deregister(self, session):
        self.deregister_called = True


@pytest.fixture(autouse=True)
def clear_publish_calls(monkeypatch):
    """
    Mokken van bus.publish: we verzamelen alle calls in 'calls' en geven die terug.
    """
    calls = []

    async def fake_publish(event_name, **kwargs):
        calls.append((event_name, kwargs))

    monkeypatch.setattr(event_bus_module.bus, "publish", fake_publish)
    return calls


@pytest.mark.asyncio
async def test_no_session_raises_404():
    """
    Als registry.get(cp_id) None retourneert, wordt HTTPException(404) gegooid.
    """
    registry = FakeRegistry(session=None)
    service = CommandService(registry)

    with pytest.raises(HTTPException) as exc:
        await service.send("cp1", "AnyAction", {})
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_session_not_running_deregisters_and_raises_404():
    """
    Als er wel een session-object is, maar _running=False,
    dan wordt deregister(...) aangeroepen en volgt HTTPException(404).
    """
    session = FakeSession(ocpp_version=OCPPVersion.V16, running=False)
    registry = FakeRegistry(session=session)
    service = CommandService(registry)

    with pytest.raises(HTTPException) as exc:
        await service.send("cp1", "AnyAction", {})
    assert exc.value.status_code == 404
    assert registry.deregister_called is True


@pytest.mark.asyncio
async def test_send_success_v16_no_publish(clear_publish_calls):
    """
    Succesvolle send_call op OCPP 1.6 (bijv. RemoteStopTransaction).
    Omdat de actie niet in {"ChangeConfiguration","SetVariables"} valt,
    mag er geen event gepubliceerd worden.
    """
    expected_result = {"status": "OK"}
    session = FakeSession(
        ocpp_version=OCPPVersion.V16,
        running=True,
        send_behavior=expected_result,
    )
    registry = FakeRegistry(session=session)
    service = CommandService(registry)

    response = await service.send("cp1", "RemoteStopTransaction", {"transaction_id": 10})
    assert response == {"result": expected_result}

    # Geen ConfigurationChanged‐event
    assert clear_publish_calls == []


@pytest.mark.asyncio
async def test_send_success_v16_with_publish(clear_publish_calls):
    """
    Succesvolle send_call op OCPP 1.6 met actie ChangeConfiguration.
    Verwacht wordt dat bus.publish(...) exact éénmaal wordt aangeroepen.
    """
    expected_result = {"status": "OK"}
    session = FakeSession(
        ocpp_version=OCPPVersion.V16,
        running=True,
        send_behavior=expected_result,
    )
    registry = FakeRegistry(session=session)
    service = CommandService(registry)

    response = await service.send("cp1", "ChangeConfiguration", {"key": "k", "value": "v"})
    assert response == {"result": expected_result}

    # Eén gepubliceerde event
    assert len(clear_publish_calls) == 1
    event_name, kwargs = clear_publish_calls[0]
    assert event_name == "ConfigurationChanged"
    assert kwargs["charge_point_id"] == "cp1"
    assert kwargs["ocpp_action"] == "ChangeConfiguration"
    assert kwargs["parameters"] == {"key": "k", "value": "v"}
    assert "status" in kwargs["result"]


@pytest.mark.asyncio
async def test_send_timeout_error_results_in_504():
    """
    Als send_call een asyncio.TimeoutError gooit, moet HTTPException(504) volgen.
    """
    session = FakeSession(
        ocpp_version=OCPPVersion.V16,
        running=True,
        send_behavior=asyncio.TimeoutError(),
    )
    registry = FakeRegistry(session=session)
    service = CommandService(registry)

    with pytest.raises(HTTPException) as exc:
        await service.send("cp1", "RemoteStopTransaction", {"transaction_id": 5})
    assert exc.value.status_code == 504


@pytest.mark.asyncio
async def test_send_runtime_error_deregisters_and_raises_503():
    """
    Als send_call een RuntimeError (bv. websocket dicht) gooit, dan
    wordt registry.deregister(...) aangeroepen en volgt HTTPException(503).
    """
    session = FakeSession(
        ocpp_version=OCPPVersion.V16,
        running=True,
        send_behavior=RuntimeError("ws closed"),
    )
    registry = FakeRegistry(session=session)
    service = CommandService(registry)

    with pytest.raises(HTTPException) as exc:
        await service.send("cp1", "RemoteStopTransaction", {"transaction_id": 5})
    assert exc.value.status_code == 503
    assert registry.deregister_called is True


@pytest.mark.asyncio
async def test_send_success_v201_and_strategy_used():
    """
    Voor OCPP 2.0.1 (V201) controleren we dat de juiste strategy
    is gebruikt: we verwachten een instance van RequestStartTransaction.
    """

    expected_result = {"status": "OK"}

    async def behavior(call):
        # Controleer dat we een instance van ocpp.v201.call.RequestStartTransaction krijgen
        from ocpp.v201.call import RequestStartTransaction
        assert isinstance(call, RequestStartTransaction)
        return expected_result

    session = FakeSession(
        ocpp_version=OCPPVersion.V201,
        running=True,
        send_behavior=behavior,
    )
    registry = FakeRegistry(session=session)
    service = CommandService(registry)

    response = await service.send(
        "cp1",
        "RequestStartTransaction",
        {"id_tag": "T", "remote_start_id": 99},
    )
    assert response == {"result": expected_result}
