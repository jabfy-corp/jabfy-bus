"""Policies du Verification Engine.

Une policy est une règle déclarative : si elle matche la commande,
elle décide (allow/deny). Les policies sont évaluées dans l'ordre,
la première qui matche gagne. Sans match : default deny au-delà du
risque faible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from typing import Any

from jabfy_bus.core.message import BusMessage
from jabfy_bus.core.types import RiskLevel, TrustLevel


@dataclass(frozen=True)
class TimeWindow:
    """Fenêtre horaire locale, gère les fenêtres passant minuit (22h -> 6h)."""

    start: time
    end: time

    def contains(self, t: time) -> bool:
        if self.start <= self.end:
            return self.start <= t <= self.end
        return t >= self.start or t <= self.end


@dataclass
class PolicyDecision:
    status: str  # "approved" | "rejected"
    policy: str
    reason: str
    risk: RiskLevel

    @property
    def approved(self) -> bool:
        return self.status == "approved"


@dataclass
class Policy:
    """Règle déclarative de validation de commande."""

    name: str
    effect: str = "allow"  # "allow" | "deny"
    max_risk: RiskLevel = RiskLevel.MEDIUM
    domains: set[str] | None = None
    actions: set[str] | None = None
    entities: set[str] | None = None
    locations: set[str] | None = None
    min_trust: TrustLevel = TrustLevel.LOCAL_NETWORK
    time_window: TimeWindow | None = None

    def matches(self, message: BusMessage, risk: RiskLevel, now: time) -> bool:
        if risk.rank() > self.max_risk.rank():
            return False
        entity = message.entity
        if self.domains is not None and (entity is None or entity.domain not in self.domains):
            return False
        if self.entities is not None and (entity is None or entity.id not in self.entities):
            return False
        if self.locations is not None and (
            entity is None or entity.location not in self.locations
        ):
            return False
        if self.actions is not None:
            action = (message.command or {}).get("action")
            if action not in self.actions:
                return False
        trust = TrustLevel(message.security.trust_level)
        if trust.rank() < self.min_trust.rank():
            return False
        if self.time_window is not None and not self.time_window.contains(now):
            return False
        return True


def policy_from_dict(data: dict[str, Any]) -> Policy:
    """Construit une policy depuis une config JSON/YAML."""
    window = None
    if "time_window" in data:
        tw = data["time_window"]
        window = TimeWindow(time.fromisoformat(tw["start"]), time.fromisoformat(tw["end"]))
    return Policy(
        name=data["name"],
        effect=data.get("effect", "allow"),
        max_risk=RiskLevel(data.get("max_risk", "medium")),
        domains=set(data["domains"]) if "domains" in data else None,
        actions=set(data["actions"]) if "actions" in data else None,
        entities=set(data["entities"]) if "entities" in data else None,
        locations=set(data["locations"]) if "locations" in data else None,
        min_trust=TrustLevel(data.get("min_trust", "local_network")),
        time_window=window,
    )
