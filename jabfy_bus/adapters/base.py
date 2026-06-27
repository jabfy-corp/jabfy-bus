"""Classe de base des adapters protocolaires.

Un adapter :
- traduit les données natives d'un protocole en BusMessage normalisés ;
- est read-only par défaut (l'écriture doit être explicitement activée) ;
- publie son état de santé sur le bus (`health`).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.errors import WriteNotAllowed
from jabfy_bus.core.message import BusMessage, Source, new_message
from jabfy_bus.core.types import AdapterMode, MessageType, TrustLevel

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """Socle commun à tous les adapters."""

    protocol: str = "unknown"

    def __init__(
        self,
        bus: UniversalJsonBus,
        name: str,
        mode: AdapterMode = AdapterMode.READ_ONLY,
        trust_level: TrustLevel = TrustLevel.LOCAL_NETWORK,
    ) -> None:
        self.bus = bus
        self.name = name
        self.mode = mode
        self.trust_level = trust_level
        self._running = False

    # -- cycle de vie --------------------------------------------------

    @abstractmethod
    def start(self) -> None:
        """Démarre l'adapter (connexion, souscriptions natives...)."""

    def stop(self) -> None:
        self._running = False
        self.report_health("stopped")

    @property
    def running(self) -> bool:
        return self._running

    # -- émission vers le bus -------------------------------------------

    def emit(self, message: BusMessage) -> int:
        """Publie sur le bus en estampillant l'adapter d'origine."""
        message.source.adapter = self.name
        if not message.source.protocol or message.source.protocol == "unknown":
            message.source.protocol = self.protocol
        message.security.trust_level = self.trust_level.value
        return self.bus.publish(message)

    def report_health(self, status: str, detail: dict[str, Any] | None = None) -> None:
        msg = new_message(
            MessageType.HEALTH,
            adapter=self.name,
            protocol=self.protocol,
            trust_level=TrustLevel.INTERNAL,
            raw={"status": status, **(detail or {})},
        )
        self.bus.publish(msg)

    # -- écriture (commandes sortantes) ----------------------------------

    def ensure_writable(self) -> None:
        """À appeler avant toute écriture vers le protocole natif."""
        if self.mode is not AdapterMode.READ_WRITE:
            raise WriteNotAllowed(self.name)

    def write(self, target: str, payload: Any) -> None:
        """Écriture native. Les adapters read-write doivent la surcharger."""
        self.ensure_writable()
        raise NotImplementedError(f"adapter '{self.name}' does not implement write()")

    # -- utilitaires -----------------------------------------------------

    def make_source(self, **kwargs: Any) -> Source:
        return Source(adapter=self.name, protocol=self.protocol, **kwargs)
