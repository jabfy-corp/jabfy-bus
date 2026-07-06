"""Découverte de capacités (WIP — Phase 2).

Agrège ce que chaque entité sait faire à partir des messages
`capability.report` et des `capabilities` portées par la télémétrie,
puis publie un instantané consolidé. Objectif : que le Reasoning
sache quelles actions sont proposables sans connaître les protocoles.

TODO:
- interroger activement les adapters (scan initial)
- expirer les capacités des entités disparues
- exposer /capabilities dans l'API
"""

from __future__ import annotations

from collections import defaultdict

from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.message import BusMessage, new_message
from jabfy_bus.core.types import MessageType, TrustLevel


class CapabilityIndex:
    """Index entité -> capacités consolidées."""

    WATCHED = ("capability.report", "telemetry", "state.*", "simulation")

    def __init__(self, bus: UniversalJsonBus) -> None:
        self.bus = bus
        self._capabilities: dict[str, set[str]] = defaultdict(set)
        self._dirty: set[str] = set()

    def attach(self) -> None:
        for pattern in self.WATCHED:
            self.bus.subscribe(pattern, self.observe, name="capability_index")

    def observe(self, message: BusMessage) -> None:
        if message.entity is None or not message.capabilities:
            return
        known = self._capabilities[message.entity.id]
        new = set(message.capabilities) - known
        if new:
            known.update(new)
            self._dirty.add(message.entity.id)

    def get(self, entity_id: str) -> set[str]:
        return set(self._capabilities.get(entity_id, set()))

    def can(self, entity_id: str, capability: str) -> bool:
        return capability in self._capabilities.get(entity_id, set())

    def commandable(self) -> dict[str, list[str]]:
        """Entités acceptant au moins une commande."""
        return {
            entity_id: sorted(c for c in caps if c.startswith("command."))
            for entity_id, caps in self._capabilities.items()
            if any(c.startswith("command.") for c in caps)
        }

    def publish_snapshot(self) -> int:
        """Publie un capability.report consolidé pour les entités modifiées."""
        published = 0
        for entity_id in sorted(self._dirty):
            self.bus.publish(
                new_message(
                    MessageType.CAPABILITY_REPORT,
                    adapter="capability_index",
                    protocol="internal",
                    trust_level=TrustLevel.INTERNAL,
                    raw={
                        "entity_id": entity_id,
                        "capabilities": sorted(self._capabilities[entity_id]),
                    },
                )
            )
            published += 1
        self._dirty.clear()
        return published
