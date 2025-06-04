import pytest
import asyncio
from starlette.websockets import WebSocketState
from infrastructure.fastapi_websocket_adapter import FastAPIWebSocketAdapter

# --------------------- FAKE WEBSOCKET IMPLEMENTATION ---------------------

class FakeWebSocket:
    def __init__(self):
        # Buffer for messages to return on receive_text()
        self._recv_buffer = []
        # Captured messages from send_text()
        self.sent_messages = []
        # Simulate application_state: can be WebSocketState.CONNECTED or DISCONNECTED
        self.application_state = WebSocketState.CONNECTED
        # Simulated client tuple
        self.client = ("127.0.0.1", 12345)
        # Flag to record if close() was called
        self.closed_with_code = None

    async def receive_text(self):
        """Return next queued text or block if none."""
        if self._recv_buffer:
            return self._recv_buffer.pop(0)
        # Simulate waiting for a message: but to test, we can raise after a short sleep
        await asyncio.sleep(0.01)
        raise RuntimeError("No message to receive")

    async def send_text(self, message: str):
        self.sent_messages.append(message)

    async def close(self, code: int = None):
        # Set application_state to DISCONNECTED instead of CLOSED
        self.application_state = WebSocketState.DISCONNECTED
        self.closed_with_code = code

# ---------------------------- TESTS ----------------------------

@pytest.mark.asyncio
async def test_recv_delegates_to_receive_text():
    fake_ws = FakeWebSocket()
    # Queue up messages
    fake_ws._recv_buffer.append("hello")
    adapter = FastAPIWebSocketAdapter(fake_ws)

    result = await adapter.recv()
    assert result == "hello"

@pytest.mark.asyncio
async def test_send_delegates_to_send_text():
    fake_ws = FakeWebSocket()
    adapter = FastAPIWebSocketAdapter(fake_ws)

    await adapter.send("test-message")
    assert fake_ws.sent_messages == ["test-message"]

@pytest.mark.asyncio
async def test_close_only_if_not_already_disconnected():
    fake_ws = FakeWebSocket()
    adapter = FastAPIWebSocketAdapter(fake_ws)

    # Case 1: application_state is CONNECTED → close should be called
    fake_ws.application_state = WebSocketState.CONNECTED
    await adapter.close(1001)
    assert fake_ws.application_state == WebSocketState.DISCONNECTED
    assert fake_ws.closed_with_code == 1001

    # Reset for next case
    fake_ws = FakeWebSocket()
    adapter = FastAPIWebSocketAdapter(fake_ws)

    # Case 2: application_state is already DISCONNECTED → close() should not be called again
    fake_ws.application_state = WebSocketState.DISCONNECTED
    await adapter.close(1002)
    # closed_with_code remains None because .close wasn't invoked
    assert fake_ws.closed_with_code is None

def test_client_property_exposes_underlying_ws_client():
    fake_ws = FakeWebSocket()
    adapter = FastAPIWebSocketAdapter(fake_ws)
    assert adapter.client == ("127.0.0.1", 12345)
