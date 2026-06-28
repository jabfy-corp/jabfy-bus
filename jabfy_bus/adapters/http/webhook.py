"""Réception de webhooks HTTP entrants.

La logique de normalisation (`handle_payload`) est séparée du serveur
pour rester testable sans socket.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from jabfy_bus.adapters.base import BaseAdapter
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.message import BusMessage
from jabfy_bus.core.types import AdapterMode, TrustLevel

logger = logging.getLogger(__name__)

# Un normaliseur reçoit (path, payload) et retourne un BusMessage ou None.
Normalizer = Callable[[str, dict[str, Any]], BusMessage | None]


@dataclass
class WebhookRoute:
    path_prefix: str
    normalizer: Normalizer


class WebhookReceiver(BaseAdapter):
    """Adapter webhook : chaque route a son normaliseur dédié."""

    protocol = "http"

    def __init__(
        self,
        bus: UniversalJsonBus,
        name: str = "webhook_adapter",
        host: str = "127.0.0.1",
        port: int = 8091,
        trust_level: TrustLevel = TrustLevel.LOCAL_NETWORK,
    ) -> None:
        super().__init__(bus, name=name, mode=AdapterMode.READ_ONLY, trust_level=trust_level)
        self.host = host
        self.port = port
        self.routes: list[WebhookRoute] = []
        self.rejected = 0
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def route(self, path_prefix: str, normalizer: Normalizer) -> "WebhookReceiver":
        self.routes.append(WebhookRoute(path_prefix, normalizer))
        return self

    # -- traitement (testable sans serveur) --------------------------------

    def handle_payload(self, path: str, payload: dict[str, Any]) -> int:
        for r in self.routes:
            if path.startswith(r.path_prefix):
                message = r.normalizer(path, payload)
                if message is None:
                    self.rejected += 1
                    return 0
                return self.emit(message)
        self.rejected += 1
        logger.debug("no webhook route for path '%s'", path)
        return 0

    # -- serveur ------------------------------------------------------------

    def start(self) -> None:
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - API stdlib
                length = int(self.headers.get("Content-Length", 0))
                try:
                    payload = json.loads(self.rfile.read(length) or b"{}")
                except ValueError:
                    self.send_response(400)
                    self.end_headers()
                    return
                handled = receiver.handle_payload(self.path, payload)
                self.send_response(202 if handled else 404)
                self.end_headers()

            def log_message(self, fmt: str, *args: Any) -> None:
                logger.debug("webhook http: " + fmt, *args)

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self._running = True
        self.report_health("started", {"listen": f"{self.host}:{self.port}"})

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server = None
        super().stop()
