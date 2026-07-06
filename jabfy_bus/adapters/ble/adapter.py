"""Adapter BLE présence (WIP).

Cas d'usage : détection de présence par advertisement (smartphone,
beacon, tag), plus RSSI comme signal de proximité. Attention aux MAC
randomisées : on ne suit QUE des beacons déclarés (identité stable),
jamais un scan sauvage.

État : normalisation des advertisements en place ; le scanner
(bleak) reste à brancher.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from jabfy_bus.adapters.base import BaseAdapter
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.errors import AdapterNotReady
from jabfy_bus.core.message import Entity, Value, new_message
from jabfy_bus.core.types import AdapterMode, Domain, EntityClass, MessageType, TrustLevel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KnownBeacon:
    """Beacon déclaré : seule identité que l'adapter accepte de suivre."""

    address: str  # MAC ou identifiant stable (iBeacon UUID...)
    entity_id: str
    name: str | None = None
    location: str | None = None
    rssi_threshold: int = -85  # en dessous : considéré absent


class BLEPresenceAdapter(BaseAdapter):
    """Traduit les advertisements des beacons connus en présence + RSSI."""

    protocol = "ble"

    def __init__(
        self,
        bus: UniversalJsonBus,
        beacons: list[KnownBeacon],
        name: str = "ble_adapter",
        trust_level: TrustLevel = TrustLevel.LOCAL_NETWORK,
    ) -> None:
        super().__init__(bus, name=name, mode=AdapterMode.READ_ONLY, trust_level=trust_level)
        self.beacons = {b.address.lower(): b for b in beacons}
        self.ignored = 0

    def start(self) -> None:
        # TODO: scanner bleak + fenêtre de disparition (absence après N s sans adv)
        raise AdapterNotReady(self.name, "BLE scanner not wired yet (WIP)")

    # -- normalisation (testable sans radio) -----------------------------------

    def handle_advertisement(self, address: str, rssi: int) -> int:
        """Normalise un advertisement BLE. Les adresses inconnues sont ignorées."""
        beacon = self.beacons.get(address.lower())
        if beacon is None:
            self.ignored += 1
            return 0
        present = rssi >= beacon.rssi_threshold
        emitted = self.emit(
            new_message(
                MessageType.TELEMETRY,
                adapter=self.name,
                protocol=self.protocol,
                raw_address=beacon.address,
                device_id=beacon.address,
                entity=Entity(
                    id=beacon.entity_id,
                    domain=Domain.BINARY_SENSOR.value,
                    entity_class=EntityClass.PRESENCE.value,
                    name=beacon.name,
                    location=beacon.location,
                ),
                value=Value(raw=rssi, normalized=present, datatype="bool"),
                trust_level=self.trust_level,
                raw={"address": beacon.address, "rssi": rssi},
            )
        )
        self.emit(
            new_message(
                MessageType.TELEMETRY,
                adapter=self.name,
                protocol=self.protocol,
                raw_address=beacon.address,
                device_id=beacon.address,
                entity=Entity(
                    id=f"{beacon.entity_id}_rssi",
                    domain=Domain.SENSOR.value,
                    entity_class=EntityClass.SIGNAL_STRENGTH.value,
                    location=beacon.location,
                ),
                value=Value(raw=rssi, normalized=rssi, unit="dBm", datatype="int"),
                trust_level=self.trust_level,
                raw={"address": beacon.address, "rssi": rssi},
            )
        )
        return emitted
