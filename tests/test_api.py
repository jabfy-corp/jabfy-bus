"""Tests CORS de l'API et contrôle d'Origin des WebSockets."""

import unittest

try:
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect
except ImportError:  # pragma: no cover - dépendance optionnelle
    TestClient = None

from jabfy_bus.audit.log import AuditLog
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.message import new_message
from jabfy_bus.core.registry import EntityRegistry
from jabfy_bus.core.types import MessageType, TrustLevel

ALLOWED = "http://localhost:5173"
FOREIGN = "http://evil.example"


@unittest.skipIf(TestClient is None, "FastAPI not installed")
class TestApiCors(unittest.TestCase):
    def setUp(self):
        from jabfy_bus.api.app import create_app
        from jabfy_bus.api.ws import register_ws_routes

        self.bus = UniversalJsonBus()
        registry = EntityRegistry()
        registry.attach(self.bus)
        app = create_app(self.bus, registry, AuditLog(), allowed_origins=[ALLOWED])
        register_ws_routes(app, self.bus, allowed_origins=[ALLOWED])
        self.client = TestClient(app)

    def _preflight(self, origin):
        return self.client.options(
            "/health",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )

    def test_preflight_from_allowed_origin(self):
        response = self._preflight(ALLOWED)
        self.assertEqual(response.headers.get("access-control-allow-origin"), ALLOWED)

    def test_foreign_origin_gets_no_cors_header(self):
        self.assertNotIn("access-control-allow-origin", self._preflight(FOREIGN).headers)
        response = self.client.get("/health", headers={"Origin": FOREIGN})
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_ws_rejects_foreign_origin(self):
        with self.assertRaises(WebSocketDisconnect) as ctx:
            with self.client.websocket_connect("/bus/events", headers={"Origin": FOREIGN}):
                pass
        self.assertEqual(ctx.exception.code, 1008)

    def _assert_receives_event(self, headers):
        with self.client.websocket_connect("/bus/events", headers=headers) as ws:
            message = new_message(
                MessageType.TELEMETRY,
                adapter="test_adapter",
                protocol="internal",
                trust_level=TrustLevel.INTERNAL,
            )
            self.bus.publish(message)
            event = ws.receive_json()
        self.assertEqual(event, message.to_dict())

    def test_ws_accepts_allowed_origin(self):
        self._assert_receives_event({"Origin": ALLOWED})

    def test_ws_accepts_client_without_origin(self):
        self._assert_receives_event({})


if __name__ == "__main__":
    unittest.main()
