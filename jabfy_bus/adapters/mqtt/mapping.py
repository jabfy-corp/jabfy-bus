"""Mapping des topics MQTT vers des entités normalisées.

Les topics MQTT ne sont pas standardisés : chaque intégration invente
son format. Le TopicMapper permet de déclarer des règles explicites
(`zigbee2mqtt/+/temperature` -> sensor/temperature) plutôt que de
deviner en aveugle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from jabfy_bus.core.types import Domain, EntityClass


def topic_matches(pattern: str, topic: str) -> dict[str, str] | None:
    """Match MQTT-like : `+` capture un segment, `#` capture la fin.

    Retourne les segments capturés ({"wild_0": "salon"}) ou None.
    """
    p_parts = pattern.split("/")
    t_parts = topic.split("/")
    captures: dict[str, str] = {}
    idx = 0
    for i, part in enumerate(p_parts):
        if part == "#":
            captures[f"wild_{idx}"] = "/".join(t_parts[i:])
            return captures
        if i >= len(t_parts):
            return None
        if part == "+":
            captures[f"wild_{idx}"] = t_parts[i]
            idx += 1
        elif part != t_parts[i]:
            return None
    if len(t_parts) != len(p_parts):
        return None
    return captures


@dataclass
class TopicRule:
    """Règle de résolution d'un topic vers une entité."""

    pattern: str
    domain: Domain
    entity_class: EntityClass | None = None
    unit: str | None = None
    value_key: str | None = None  # clé du payload JSON portant la valeur
    entity_id: Callable[[dict[str, str]], str] | str | None = None
    capabilities: list[str] = field(default_factory=lambda: ["read"])

    def resolve_entity_id(self, topic: str, captures: dict[str, str]) -> str:
        if callable(self.entity_id):
            return self.entity_id(captures)
        if isinstance(self.entity_id, str):
            return self.entity_id.format(**captures)
        slug = topic.replace("/", "_")
        return f"{self.domain.value}.{slug}"


@dataclass
class ResolvedTopic:
    rule: TopicRule
    entity_id: str
    captures: dict[str, str]


class TopicMapper:
    """Résout un topic vers la première règle qui matche."""

    def __init__(self, rules: list[TopicRule] | None = None) -> None:
        self.rules: list[TopicRule] = list(rules or [])

    def add(self, rule: TopicRule) -> "TopicMapper":
        self.rules.append(rule)
        return self

    def resolve(self, topic: str) -> ResolvedTopic | None:
        for rule in self.rules:
            captures = topic_matches(rule.pattern, topic)
            if captures is not None:
                return ResolvedTopic(
                    rule=rule,
                    entity_id=rule.resolve_entity_id(topic, captures),
                    captures=captures,
                )
        return None


def extract_value(payload: Any, value_key: str | None) -> Any:
    """Extrait la valeur utile du payload sans jeter le reste."""
    if value_key is None:
        return payload
    if isinstance(payload, dict):
        return payload.get(value_key)
    return payload
