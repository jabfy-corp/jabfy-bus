"""Mapping des clusters/attributs Matter vers le vocabulaire du bus.

Matter est proche de ce que fait JABFY, au niveau smart home
standardisé : nodes, endpoints, clusters, attributes, commands.
JABFY se place au-dessus : le cluster est une entrée, jamais le
modèle interne.
"""

from __future__ import annotations

from dataclasses import dataclass

from jabfy_bus.core.types import Domain, EntityClass


@dataclass(frozen=True)
class ClusterMapping:
    domain: Domain
    entity_class: EntityClass | None = None
    unit: str | None = None
    scale: float = 1.0
    capabilities: tuple[str, ...] = ("read", "subscribe")


# (cluster, attribute) -> sémantique bus.
# Identifiants humains pour l'instant ; les ids numériques Matter
# (0x0006/0x0000...) seront ajoutés avec le transport réel.
CLUSTER_MAP: dict[tuple[str, str], ClusterMapping] = {
    ("OnOff", "OnOff"): ClusterMapping(
        Domain.LIGHT,
        EntityClass.SWITCHABLE,
        capabilities=("read", "subscribe", "write", "command.turn_on", "command.turn_off"),
    ),
    ("LevelControl", "CurrentLevel"): ClusterMapping(
        Domain.LIGHT,
        EntityClass.SWITCHABLE,
        capabilities=("read", "subscribe", "write", "command.set_brightness"),
    ),
    # TemperatureMeasurement : centièmes de degré -> °C
    ("TemperatureMeasurement", "MeasuredValue"): ClusterMapping(
        Domain.SENSOR, EntityClass.TEMPERATURE, "°C", scale=0.01
    ),
    ("RelativeHumidityMeasurement", "MeasuredValue"): ClusterMapping(
        Domain.SENSOR, EntityClass.HUMIDITY, "%", scale=0.01
    ),
    ("IlluminanceMeasurement", "MeasuredValue"): ClusterMapping(
        Domain.SENSOR, EntityClass.ILLUMINANCE, "lx"
    ),
    ("OccupancySensing", "Occupancy"): ClusterMapping(
        Domain.BINARY_SENSOR, EntityClass.MOTION
    ),
    ("DoorLock", "LockState"): ClusterMapping(
        Domain.LOCK,
        EntityClass.DOOR,
        capabilities=("read", "subscribe", "command.lock", "command.unlock"),
    ),
}
