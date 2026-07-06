"""Squelette d'adapter CoAP (P2).

Le transport CoAP (aiocoap) n'est pas encore branché : ce module fixe
le contrat de normalisation pour que le reste du bus n'ait pas à
changer quand le transport arrivera.
"""

from __future__ import annotations

from urllib.parse import urlparse

from jabfy_bus.adapters.base import BaseAdapter
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.errors import AdapterNotReady
from jabfy_bus.core.message import Entity, Value, new_message
from jabfy_bus.core.types import AdapterMode, Domain, MessageType, TrustLevel


def coap_uri_to_entity(uri: str) -> tuple[str, str]:
    """`coap://sensor-01/temp` -> (device_id, resource)."""
    parsed = urlparse(uri)
    if parsed.scheme not in ("coap", "coaps"):
        raise ValueError(f"not a CoAP URI: {uri}")
    resource = parsed.path.strip("/").replace("/", "_") or "root"
    return parsed.hostname or "unknown", resource


class CoAPAdapter(BaseAdapter):
    """Contrat de l'adapter CoAP. Transport non implémenté (P2)."""

    protocol = "coap"

    def __init__(
        self,
        bus: UniversalJsonBus,
        name: str = "coap_adapter",
        trust_level: TrustLevel = TrustLevel.LOCAL_NETWORK,
    ) -> None:
        super().__init__(bus, name=name, mode=AdapterMode.READ_ONLY, trust_level=trust_level)

    def start(self) -> None:
        raise AdapterNotReady(self.name, "CoAP transport not implemented yet (P2)")

    def handle_response(self, uri: str, method: str, payload: object, unit: str | None = None) -> int:
        """Normalise une réponse CoAP déjà décodée (utilisé par les tests/le futur transport)."""
        device_id, resource = coap_uri_to_entity(uri)
        msg = new_message(
            MessageType.TELEMETRY,
            adapter=self.name,
            protocol=self.protocol,
            raw_address=uri,
            device_id=device_id,
            method=method,
            entity=Entity(
                id=f"sensor.{device_id}_{resource}",
                domain=Domain.SENSOR.value,
            ),
            value=Value(raw=payload, normalized=payload, unit=unit, datatype=type(payload).__name__),
            trust_level=self.trust_level,
            raw={"uri": uri, "method": method, "payload": payload},
        )
        return self.emit(msg)
