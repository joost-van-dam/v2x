from fastapi import WebSocket
from .fastapi_websocket_adapter import FastAPIWebSocketAdapter
from domain.chargepoint_session import WebSocketChannel


class WebSocketGateway:
    """
    ‘Port’ aan de buitenkant: accepteert FastAPI-sockets en levert intern
    een uniforme `WebSocketChannel` op.
    """

    async def accept(self, ws: WebSocket) -> WebSocketChannel:
        """
        Handshake + adapt; het sub-protocol wordt één-op-één doorgegeven
        zodat de laadpaal de juiste OCPP-versie kiest.
        """
        subproto = ws.headers.get("sec-websocket-protocol", "")
        await ws.accept(subprotocol=subproto or None)
        return FastAPIWebSocketAdapter(ws)  # type: ignore[arg-type]

    async def close(self, channel: WebSocketChannel) -> None:
        await channel.close()
