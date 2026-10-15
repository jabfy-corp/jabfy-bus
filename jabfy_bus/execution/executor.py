"""Execution Layer.

Ne consomme QUE des `command.approved` (émis par le Verification
Engine, correlation_id obligatoire). Traduit la commande normalisée
vers le protocole cible via un transport enregistré, puis publie
`command.executed` et trace dans l'audit.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from jabfy_bus.audit.log import AuditLog
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.errors import VerificationBypass
from jabfy_bus.core.message import BusMessage, new_message
from jabfy_bus.core.types import MessageType, TrustLevel
from jabfy_bus.execution.translators import translate

logger = logging.getLogger(__name__)

# Un transport envoie une requête native : transport(target, payload) -> None
Transport = Callable[[str, Any], None]


class ExecutionLayer:
    """Exécute les commandes approuvées via les transports enregistrés."""

    def __init__(self, bus: UniversalJsonBus, audit: AuditLog | None = None,
                 approval_validator: Callable[[BusMessage], bool] | None = None) -> None:
        self.bus = bus
        self.audit = audit
        self.approval_validator = approval_validator
        self._transports: dict[str, Transport] = {}
        self.executed = 0
        self.failed = 0

    def register_transport(self, protocol: str, transport: Transport) -> None:
        self._transports[protocol] = transport

    def attach(self) -> None:
        self.bus.subscribe(
            MessageType.COMMAND_APPROVED.value, self.execute, name="execution_layer"
        )

    # -- exécution ------------------------------------------------------------

    def execute(self, message: BusMessage) -> bool:
        """Exécute une commande approuvée. Retourne True si succès."""
        if (message.message_type != MessageType.COMMAND_APPROVED.value
                or message.correlation_id is None or message.source.adapter != "verification_engine"
                or (self.approval_validator is not None and not self.approval_validator(message))):
            # Défense en profondeur : une "approbation" ne venant pas du
            # Verification Engine est un contournement, pas une commande.
            raise VerificationBypass(message.message_id)

        command = dict(message.command or {})
        protocol = command.get("protocol", "")
        success = False
        error: str | None = None
        native: dict[str, Any] | None = None

        try:
            native = translate(protocol, command)
            transport = self._transports.get(protocol)
            if transport is None:
                raise LookupError(f"no transport registered for '{protocol}'")
            transport(native["target"], native["payload"])
            success = True
            self.executed += 1
        except Exception as exc:  # noqa: BLE001 - l'échec est un résultat, pas un crash
            error = str(exc)
            self.failed += 1
            logger.error("execution failed for %s: %s", message.message_id, exc)

        self._publish_result(message, command, native, success, error)
        return success

    def _publish_result(
        self,
        approved: BusMessage,
        command: dict[str, Any],
        native: dict[str, Any] | None,
        success: bool,
        error: str | None,
    ) -> None:
        result = new_message(
            MessageType.COMMAND_EXECUTED,
            adapter="execution_layer",
            protocol=command.get("protocol", "unknown"),
            entity=approved.entity,
            command=command,
            trust_level=TrustLevel.INTERNAL,
            correlation_id=approved.correlation_id,
            raw={
                "success": success,
                "error": error,
                "native_request": native,
                "approved_message_id": approved.message_id,
            },
        )
        self.bus.publish(result)
        if self.audit is not None:
            self.audit.append(
                {
                    "kind": "command.execution",
                    "actor": {"type": "execution_layer"},
                    "command": {
                        "normalized": command.get("action"),
                        "target": approved.entity.id if approved.entity else command.get("target"),
                    },
                    "decision_ref": approved.correlation_id,
                    "execution": {
                        "protocol": command.get("protocol"),
                        "success": success,
                        "error": error,
                    },
                }
            )
