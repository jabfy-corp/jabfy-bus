"""Types et énumérations partagés par tout le bus.

Le principe directeur : aucun protocole externe ne dicte le modèle interne.
Ces énumérations constituent le vocabulaire commun vers lequel chaque
adapter traduit ses données.
"""

from __future__ import annotations

from enum import Enum


class MessageType(str, Enum):
    """Types de messages circulant sur le bus."""

    TELEMETRY = "telemetry"
    STATE_CHANGED = "state.changed"
    EVENT = "event"
    COMMAND_REQUESTED = "command.requested"
    COMMAND_APPROVED = "command.approved"
    COMMAND_REJECTED = "command.rejected"
    COMMAND_EXECUTED = "command.executed"
    CAPABILITY_REPORT = "capability.report"
    HEALTH = "health"
    AUDIT = "audit"
    SIMULATION = "simulation"
    USER_SITUATION = "user_situation"


class Domain(str, Enum):
    """Domaines d'entités normalisés."""

    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    SWITCH = "switch"
    LIGHT = "light"
    COVER = "cover"
    LOCK = "lock"
    CLIMATE = "climate"
    FAN = "fan"
    VALVE = "valve"
    METER = "meter"
    ALARM = "alarm"
    CAMERA = "camera"
    BUTTON = "button"
    SCENE = "scene"
    AUTOMATION = "automation"
    GATEWAY = "gateway"
    CONTROLLER = "controller"
    MACHINE = "machine"
    ACTUATOR = "actuator"


class EntityClass(str, Enum):
    """Classes sémantiques : le sens réel de la donnée."""

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    POWER = "power"
    ENERGY = "energy"
    VOLTAGE = "voltage"
    CURRENT = "current"
    MOTION = "motion"
    PRESENCE = "presence"
    DOOR = "door"
    WINDOW = "window"
    SMOKE = "smoke"
    CO2 = "co2"
    CO = "co"
    WATER_LEAK = "water_leak"
    ILLUMINANCE = "illuminance"
    BATTERY = "battery"
    SIGNAL_STRENGTH = "signal_strength"
    POSITION = "position"
    SPEED = "speed"
    FLOW = "flow"
    LEVEL = "level"
    SETPOINT = "setpoint"
    MODE = "mode"
    FAULT = "fault"
    SWITCHABLE = "switchable"
    SOIL_MOISTURE = "soil_moisture"


class Action(str, Enum):
    """Actions normalisées, indépendantes du protocole cible."""

    TURN_ON = "turn_on"
    TURN_OFF = "turn_off"
    TOGGLE = "toggle"
    SET_VALUE = "set_value"
    SET_BRIGHTNESS = "set_brightness"
    SET_COLOR = "set_color"
    SET_TEMPERATURE = "set_temperature"
    OPEN = "open"
    CLOSE = "close"
    STOP = "stop"
    LOCK = "lock"
    UNLOCK = "unlock"
    ARM = "arm"
    DISARM = "disarm"
    RESET = "reset"
    ACKNOWLEDGE = "acknowledge"
    START = "start"
    STOP_PROCESS = "stop_process"


class TrustLevel(str, Enum):
    """Niveau de confiance de la source d'un message."""

    UNTRUSTED = "untrusted"
    LOCAL_NETWORK = "local_network"
    LOCAL_GATEWAY = "local_gateway"
    VERIFIED_DEVICE = "verified_device"
    INTERNAL = "internal"

    def rank(self) -> int:
        return _TRUST_RANK[self]


_TRUST_RANK = {
    TrustLevel.UNTRUSTED: 0,
    TrustLevel.LOCAL_NETWORK: 1,
    TrustLevel.LOCAL_GATEWAY: 2,
    TrustLevel.VERIFIED_DEVICE: 3,
    TrustLevel.INTERNAL: 4,
}


class RiskLevel(str, Enum):
    """Niveaux de risque d'une commande."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def rank(self) -> int:
        return _RISK_RANK[self]


_RISK_RANK = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


class AdapterMode(str, Enum):
    """Mode d'un adapter. Par défaut : lecture seule."""

    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
