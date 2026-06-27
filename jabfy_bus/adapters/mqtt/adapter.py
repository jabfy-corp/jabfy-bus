"""Adapter MQTT.

Le client MQTT est injectable : en production on branche paho-mqtt,
en test ou en simulation on injecte un client factice. L'adapter ne
dépend donc d'aucune librairie externe.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from jabfy_bus.adapters.base import BaseAdapter
from jabfy_bus.adapters.mqtt.mapping import TopicMapper, extract_value
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.errors import AdapterNotReady
from jabfy_bus.core.message import Entity, Value, new_message
from jabfy_bus.core.types import AdapterMode, MessageType, TrustLevel

logger = logging.getLogger(__name__)


class MQTTClient(Protocol):
    """Interface minimale attendue d'un client MQTT."""

    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def subscribe(self, topic: str) -> None: ...
    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> None: ...


def parse_payload(raw: bytes | str) -> Any:
    """Décode un payload MQTT : JSON si possible, scalaire sinon."""
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    text = text.strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return text


class MQTTAdapter(BaseAdapter):
    """Traduit les messages MQTT entrants vers le bus JSON."""

    protocol = "mqtt"

    def __init__(
        self,
        bus: UniversalJsonBus,
        mapper: TopicMapper,
        client: MQTTClient | None = None,
        name: str = "mqtt_adapter",
        subscriptions: list[str] | None = None,
        mode: AdapterMode = AdapterMode.READ_ONLY,
        trust_level: TrustLevel = TrustLevel.LOCAL_GATEWAY,
    ) -> None:
        super().__init__(bus, name=name, mode=mode, trust_level=trust_level)
        self.mapper = mapper
        self.client = client
        self.subscriptions = list(subscriptions or ["#"])
        self.dropped = 0

    # -- cycle de vie ----------------------------------------------------

    def start(self) -> None:
        if self.client is None:
            raise AdapterNotReady(self.name, "no MQTT client injected")
        self.client.connect()
        for topic in self.subscriptions:
            self.client.subscribe(topic)
        self._running = True
        self.report_health("started", {"subscriptions": self.subscriptions})

    def stop(self) -> None:
        if self.client is not None:
            self.client.disconnect()
        super().stop()

    # -- réception -------------------------------------------------------

    def handle_message(
        self,
        topic: str,
        payload: bytes | str,
        qos: int = 0,
        retain: bool = False,
    ) -> int:
        """Point d'entrée d'un message MQTT natif. Retourne le nb de handlers notifiés."""
        decoded = parse_payload(payload)
        resolved = self.mapper.resolve(topic)
        if resolved is None:
            self.dropped += 1
            logger.debug("no mapping rule for topic '%s', message dropped", topic)
            return 0

        rule = resolved.rule
        value_raw = extract_value(decoded, rule.value_key)
        msg = new_message(
            MessageType.TELEMETRY,
            adapter=self.name,
            protocol=self.protocol,
            raw_address=topic,
            entity=Entity(
                id=resolved.entity_id,
                domain=rule.domain.value,
                entity_class=rule.entity_class.value if rule.entity_class else None,
            ),
            value=Value(
                raw=value_raw,
                normalized=value_raw,
                unit=rule.unit,
                datatype=type(value_raw).__name__,
            ),
            capabilities=rule.capabilities,
            trust_level=self.trust_level,
            raw={
                "topic": topic,
                "payload": decoded,
                "qos": qos,
                "retain": retain,
            },
        )
        return self.emit(msg)

    # -- écriture ----------------------------------------------------------

    def write(self, target: str, payload: Any) -> None:
        """Publie une commande sur un topic MQTT (adapter read-write uniquement)."""
        self.ensure_writable()
        if self.client is None:
            raise AdapterNotReady(self.name, "no MQTT client injected")
        body = payload if isinstance(payload, str) else json.dumps(payload)
        self.client.publish(target, body, qos=1, retain=False)
