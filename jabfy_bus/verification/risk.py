"""Classification du risque des commandes.

| Niveau   | Exemple                                   |
|----------|-------------------------------------------|
| low      | lire une température                      |
| medium   | allumer une lumière                       |
| high     | ouvrir une porte, désactiver une alarme   |
| critical | action industrielle, coupure énergie      |
"""

from __future__ import annotations

from jabfy_bus.core.message import Entity
from jabfy_bus.core.types import Action, Domain, RiskLevel

# Risque de base par action, indépendamment de la cible.
ACTION_BASE_RISK: dict[Action, RiskLevel] = {
    Action.TURN_ON: RiskLevel.MEDIUM,
    Action.TURN_OFF: RiskLevel.MEDIUM,
    Action.TOGGLE: RiskLevel.MEDIUM,
    Action.SET_VALUE: RiskLevel.MEDIUM,
    Action.SET_BRIGHTNESS: RiskLevel.MEDIUM,
    Action.SET_COLOR: RiskLevel.LOW,
    Action.SET_TEMPERATURE: RiskLevel.HIGH,
    Action.SET_POSITION: RiskLevel.MEDIUM,
    Action.SET_TILT: RiskLevel.MEDIUM,
    Action.SET_MODE: RiskLevel.MEDIUM,
    Action.OPEN: RiskLevel.HIGH,
    Action.CLOSE: RiskLevel.MEDIUM,
    Action.STOP: RiskLevel.MEDIUM,
    Action.LOCK: RiskLevel.MEDIUM,
    Action.UNLOCK: RiskLevel.HIGH,
    Action.ARM: RiskLevel.MEDIUM,
    Action.DISARM: RiskLevel.HIGH,
    Action.RESET: RiskLevel.HIGH,
    Action.ACKNOWLEDGE: RiskLevel.LOW,
    Action.START: RiskLevel.HIGH,
    Action.STOP_PROCESS: RiskLevel.CRITICAL,
}

# Certains domaines aggravent le risque quelle que soit l'action.
DOMAIN_MIN_RISK: dict[Domain, RiskLevel] = {
    Domain.LOCK: RiskLevel.HIGH,
    Domain.ALARM: RiskLevel.HIGH,
    Domain.MACHINE: RiskLevel.CRITICAL,
    Domain.VALVE: RiskLevel.HIGH,
    Domain.CLIMATE: RiskLevel.MEDIUM,
    Domain.COVER: RiskLevel.MEDIUM,
}


def _max_risk(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    return a if a.rank() >= b.rank() else b


def classify_risk(action: Action | str, entity: Entity | None = None) -> RiskLevel:
    """Risque d'une commande = max(risque action, plancher du domaine cible)."""
    try:
        action = Action(action)
    except ValueError:
        # Action inconnue : on refuse de la considérer bénigne.
        return RiskLevel.CRITICAL

    risk = ACTION_BASE_RISK.get(action, RiskLevel.HIGH)
    if entity is not None:
        try:
            domain = Domain(entity.domain)
        except ValueError:
            return RiskLevel.CRITICAL
        floor = DOMAIN_MIN_RISK.get(domain)
        if floor is not None:
            risk = _max_risk(risk, floor)
    return risk
