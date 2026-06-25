"""Bus pub/sub interne (in-process).

Les adapters publient des messages normalisés ; les moteurs
(raisonnement, vérification, exécution, audit) s'abonnent par
pattern de type de message :

    bus.subscribe("state.*", handler)
    bus.subscribe("command.requested", handler)
    bus.subscribe("*", tap)
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

from jabfy_bus.core.message import BusMessage

logger = logging.getLogger(__name__)

Handler = Callable[[BusMessage], None]


def match_pattern(pattern: str, message_type: str) -> bool:
    """Match par segments séparés par des points, `*` = joker.

    "*"                -> tout
    "command.*"        -> command.requested, command.approved...
    "state.changed"    -> exact
    """
    if pattern == "*":
        return True
    p_parts = pattern.split(".")
    t_parts = message_type.split(".")
    if p_parts[-1] == "*":
        return t_parts[: len(p_parts) - 1] == p_parts[:-1]
    return p_parts == t_parts


@dataclass
class Subscription:
    pattern: str
    handler: Handler = field(repr=False)
    name: str = ""


class UniversalJsonBus:
    """Bus JSON universel : point de passage unique des messages."""

    def __init__(self, history_size: int = 500) -> None:
        self._subscriptions: list[Subscription] = []
        self._history: deque[BusMessage] = deque(maxlen=history_size)
        self._published_ids: set[str] = set()

    # -- souscriptions -------------------------------------------------

    def subscribe(self, pattern: str, handler: Handler, name: str = "") -> Subscription:
        sub = Subscription(pattern=pattern, handler=handler, name=name or getattr(handler, "__name__", ""))
        self._subscriptions.append(sub)
        return sub

    def unsubscribe(self, subscription: Subscription) -> None:
        try:
            self._subscriptions.remove(subscription)
        except ValueError:
            pass

    # -- publication ---------------------------------------------------

    def publish(self, message: BusMessage) -> int:
        """Valide puis diffuse le message. Retourne le nombre de handlers notifiés.

        Les messages déjà vus (même message_id) sont ignorés : déduplication.
        Une exception dans un handler n'interrompt jamais les autres.
        """
        message.validate()
        if message.message_id in self._published_ids:
            logger.debug("duplicate message %s ignored", message.message_id)
            return 0
        self._published_ids.add(message.message_id)
        self._history.append(message)

        notified = 0
        for sub in list(self._subscriptions):
            if not match_pattern(sub.pattern, message.message_type):
                continue
            try:
                sub.handler(message)
                notified += 1
            except Exception:  # noqa: BLE001 - isolation des handlers
                logger.exception(
                    "handler '%s' failed on message %s (%s)",
                    sub.name,
                    message.message_id,
                    message.message_type,
                )
        return notified

    # -- historique ----------------------------------------------------

    def history(self, pattern: str = "*", limit: int | None = None) -> list[BusMessage]:
        matches = [m for m in self._history if match_pattern(pattern, m.message_type)]
        if limit is not None:
            matches = matches[-limit:]
        return matches
