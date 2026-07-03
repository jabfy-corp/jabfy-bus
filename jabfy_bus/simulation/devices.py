"""Devices simulés pour le Simulation Lab.

Chaque device produit à chaque tick zéro ou plusieurs lectures
(`Reading`), que le lab convertit en BusMessage.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from jabfy_bus.core.types import Domain, EntityClass


@dataclass
class Reading:
    """Une mesure produite par un device simulé."""

    entity_id: str
    domain: Domain
    value: Any
    entity_class: EntityClass | None = None
    unit: str | None = None
    capabilities: tuple[str, ...] = ("read",)
    location: str | None = None


class SimulatedDevice(ABC):
    """Device virtuel piloté par le lab."""

    def __init__(self, device_id: str, location: str | None = None, seed: int | None = None) -> None:
        self.device_id = device_id
        self.location = location
        self.rng = random.Random(seed)

    @abstractmethod
    def tick(self) -> list[Reading]:
        """Avance d'un pas de simulation et retourne les lectures produites."""


class SimulatedTemperatureSensor(SimulatedDevice):
    """Marche aléatoire bornée autour d'une température de consigne."""

    def __init__(
        self,
        device_id: str,
        location: str | None = None,
        base: float = 21.0,
        drift: float = 0.3,
        seed: int | None = None,
    ) -> None:
        super().__init__(device_id, location, seed)
        self.base = base
        self.drift = drift
        self.current = base

    def tick(self) -> list[Reading]:
        self.current += self.rng.uniform(-self.drift, self.drift)
        # rappel vers la consigne pour éviter la dérive infinie
        self.current += (self.base - self.current) * 0.05
        return [
            Reading(
                entity_id=f"sensor.{self.device_id}",
                domain=Domain.SENSOR,
                entity_class=EntityClass.TEMPERATURE,
                value=round(self.current, 1),
                unit="°C",
                location=self.location,
            )
        ]


class SimulatedMotionSensor(SimulatedDevice):
    """Détection de mouvement probabiliste, avec possibilité de forcer."""

    def __init__(
        self,
        device_id: str,
        location: str | None = None,
        probability: float = 0.1,
        seed: int | None = None,
    ) -> None:
        super().__init__(device_id, location, seed)
        self.probability = probability
        self._forced: bool | None = None

    def force(self, detected: bool) -> None:
        """Force la prochaine détection (utile pour les scénarios)."""
        self._forced = detected

    def tick(self) -> list[Reading]:
        if self._forced is not None:
            detected, self._forced = self._forced, None
        else:
            detected = self.rng.random() < self.probability
        return [
            Reading(
                entity_id=f"binary_sensor.{self.device_id}",
                domain=Domain.BINARY_SENSOR,
                entity_class=EntityClass.MOTION,
                value=detected,
                location=self.location,
            )
        ]


class SimulatedSwitch(SimulatedDevice):
    """Actionneur on/off : reçoit des commandes du lab."""

    def __init__(self, device_id: str, location: str | None = None, seed: int | None = None) -> None:
        super().__init__(device_id, location, seed)
        self.state = False
        self.command_count = 0

    def apply_command(self, action: str, params: dict[str, Any] | None = None) -> None:
        self.command_count += 1
        if action == "turn_on":
            self.state = True
        elif action == "turn_off":
            self.state = False
        elif action == "toggle":
            self.state = not self.state

    def tick(self) -> list[Reading]:
        return [
            Reading(
                entity_id=f"switch.{self.device_id}",
                domain=Domain.SWITCH,
                entity_class=EntityClass.SWITCHABLE,
                value=self.state,
                capabilities=("read", "write", "command.turn_on", "command.turn_off"),
                location=self.location,
            )
        ]


class SimulatedPowerMeter(SimulatedDevice):
    """Compteur : puissance instantanée bruitée + énergie cumulée."""

    def __init__(
        self,
        device_id: str,
        location: str | None = None,
        base_power: float = 250.0,
        seed: int | None = None,
    ) -> None:
        super().__init__(device_id, location, seed)
        self.base_power = base_power
        self.energy_kwh = 0.0

    def tick(self) -> list[Reading]:
        power = max(0.0, self.rng.gauss(self.base_power, self.base_power * 0.15))
        # un tick = une minute simulée
        self.energy_kwh += power / 1000.0 / 60.0
        return [
            Reading(
                entity_id=f"sensor.{self.device_id}_power",
                domain=Domain.SENSOR,
                entity_class=EntityClass.POWER,
                value=round(power, 1),
                unit="W",
                location=self.location,
            ),
            Reading(
                entity_id=f"sensor.{self.device_id}_energy",
                domain=Domain.SENSOR,
                entity_class=EntityClass.ENERGY,
                value=round(self.energy_kwh, 4),
                unit="kWh",
                location=self.location,
            ),
        ]
