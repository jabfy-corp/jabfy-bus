"""Connaissance des devices Zigbee2MQTT.

EXPOSE_MAP traduit les clés de payload Zigbee2MQTT ("exposes") vers le
vocabulaire normalisé du bus (domaine, classe, unité).
"""

from __future__ import annotations

from dataclasses import dataclass

from jabfy_bus.core.types import Domain, EntityClass


@dataclass(frozen=True)
class ExposeMapping:
    domain: Domain
    entity_class: EntityClass | None = None
    unit: str | None = None
    capabilities: tuple[str, ...] = ("read",)
    # Certains exposes booléens sont inversés : contact=true veut dire "fermé".
    invert: bool = False


# Clés de payload Zigbee2MQTT -> sémantique normalisée.
EXPOSE_MAP: dict[str, ExposeMapping] = {
    "temperature": ExposeMapping(Domain.SENSOR, EntityClass.TEMPERATURE, "°C"),
    "humidity": ExposeMapping(Domain.SENSOR, EntityClass.HUMIDITY, "%"),
    "pressure": ExposeMapping(Domain.SENSOR, EntityClass.PRESSURE, "hPa"),
    "illuminance": ExposeMapping(Domain.SENSOR, EntityClass.ILLUMINANCE, "lx"),
    "illuminance_lux": ExposeMapping(Domain.SENSOR, EntityClass.ILLUMINANCE, "lx"),
    "co2": ExposeMapping(Domain.SENSOR, EntityClass.CO2, "ppm"),
    "battery": ExposeMapping(Domain.SENSOR, EntityClass.BATTERY, "%"),
    "voltage": ExposeMapping(Domain.SENSOR, EntityClass.VOLTAGE, "mV"),
    "power": ExposeMapping(Domain.SENSOR, EntityClass.POWER, "W"),
    "energy": ExposeMapping(Domain.SENSOR, EntityClass.ENERGY, "kWh"),
    "current": ExposeMapping(Domain.SENSOR, EntityClass.CURRENT, "A"),
    "linkquality": ExposeMapping(Domain.SENSOR, EntityClass.SIGNAL_STRENGTH, "lqi"),
    "occupancy": ExposeMapping(Domain.BINARY_SENSOR, EntityClass.MOTION),
    "presence": ExposeMapping(Domain.BINARY_SENSOR, EntityClass.PRESENCE),
    "contact": ExposeMapping(Domain.BINARY_SENSOR, EntityClass.DOOR, invert=True),
    "water_leak": ExposeMapping(Domain.BINARY_SENSOR, EntityClass.WATER_LEAK),
    "smoke": ExposeMapping(Domain.BINARY_SENSOR, EntityClass.SMOKE),
    "state": ExposeMapping(
        Domain.SWITCH, EntityClass.SWITCHABLE, capabilities=("read", "write", "command.turn_on", "command.turn_off")
    ),
    "brightness": ExposeMapping(
        Domain.LIGHT, EntityClass.SWITCHABLE, capabilities=("read", "write", "command.set_brightness")
    ),
    "position": ExposeMapping(
        Domain.COVER, EntityClass.POSITION, "%", capabilities=("read", "write", "command.open", "command.close")
    ),
    "soil_moisture": ExposeMapping(Domain.SENSOR, EntityClass.SOIL_MOISTURE, "%"),
}

# Clés techniques à ignorer (métadonnées Zigbee2MQTT, pas des mesures).
IGNORED_KEYS = frozenset(
    {
        "last_seen",
        "elapsed",
        "update",
        "update_available",
        "device",
        "action_group",
        "power_outage_count",
    }
)


@dataclass(frozen=True)
class DeviceInfo:
    """Fiche minimale d'un modèle connu."""

    manufacturer: str
    model: str
    description: str
    default_domain: Domain


# Quelques modèles répandus, utile pour enrichir l'entité normalisée.
KNOWN_MODELS: dict[str, DeviceInfo] = {
    "RTCGQ11LM": DeviceInfo("Aqara", "RTCGQ11LM", "Motion sensor", Domain.BINARY_SENSOR),
    "WSDCGQ11LM": DeviceInfo("Aqara", "WSDCGQ11LM", "Temperature/humidity sensor", Domain.SENSOR),
    "MCCGQ11LM": DeviceInfo("Aqara", "MCCGQ11LM", "Door/window sensor", Domain.BINARY_SENSOR),
    "SJCGQ11LM": DeviceInfo("Aqara", "SJCGQ11LM", "Water leak sensor", Domain.BINARY_SENSOR),
    "LED1836G9": DeviceInfo("IKEA", "LED1836G9", "TRADFRI bulb E27", Domain.LIGHT),
    "E1743": DeviceInfo("IKEA", "E1743", "TRADFRI on/off switch", Domain.BUTTON),
    "ZNCZ04LM": DeviceInfo("Xiaomi", "ZNCZ04LM", "Smart plug", Domain.SWITCH),
    "SNZB-02": DeviceInfo("SONOFF", "SNZB-02", "Temperature/humidity sensor", Domain.SENSOR),
}


def normalize_expose_value(key: str, value: object) -> object:
    """Normalise la valeur d'un expose (inversion des booléens 'contact')."""
    mapping = EXPOSE_MAP.get(key)
    if mapping is None:
        return value
    if mapping.invert and isinstance(value, bool):
        return not value
    if key == "state" and isinstance(value, str):
        return value.upper() == "ON"
    return value
