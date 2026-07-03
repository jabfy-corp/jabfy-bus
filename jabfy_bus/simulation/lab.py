"""Simulation Lab.

Fait tourner des devices simulés, publie leurs lectures sur le bus
via un adapter dédié (protocol "simulation") et sert de transport
d'exécution pour actionner les devices simulés.
"""

from __future__ import annotations

import logging
from typing import Any

from jabfy_bus.adapters.base import BaseAdapter
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.message import Entity, Value, new_message
from jabfy_bus.core.types import AdapterMode, MessageType, TrustLevel
from jabfy_bus.simulation.devices import Reading, SimulatedDevice, SimulatedSwitch

logger = logging.getLogger(__name__)


class SimulationAdapter(BaseAdapter):
    """Adapter du lab : publie les lectures simulées sur le bus."""

    protocol = "simulation"

    def __init__(self, bus: UniversalJsonBus, name: str = "simulation_adapter") -> None:
        super().__init__(
            bus,
            name=name,
            mode=AdapterMode.READ_WRITE,
            trust_level=TrustLevel.LOCAL_GATEWAY,
        )

    def start(self) -> None:
        self._running = True
        self.report_health("started")

    def emit_reading(self, device_id: str, reading: Reading) -> None:
        msg = new_message(
            MessageType.SIMULATION,
            adapter=self.name,
            protocol=self.protocol,
            device_id=device_id,
            raw_address=f"sim://{device_id}",
            entity=Entity(
                id=reading.entity_id,
                domain=reading.domain.value,
                entity_class=reading.entity_class.value if reading.entity_class else None,
                location=reading.location,
            ),
            value=Value(
                raw=reading.value,
                normalized=reading.value,
                unit=reading.unit,
                datatype=type(reading.value).__name__,
            ),
            capabilities=list(reading.capabilities),
            trust_level=self.trust_level,
            raw={"device_id": device_id, "simulated": True},
        )
        self.emit(msg)


class SimulationLab:
    """Orchestre les devices simulés et le temps discret du lab."""

    def __init__(self, bus: UniversalJsonBus) -> None:
        self.bus = bus
        self.adapter = SimulationAdapter(bus)
        self.adapter.start()
        self.devices: dict[str, SimulatedDevice] = {}
        self.ticks = 0

    def add_device(self, device: SimulatedDevice) -> SimulatedDevice:
        self.devices[device.device_id] = device
        return device

    def get(self, device_id: str) -> SimulatedDevice | None:
        return self.devices.get(device_id)

    # -- temps discret -------------------------------------------------------

    def tick(self) -> int:
        """Un pas de simulation : chaque device publie ses lectures."""
        emitted = 0
        for device in self.devices.values():
            for reading in device.tick():
                self.adapter.emit_reading(device.device_id, reading)
                emitted += 1
        self.ticks += 1
        return emitted

    def run(self, steps: int) -> int:
        emitted = 0
        for _ in range(steps):
            emitted += self.tick()
        return emitted

    # -- transport d'exécution --------------------------------------------------

    def transport(self, target: str, payload: Any) -> None:
        """Transport 'simulation' pour l'Execution Layer.

        `target` = device_id simulé, `payload` = commande normalisée.
        """
        device = self.devices.get(target)
        if device is None:
            raise LookupError(f"no simulated device '{target}'")
        if not isinstance(device, SimulatedSwitch):
            raise TypeError(f"device '{target}' does not accept commands")
        action = payload.get("action") if isinstance(payload, dict) else str(payload)
        params = payload.get("params", {}) if isinstance(payload, dict) else {}
        device.apply_command(action, params)
        logger.info("simulated device '%s' applied %s", target, action)
