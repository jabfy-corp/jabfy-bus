"""Adapter Matter (WIP).

État : la normalisation des attribute reports est en place et
testable ; le commissioning et le transport (python-matter-server)
restent à brancher.
"""

from __future__ import annotations

import logging

from jabfy_bus.adapters.base import BaseAdapter
from jabfy_bus.adapters.matter.clusters import CLUSTER_MAP
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.errors import AdapterNotReady
from jabfy_bus.core.message import Entity, Value, new_message
from jabfy_bus.core.types import AdapterMode, MessageType, TrustLevel

logger = logging.getLogger(__name__)


class MatterAdapter(BaseAdapter):
    """Traduit les attribute reports Matter vers le bus."""

    protocol = "matter"

    def __init__(
        self,
        bus: UniversalJsonBus,
        fabric_id: str = "jabfy-home",
        name: str = "matter_adapter",
        mode: AdapterMode = AdapterMode.READ_ONLY,
        trust_level: TrustLevel = TrustLevel.VERIFIED_DEVICE,
    ) -> None:
        super().__init__(bus, name=name, mode=mode, trust_level=trust_level)
        self.fabric_id = fabric_id
        self.unmapped = 0

    def start(self) -> None:
        # TODO: connexion python-matter-server + subscriptions
        raise AdapterNotReady(self.name, "matter transport not wired yet (WIP)")

    # -- normalisation (testable sans fabric) ---------------------------------

    def handle_attribute_report(
        self,
        node_id: str,
        endpoint_id: int,
        cluster: str,
        attribute: str,
        value: object,
        transport: str = "thread",
    ) -> int:
        """Normalise un attribute report Matter. Retourne le nb de handlers notifiés."""
        mapping = CLUSTER_MAP.get((cluster, attribute))
        if mapping is None:
            self.unmapped += 1
            logger.debug("no mapping for cluster %s.%s, report dropped", cluster, attribute)
            return 0

        normalized = value
        if isinstance(value, (int, float)) and mapping.scale != 1.0:
            normalized = round(value * mapping.scale, 2)

        msg = new_message(
            MessageType.STATE_CHANGED if cluster == "OnOff" else MessageType.TELEMETRY,
            adapter=self.name,
            protocol=self.protocol,
            raw_address=f"{node_id}/ep{endpoint_id}/{cluster}/{attribute}",
            device_id=node_id,
            transport=transport,
            fabric_id=self.fabric_id,
            endpoint_id=endpoint_id,
            cluster=cluster,
            attribute=attribute,
            entity=Entity(
                id=f"{mapping.domain.value}.matter_{node_id}_ep{endpoint_id}_{cluster.lower()}",
                domain=mapping.domain.value,
                entity_class=mapping.entity_class.value if mapping.entity_class else None,
            ),
            value=Value(
                raw=value,
                normalized=normalized,
                unit=mapping.unit,
                datatype=type(normalized).__name__,
                scale=mapping.scale if mapping.scale != 1.0 else None,
            ),
            capabilities=list(mapping.capabilities),
            trust_level=self.trust_level,
            raw={
                "node_id": node_id,
                "endpoint_id": endpoint_id,
                "cluster": cluster,
                "attribute": attribute,
                "value": value,
            },
        )
        return self.emit(msg)
