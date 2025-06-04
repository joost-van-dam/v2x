import sys, os
# Voeg project root toe aan sys.path zodat 'domain' gevonden wordt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import asyncio
import logging
from starlette.websockets import WebSocketDisconnect

from domain.chargepoint_session import (
    ChargePointSession,
    ChargePointSettings,
    OCPPVersion,
    WebSocketChannel,
    IOcppEndpoint,
)

# --------------------- FAKE IMPLEMENTATIONS ---------------------

class FakeChannel(WebSocketChannel):
    def __init__(self, messages):
        self._messages = messages.copy()
        self.closed = False
        self.sent_messages = []

    async def recv(self) -> str:
        if self._messages:
            return self._messages.pop(0)
        raise WebSocketDisconnect()

    async def send(self, message: str) -> None:
        self.sent_messages.append(message)

    async def close(self, code: int | None = None) -> None:
        self.closed = True

class FakeParser(IOcppEndpoint):
    def __init__(self):
        self.routed = []
        self.call_responses = []
        self.id = "fake_parser"

    async def route_message(self, raw: str) -> None:
        self.routed.append(raw)

    async def call(self, message: any) -> any:
        if self.call_responses:
            return self.call_responses.pop(0)
        return f"response to {message}"

# ---------------------- FIXTURES -----------------------------

@pytest.fixture
def settings():
    return ChargePointSettings()

@pytest.fixture
def fake_parser():
    return FakeParser()

@pytest.fixture
def fake_channel():
    return FakeChannel(messages=["hello"])

@pytest.fixture
def session(fake_channel, fake_parser, settings):
    settings.ocpp_version = OCPPVersion.V16
    return ChargePointSession("session1", fake_channel, fake_parser, settings)

# ----------------------- TESTS -------------------------------

@pytest.mark.asyncio
async def test_listen_calls_route_and_disconnect(session, fake_channel, fake_parser):
    task = asyncio.create_task(session.listen())
    await asyncio.sleep(0.1)

    # Parser moet precies één keer worden aangeroepen met "hello"
    assert fake_parser.routed == ["hello"]

    # Na het uitlezen gooit channel.recv() WebSocketDisconnect → channel.closed = True
    await asyncio.sleep(0.1)
    assert fake_channel.closed is True

    # Session mag niet meer als 'running' gemarkeerd staan
    assert session._running is False
    task.cancel()

@pytest.mark.asyncio
async def test_send_call_invokes_parser_and_returns(session, fake_parser):
    fake_parser.call_responses.append("ok_response")
    result = await session.send_call("dummy_message")
    assert result == "ok_response"

@pytest.mark.asyncio
async def test_send_call_logs_and_handles_no_response(session, fake_parser, caplog):
    caplog.set_level(logging.INFO)
    # parser.call is leeg, dus teruggegeven wordt "response to ping"
    result = await session.send_call("ping")
    assert result == "response to ping"

    # Controleer dat er logregels zijn voor zowel request als response
    logs = [
        rec.message
        for rec in caplog.records
        if "→ CP session1" in rec.message or "← CP session1" in rec.message
    ]
    assert any("request" in msg for msg in logs)
    assert any("response" in msg for msg in logs)
