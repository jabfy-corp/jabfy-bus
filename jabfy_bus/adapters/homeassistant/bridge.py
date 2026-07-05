"""Bridge Home Assistant (WIP).

Home Assistant n'est pas un protocole mais un excellent agrégateur
initial : son WebSocket API pousse des événements `state_changed`
déjà riches (entity_id, domaine, attributs, unité).

État : la normalisation des événements est en place et testable ;
le client WebSocket (auth par token, reconnexion) reste à brancher.
"""

from __future__ import annotations

import logging
from typing import Any

from jabfy_bus.adapters.base import BaseAdapter
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.errors import AdapterNotReady
from jabfy_bus.core.message import Entity, Value, new_message
from jabfy_bus.core.types import AdapterMode, MessageType, TrustLevel

logger = logging.getLogger(__name__)

# domaine HA -> domaine bus (identiques pour la plupart)
DOMAIN_ALIASES = {
    "input_boolean": "switch",
    "media_player": "controller",
}

# device_class HA notables -> classe sémantique bus
DEVICE_CLASS_ALIASES = {
    "garage_door": "door",
    "opening": "window",
    "moisture": "water_leak",
}


class HomeAssistantBridge(BaseAdapter):
    """Consomme les événements state_changed de Home Assistant."""

    protocol = "homeassistant"

    def __init__(
        self,
        bus: UniversalJsonBus,
        base_url: str = "http://homeassistant.local:8123",
        name: str = "homeassistant_bridge",
        trust_level: TrustLevel = TrustLevel.LOCAL_GATEWAY,
    ) -> None:
        super().__init__(bus, name=name, mode=AdapterMode.READ_ONLY, trust_level=trust_level)
        self.base_url = base_url.rstrip("/")

    def start(self) -> None:
        # TODO: client WebSocket HA (auth token, subscribe_events, reconnexion)
        raise AdapterNotReady(self.name, "HA websocket client not wired yet (WIP)")

    # -- normalisation (testable sans HA) -----------------------------------

    def handle_state_changed(self, event: dict[str, Any]) -> int:
        """Normalise un événement HA `state_changed` vers le bus."""
        data = event.get("data", {})
        entity_id = data.get("entity_id", "")
        new_state = data.get("new_state") or {}
        if not entity_id or not new_state:
            return 0

        ha_domain = entity_id.split(".", 1)[0]
        domain = DOMAIN_ALIASES.get(ha_domain, ha_domain)
        attributes = new_state.get("attributes", {})
        device_class = attributes.get("device_class")
        entity_class = DEVICE_CLASS_ALIASES.get(device_class, device_class)

        state = new_state.get("state")
        normalized: Any = state
        if state in ("on", "off"):
            normalized = state == "on"
        else:
            try:
                normalized = float(state)
            except (TypeError, ValueError):
                pass

        msg = new_message(
            MessageType.STATE_CHANGED,
            adapter=self.name,
            protocol=self.protocol,
            bridge="home_assistant",
            raw_address=entity_id,
            device_id=entity_id,
            entity=Entity(
                id=entity_id,
                domain=domain,
                entity_class=entity_class,
                name=attributes.get("friendly_name"),
            ),
            value=Value(
                raw=state,
                normalized=normalized,
                unit=attributes.get("unit_of_measurement"),
                datatype=type(normalized).__name__,
            ),
            trust_level=self.trust_level,
            raw={"event": event},
        )
        return self.emit(msg)
