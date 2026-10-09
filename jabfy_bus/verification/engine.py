"""Verification Engine.

Pipeline obligatoire :

    command.requested -> Verification Engine -> command.approved | command.rejected

Interdit absolu : IA -> publish direct vers un protocole externe.
L'Execution Layer ne consomme que des `command.approved` émis ici.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from datetime import datetime
from threading import RLock
from typing import Callable

from jabfy_bus.audit.log import AuditLog
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.message import BusMessage, new_message
from jabfy_bus.core.types import MessageType, RiskLevel, TrustLevel
from jabfy_bus.verification.policies import Policy, PolicyDecision
from jabfy_bus.verification.risk import classify_risk

logger = logging.getLogger(__name__)

Clock = Callable[[], datetime]


class VerificationEngine:
    """Évalue chaque command.requested contre les policies."""

    def __init__(
        self,
        bus: UniversalJsonBus,
        policies: list[Policy] | None = None,
        clock: Clock | None = None,
        authorizer: Callable[[BusMessage], PolicyDecision] | None = None,
        audit: AuditLog | None = None,
    ) -> None:
        self.bus = bus
        self.policies: list[Policy] = list(policies or [])
        self.clock: Clock = clock or datetime.now
        self.decisions: list[PolicyDecision] = []
        self.authorizer = authorizer
        self.audit = audit
        self._admissions: dict[str, dict] = {}
        self._lock = RLock()

    def attach(self) -> None:
        self.bus.subscribe(
            MessageType.COMMAND_REQUESTED.value, self.review, name="verification_engine"
        )

    # -- décision ----------------------------------------------------------

    def review(self, message: BusMessage) -> PolicyDecision:
        with self._lock:
            return self._review(message)

    def _review(self, message: BusMessage) -> PolicyDecision:
        if self.authorizer is not None:
            try:
                decision = self.authorizer(message)
            except Exception:
                logger.exception("Authorization failed; command denied")
                decision = PolicyDecision("rejected", "guard_error", "Authorization unavailable", RiskLevel.CRITICAL)
            self.decisions.append(decision)
            self._publish_decision(message, decision)
            return decision
        command = message.command or {}
        action = command.get("action", "")
        risk = classify_risk(action, message.entity)
        now = self.clock().time()

        decision: PolicyDecision | None = None
        for policy in self.policies:
            if policy.matches(message, risk, now):
                status = "approved" if policy.effect == "allow" else "rejected"
                decision = PolicyDecision(
                    status=status,
                    policy=policy.name,
                    reason=f"matched policy '{policy.name}' (effect={policy.effect})",
                    risk=risk,
                )
                break

        if decision is None:
            # Default : seul le risque faible passe sans policy explicite.
            if risk is RiskLevel.LOW:
                decision = PolicyDecision(
                    status="approved",
                    policy="default_low_risk",
                    reason="no matching policy, low risk auto-approved",
                    risk=risk,
                )
            else:
                decision = PolicyDecision(
                    status="rejected",
                    policy="default_deny",
                    reason=f"no matching policy for risk '{risk.value}', default deny",
                    risk=risk,
                )

        self.decisions.append(decision)
        self._publish_decision(message, decision)
        return decision

    def _publish_decision(self, request: BusMessage, decision: PolicyDecision) -> None:
        message_type = (
            MessageType.COMMAND_APPROVED if decision.approved else MessageType.COMMAND_REJECTED
        )
        outcome = new_message(
            message_type,
            adapter="verification_engine",
            protocol="internal",
            entity=request.entity,
            command=dict(request.command or {}),
            trust_level=TrustLevel.INTERNAL,
            correlation_id=request.message_id,
            raw={
                "decision": {
                    "status": decision.status,
                    "policy": decision.policy,
                    "reason": decision.reason,
                    "risk": decision.risk.value,
                },
                "requested_by": request.source.adapter,
            },
        )
        logger.info(
            "command %s %s by policy '%s' (risk=%s)",
            request.message_id,
            decision.status,
            decision.policy,
            decision.risk.value,
        )
        # Persist BEFORE granting admission. Audit I/O errors must prevent dispatch.
        if self.audit is not None:
            self.audit.record_message(outcome)
        if decision.approved:
            self._admissions[outcome.message_id] = deepcopy(outcome.to_dict())
        try:
            self.bus.publish(outcome)
        finally:
            self._admissions.pop(outcome.message_id, None)

    def consume_approval(self, message: BusMessage) -> bool:
        """One-use admission valid only during synchronous dispatch of this exact payload."""
        with self._lock:
            expected = self._admissions.pop(message.message_id, None)
            return expected is not None and expected == message.to_dict()
