"""Modèle de message normalisé du bus JABFY (schéma v1.0).

Règle d'or : la normalisation ne supprime jamais l'information brute.
Chaque message conserve le protocole source, l'adresse brute et le
payload original dans les champs `source` et `raw`.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from jabfy_bus import BUS_VERSION
from jabfy_bus.core.errors import InvalidMessage
from jabfy_bus.core.types import MessageType, TrustLevel


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Source:
    """Provenance du message. `raw_address` garde l'adresse native
    (topic MQTT, registre Modbus, node OPC UA...)."""

    adapter: str
    protocol: str
    device_id: str | None = None
    bridge: str | None = None
    raw_address: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Entity:
    """Identité logique normalisée de l'entité concernée."""

    id: str
    domain: str
    entity_class: str | None = None
    name: str | None = None
    location: str | None = None
    asset: str | None = None


@dataclass
class Value:
    """Valeur mesurée : brute et normalisée, jamais l'une sans l'autre."""

    raw: Any = None
    normalized: Any = None
    unit: str | None = None
    datatype: str | None = None
    scale: float | None = None


@dataclass
class Quality:
    confidence: float = 1.0
    source_quality: str = "good"
    stale: bool = False


@dataclass
class Security:
    trust_level: str = TrustLevel.UNTRUSTED.value
    auth_context: str | None = None
    verified: bool = False
    write_allowed: bool = False


@dataclass
class BusMessage:
    """Message universel du bus, schéma v1.0."""

    message_type: str
    source: Source
    entity: Entity | None = None
    value: Value | None = None
    command: dict[str, Any] | None = None
    capabilities: list[str] = field(default_factory=list)
    quality: Quality = field(default_factory=Quality)
    security: Security = field(default_factory=Security)
    raw: dict[str, Any] = field(default_factory=dict)
    bus_version: str = BUS_VERSION
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str | None = None
    timestamp: str = field(default_factory=_utcnow)

    def validate(self) -> None:
        """Valide le message contre le schéma. Lève InvalidMessage sinon."""
        if self.bus_version != BUS_VERSION:
            raise InvalidMessage(
                f"unsupported bus_version '{self.bus_version}'", "bus_version"
            )
        if not self.message_id:
            raise InvalidMessage("missing message_id", "message_id")
        try:
            MessageType(self.message_type)
        except ValueError:
            raise InvalidMessage(
                f"unknown message_type '{self.message_type}'", "message_type"
            ) from None
        if not self.source.adapter:
            raise InvalidMessage("source.adapter is required", "source.adapter")
        if not self.source.protocol:
            raise InvalidMessage("source.protocol is required", "source.protocol")
        if self.entity is not None:
            if not self.entity.id:
                raise InvalidMessage("entity.id is required", "entity.id")
            if not self.entity.domain:
                raise InvalidMessage("entity.domain is required", "entity.domain")
        if self.message_type.startswith("command."):
            if self.command is None:
                raise InvalidMessage(
                    "command messages must carry a command payload", "command"
                )
            if "action" not in self.command:
                raise InvalidMessage("command.action is required", "command.action")
        if not (0.0 <= self.quality.confidence <= 1.0):
            raise InvalidMessage(
                "quality.confidence must be within [0, 1]", "quality.confidence"
            )
        try:
            TrustLevel(self.security.trust_level)
        except ValueError:
            raise InvalidMessage(
                f"unknown trust_level '{self.security.trust_level}'",
                "security.trust_level",
            ) from None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # `entity_class` est sérialisé sous la clé publique `class`.
        if data.get("entity") is not None:
            data["entity"]["class"] = data["entity"].pop("entity_class")
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BusMessage":
        payload = dict(data)
        source = Source(**payload.pop("source"))
        entity_data = payload.pop("entity", None)
        entity = None
        if entity_data is not None:
            entity_data = dict(entity_data)
            if "class" in entity_data:
                entity_data["entity_class"] = entity_data.pop("class")
            entity = Entity(**entity_data)
        value_data = payload.pop("value", None)
        value = Value(**value_data) if value_data is not None else None
        quality = Quality(**payload.pop("quality", {}))
        security = Security(**payload.pop("security", {}))
        msg = cls(
            source=source,
            entity=entity,
            value=value,
            quality=quality,
            security=security,
            **payload,
        )
        msg.validate()
        return msg


def new_message(
    message_type: MessageType | str,
    *,
    adapter: str,
    protocol: str,
    entity: Entity | None = None,
    value: Value | None = None,
    command: dict[str, Any] | None = None,
    capabilities: list[str] | None = None,
    trust_level: TrustLevel | str = TrustLevel.UNTRUSTED,
    raw: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    **source_extra: Any,
) -> BusMessage:
    """Fabrique un message validé prêt à publier sur le bus."""
    known = {"device_id", "bridge", "raw_address"}
    src_kwargs = {k: v for k, v in source_extra.items() if k in known}
    extra = {k: v for k, v in source_extra.items() if k not in known}
    msg = BusMessage(
        message_type=MessageType(message_type).value,
        source=Source(adapter=adapter, protocol=protocol, extra=extra, **src_kwargs),
        entity=entity,
        value=value,
        command=command,
        capabilities=list(capabilities or []),
        security=Security(trust_level=TrustLevel(trust_level).value),
        raw=dict(raw or {}),
        correlation_id=correlation_id,
    )
    msg.validate()
    return msg
