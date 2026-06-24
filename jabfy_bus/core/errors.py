"""Exceptions dédiées du bus JABFY."""

from __future__ import annotations


class BusError(Exception):
    """Erreur générique du bus."""


class InvalidMessage(BusError):
    """Le message ne respecte pas le schéma bus v1.0."""

    def __init__(self, reason: str, field: str | None = None) -> None:
        self.reason = reason
        self.field = field
        super().__init__(f"invalid bus message: {reason}" + (f" (field: {field})" if field else ""))


class AdapterError(BusError):
    """Erreur côté adapter protocolaire."""

    def __init__(self, adapter: str, reason: str) -> None:
        self.adapter = adapter
        self.reason = reason
        super().__init__(f"adapter '{adapter}': {reason}")


class AdapterNotReady(AdapterError):
    """L'adapter n'est pas encore utilisable (dépendance manquante, non connecté)."""


class UnknownProtocol(BusError):
    """Aucun transport/traducteur enregistré pour ce protocole."""

    def __init__(self, protocol: str) -> None:
        self.protocol = protocol
        super().__init__(f"no transport registered for protocol '{protocol}'")


class WriteNotAllowed(BusError):
    """Tentative d'écriture via un adapter en lecture seule."""

    def __init__(self, adapter: str) -> None:
        self.adapter = adapter
        super().__init__(f"adapter '{adapter}' is read-only, write refused")


class VerificationBypass(BusError):
    """Tentative d'exécution d'une commande non passée par le Verification Engine."""

    def __init__(self, message_id: str) -> None:
        self.message_id = message_id
        super().__init__(
            f"command {message_id} did not go through the verification engine"
        )
