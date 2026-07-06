"""Adapter OPC UA (WIP).

OPC UA est déjà sémantique (hiérarchie, types, unités) : le bus doit
respecter cette richesse au lieu de l'écraser. Chaque NodeSpec relie
un node id à une entité normalisée, en gardant le browse path.

État : normalisation des data changes en place ; le client
(asyncua), la session sécurisée et les subscriptions restent à
brancher.
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
class NodeSpec:
    """Un node OPC UA suivi et sa sémantique bus."""

    node_id: str  # ex: "ns=2;s=Boiler1.Temperature"
    entity_id: str
    domain: Domain
    entity_class: EntityClass | None = None
    unit: str | None = None
    browse_path: str | None = None  # ex: "/Factory/Line1/Boiler1/Temperature"
    asset: str | None = None


class OPCUAAdapter(BaseAdapter):
    """Read/subscribe minimal sur un ensemble de nodes déclarés."""

    protocol = "opcua"

    def __init__(
        self,
        bus: UniversalJsonBus,
        endpoint: str,
        nodes: list[NodeSpec],
        name: str = "opcua_adapter",
        trust_level: TrustLevel = TrustLevel.LOCAL_NETWORK,
    ) -> None:
        super().__init__(bus, name=name, mode=AdapterMode.READ_ONLY, trust_level=trust_level)
        self.endpoint = endpoint
        self.nodes = {spec.node_id: spec for spec in nodes}

    def start(self) -> None:
        # TODO: client asyncua, security policy, création des subscriptions
        raise AdapterNotReady(self.name, "opcua client not wired yet (WIP)")

    # -- normalisation (testable sans serveur) --------------------------------

    def handle_data_change(
        self, node_id: str, value: object, source_quality: str = "good"
    ) -> int:
        """Normalise un data change OPC UA. Retourne le nb de handlers notifiés."""
        spec = self.nodes.get(node_id)
        if spec is None:
            logger.debug("data change on untracked node '%s' dropped", node_id)
            return 0
        msg = new_message(
            MessageType.TELEMETRY,
            adapter=self.name,
            protocol=self.protocol,
            raw_address=node_id,
            endpoint=self.endpoint,
            browse_path=spec.browse_path,
            entity=Entity(
                id=spec.entity_id,
                domain=spec.domain.value,
                entity_class=spec.entity_class.value if spec.entity_class else None,
                asset=spec.asset,
            ),
            value=Value(raw=value, normalized=value, unit=spec.unit, datatype=type(value).__name__),
            capabilities=["read", "subscribe"],
            trust_level=self.trust_level,
            raw={"node_id": node_id, "value": value, "source_quality": source_quality},
        )
        msg.quality.source_quality = source_quality
        return self.emit(msg)
