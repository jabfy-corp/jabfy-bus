"""Flux WebSocket temps réel des événements du bus.

WebSocket = canal de LECTURE du bus interne, jamais un canal de
commande. Endpoints prévus : /bus/events, /verification/decisions,
/audit/live.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from jabfy_bus.core.bus import Subscription, UniversalJsonBus
from jabfy_bus.core.message import BusMessage


class BusEventStream:
    """Pont bus synchrone -> file asyncio consommable par un WebSocket."""

    def __init__(
        self,
        bus: UniversalJsonBus,
        pattern: str = "*",
        max_queue: int = 1000,
    ) -> None:
        self.bus = bus
        self.pattern = pattern
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=max_queue)
        self.dropped = 0
        self._subscription: Subscription | None = None

    def start(self) -> None:
        self._subscription = self.bus.subscribe(self.pattern, self._enqueue, name="ws_stream")

    def stop(self) -> None:
        if self._subscription is not None:
            self.bus.unsubscribe(self._subscription)
            self._subscription = None

    def _enqueue(self, message: BusMessage) -> None:
        try:
            self.queue.put_nowait(message.to_dict())
        except asyncio.QueueFull:
            # anti-spam événementiel : on jette le plus ancien
            self.dropped += 1
            try:
                self.queue.get_nowait()
                self.queue.put_nowait(message.to_dict())
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass

    async def next_event(self) -> dict[str, Any]:
        return await self.queue.get()


def register_ws_routes(app: Any, bus: UniversalJsonBus) -> None:
    """Ajoute les endpoints WebSocket à une app FastAPI existante."""
    from fastapi import WebSocket, WebSocketDisconnect  # noqa: PLC0415 - optionnel

    async def _stream(websocket: WebSocket, pattern: str) -> None:
        await websocket.accept()
        stream = BusEventStream(bus, pattern=pattern)
        stream.start()
        try:
            while True:
                event = await stream.next_event()
                await websocket.send_text(json.dumps(event, ensure_ascii=False))
        except WebSocketDisconnect:
            pass
        finally:
            stream.stop()

    @app.websocket("/bus/events")
    async def bus_events(websocket: WebSocket) -> None:
        await _stream(websocket, "*")

    @app.websocket("/verification/decisions")
    async def verification_decisions(websocket: WebSocket) -> None:
        await _stream(websocket, "command.*")

    @app.websocket("/audit/live")
    async def audit_live(websocket: WebSocket) -> None:
        await _stream(websocket, "audit")
