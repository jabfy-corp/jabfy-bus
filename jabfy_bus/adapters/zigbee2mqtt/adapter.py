"""Adapter Zigbee2MQTT.

Consomme les messages MQTT publiés par Zigbee2MQTT et produit un
BusMessage par expose (une mesure = un message), en conservant le
payload complet dans `raw`.
"""

from __future__ import annotations

import logging
from typing import Any

from jabfy_bus.adapters.base import BaseAdapter
from jabfy_bus.adapters.mqtt.adapter import parse_payload
from jabfy_bus.adapters.zigbee2mqtt.devices import (
    EXPOSE_MAP,
    IGNORED_KEYS,
    KNOWN_MODELS,
    normalize_expose_value,
)
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.message import Entity, Value, new_message
from jabfy_bus.core.types import AdapterMode, MessageType, TrustLevel

logger = logging.getLogger(__name__)


class Zigbee2MQTTAdapter(BaseAdapter):
    """Traduit les topics `zigbee2mqtt/<friendly_name>` vers le bus."""

    protocol = "zigbee"

    def __init__(
        self,
        bus: UniversalJsonBus,
        base_topic: str = "zigbee2mqtt",
        name: str = "zigbee2mqtt_adapter",
        mode: AdapterMode = AdapterMode.READ_ONLY,
        trust_level: TrustLevel = TrustLevel.LOCAL_GATEWAY,
    ) -> None:
        super().__init__(bus, name=name, mode=mode, trust_level=trust_level)
        self.base_topic = base_topic.rstrip("/")
        # friendly_name -> métadonnées connues (model, ieee_address...)
        self.devices: dict[str, dict[str, Any]] = {}

    def start(self) -> None:
        self._running = True
        self.report_health("started", {"base_topic": self.base_topic})

    # -- inventaire ---------------------------------------------------------

    def register_device(
        self,
        friendly_name: str,
        model: str | None = None,
        ieee_address: str | None = None,
        location: str | None = None,
    ) -> None:
        self.devices[friendly_name] = {
            "model": model,
            "ieee_address": ieee_address,
            "location": location,
        }

    # -- réception MQTT -------------------------------------------------------

    def handle_mqtt(self, topic: str, payload: bytes | str) -> int:
        """Traite un message MQTT Zigbee2MQTT. Retourne le nb de messages émis."""
        if not topic.startswith(self.base_topic + "/"):
            return 0
        suffix = topic[len(self.base_topic) + 1 :]
        if suffix.startswith("bridge/"):
            return self._handle_bridge(suffix, payload)
        # topics de commande écho (`.../set`) et availability
        if suffix.endswith("/set"):
            return 0
        if suffix.endswith("/availability"):
            return self._handle_availability(suffix.rsplit("/", 1)[0], payload)

        friendly_name = suffix
        decoded = parse_payload(payload)
        if not isinstance(decoded, dict):
            logger.debug("non-dict z2m payload on '%s' dropped", topic)
            return 0
        return self._emit_exposes(friendly_name, topic, decoded)

    def _emit_exposes(self, friendly_name: str, topic: str, payload: dict[str, Any]) -> int:
        meta = self.devices.get(friendly_name, {})
        model = meta.get("model")
        device_info = KNOWN_MODELS.get(model) if model else None
        emitted = 0
        for key, raw_value in payload.items():
            if key in IGNORED_KEYS:
                continue
            mapping = EXPOSE_MAP.get(key)
            if mapping is None:
                continue
            normalized = normalize_expose_value(key, raw_value)
            entity_domain = mapping.domain
            msg = new_message(
                MessageType.STATE_CHANGED if key == "state" else MessageType.TELEMETRY,
                adapter=self.name,
                protocol=self.protocol,
                bridge="zigbee2mqtt",
                raw_address=topic,
                device_id=friendly_name,
                ieee_address=meta.get("ieee_address"),
                manufacturer=device_info.manufacturer if device_info else None,
                model=model,
                entity=Entity(
                    id=f"{entity_domain.value}.{friendly_name}_{key}",
                    domain=entity_domain.value,
                    entity_class=mapping.entity_class.value if mapping.entity_class else None,
                    name=friendly_name.replace("_", " ").title(),
                    location=meta.get("location"),
                ),
                value=Value(
                    raw=raw_value,
                    normalized=normalized,
                    unit=mapping.unit,
                    datatype=type(normalized).__name__,
                ),
                capabilities=list(mapping.capabilities),
                trust_level=self.trust_level,
                raw={"topic": topic, "payload": payload},
            )
            self.emit(msg)
            emitted += 1
        return emitted

    def _handle_availability(self, friendly_name: str, payload: bytes | str) -> int:
        decoded = parse_payload(payload)
        state = decoded.get("state") if isinstance(decoded, dict) else decoded
        self.report_health(
            "device_availability", {"device": friendly_name, "state": state}
        )
        return 1

    def _handle_bridge(self, suffix: str, payload: bytes | str) -> int:
        """Topics bridge : on n'exploite que l'inventaire des devices."""
        if suffix != "bridge/devices":
            return 0
        decoded = parse_payload(payload)
        if not isinstance(decoded, list):
            return 0
        for device in decoded:
            if not isinstance(device, dict):
                continue
            fname = device.get("friendly_name")
            if not fname:
                continue
            definition = device.get("definition") or {}
            self.register_device(
                fname,
                model=definition.get("model"),
                ieee_address=device.get("ieee_address"),
            )
        return 0
