"""Core du bus : modèle de message, types, bus pub/sub interne."""

from jabfy_bus.core.bus import Subscription, UniversalJsonBus
from jabfy_bus.core.errors import (
    AdapterError,
    BusError,
    InvalidMessage,
    UnknownProtocol,
    WriteNotAllowed,
)
from jabfy_bus.core.message import (
    BusMessage,
    Entity,
    Quality,
    Security,
    Source,
    Value,
    new_message,
)
from jabfy_bus.core.registry import EntityRegistry
from jabfy_bus.core.types import (
    Action,
    AdapterMode,
    Domain,
    EntityClass,
    MessageType,
    RiskLevel,
    TrustLevel,
)

__all__ = [
    "Action",
    "AdapterError",
    "AdapterMode",
    "BusError",
    "BusMessage",
    "Domain",
    "Entity",
    "EntityClass",
    "EntityRegistry",
    "InvalidMessage",
    "MessageType",
    "new_message",
    "Quality",
    "RiskLevel",
    "Security",
    "Source",
    "Subscription",
    "TrustLevel",
    "UniversalJsonBus",
    "UnknownProtocol",
    "Value",
    "WriteNotAllowed",
]
