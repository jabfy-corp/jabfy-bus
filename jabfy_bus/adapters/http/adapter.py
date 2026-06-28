"""Adapter HTTP en mode polling.

Beaucoup d'appareils exposent une API locale (Shelly, Tasmota...).
Le fetcher est injectable pour rester testable sans réseau.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

from jabfy_bus.adapters.base import BaseAdapter
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.message import Entity, Value, new_message
from jabfy_bus.core.types import AdapterMode, Domain, EntityClass, MessageType, TrustLevel

logger = logging.getLogger(__name__)

Fetcher = Callable[[str, str], Any]


def default_fetcher(url: str, method: str = "GET") -> Any:
    """Fetcher stdlib minimal (usage local uniquement)."""
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310 - API locales
        return json.loads(resp.read().decode("utf-8"))


@dataclass
class Endpoint:
    """Un endpoint HTTP à interroger périodiquement."""

    url: str
    entity_id: str
    domain: Domain
    entity_class: EntityClass | None = None
    unit: str | None = None
    method: str = "GET"
    value_path: str | None = None  # chemin pointé "relay.power"
    capabilities: list[str] = field(default_factory=lambda: ["read"])


def dig(payload: Any, path: str | None) -> Any:
    """Extrait `payload["a"]["b"]` depuis un chemin "a.b"."""
    if path is None:
        return payload
    current = payload
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return None
    return current


class HTTPPollingAdapter(BaseAdapter):
    """Interroge des endpoints HTTP locaux et normalise les réponses."""

    protocol = "http"

    def __init__(
        self,
        bus: UniversalJsonBus,
        endpoints: list[Endpoint],
        fetcher: Fetcher | None = None,
        name: str = "http_adapter",
        mode: AdapterMode = AdapterMode.READ_ONLY,
        trust_level: TrustLevel = TrustLevel.LOCAL_NETWORK,
    ) -> None:
        super().__init__(bus, name=name, mode=mode, trust_level=trust_level)
        self.endpoints = list(endpoints)
        self.fetcher: Fetcher = fetcher or default_fetcher
        self.errors = 0

    def start(self) -> None:
        self._running = True
        self.report_health("started", {"endpoints": len(self.endpoints)})

    def poll_once(self) -> int:
        """Interroge tous les endpoints une fois. Retourne le nb de messages émis."""
        emitted = 0
        for endpoint in self.endpoints:
            try:
                payload = self.fetcher(endpoint.url, endpoint.method)
            except Exception as exc:  # noqa: BLE001 - un endpoint HS ne bloque pas les autres
                self.errors += 1
                logger.warning("endpoint %s failed: %s", endpoint.url, exc)
                self.report_health("endpoint_error", {"url": endpoint.url, "error": str(exc)})
                continue
            value_raw = dig(payload, endpoint.value_path)
            msg = new_message(
                MessageType.TELEMETRY,
                adapter=self.name,
                protocol=self.protocol,
                raw_address=endpoint.url,
                entity=Entity(
                    id=endpoint.entity_id,
                    domain=endpoint.domain.value,
                    entity_class=endpoint.entity_class.value if endpoint.entity_class else None,
                ),
                value=Value(
                    raw=value_raw,
                    normalized=value_raw,
                    unit=endpoint.unit,
                    datatype=type(value_raw).__name__,
                ),
                capabilities=endpoint.capabilities,
                trust_level=self.trust_level,
                raw={"url": endpoint.url, "method": endpoint.method, "payload": payload},
            )
            self.emit(msg)
            emitted += 1
        return emitted
