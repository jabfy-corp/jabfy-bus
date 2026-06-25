"""Registre d'entités : dernier état connu de chaque entité du bus."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.message import BusMessage


@dataclass
class EntityRecord:
    entity_id: str
    domain: str
    entity_class: str | None = None
    name: str | None = None
    location: str | None = None
    last_message: BusMessage | None = field(default=None, repr=False)
    capabilities: set[str] = field(default_factory=set)
    seen_count: int = 0

    @property
    def last_value(self) -> Any:
        if self.last_message and self.last_message.value:
            return self.last_message.value.normalized
        return None

    @property
    def last_seen(self) -> str | None:
        return self.last_message.timestamp if self.last_message else None


class EntityRegistry:
    """Suit les entités observées via telemetry / state / capability."""

    TRACKED = ("telemetry", "state.*", "event", "capability.report", "simulation")

    def __init__(self) -> None:
        self._entities: dict[str, EntityRecord] = {}

    def attach(self, bus: UniversalJsonBus) -> None:
        for pattern in self.TRACKED:
            bus.subscribe(pattern, self.observe, name="entity_registry")

    def observe(self, message: BusMessage) -> None:
        if message.entity is None:
            return
        record = self._entities.get(message.entity.id)
        if record is None:
            record = EntityRecord(
                entity_id=message.entity.id,
                domain=message.entity.domain,
                entity_class=message.entity.entity_class,
                name=message.entity.name,
                location=message.entity.location,
            )
            self._entities[message.entity.id] = record
        record.last_message = message
        record.seen_count += 1
        record.capabilities.update(message.capabilities)

    def get(self, entity_id: str) -> EntityRecord | None:
        return self._entities.get(entity_id)

    def list(self, domain: str | None = None) -> list[EntityRecord]:
        records = list(self._entities.values())
        if domain is not None:
            records = [r for r in records if r.domain == domain]
        return sorted(records, key=lambda r: r.entity_id)

    def __len__(self) -> int:
        return len(self._entities)
