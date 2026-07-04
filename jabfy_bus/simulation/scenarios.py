"""Scénarios de démonstration du pipeline complet.

Scénario de référence (Phase 1) :

    mouvement salon détecté
    -> raisonnement propose d'allumer la lampe (command.requested)
    -> Verification Engine valide (risque moyen + policy dédiée)
    -> Execution Layer actionne le switch simulé
    -> audit append-only
"""

from __future__ import annotations

from dataclasses import dataclass

from jabfy_bus.audit.log import AuditLog
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.message import BusMessage, Entity, new_message
from jabfy_bus.core.registry import EntityRegistry
from jabfy_bus.core.types import (
    Action,
    Domain,
    EntityClass,
    MessageType,
    RiskLevel,
    TrustLevel,
)
from jabfy_bus.execution.executor import ExecutionLayer
from jabfy_bus.simulation.devices import SimulatedMotionSensor, SimulatedSwitch, SimulatedTemperatureSensor
from jabfy_bus.simulation.lab import SimulationLab
from jabfy_bus.verification.engine import VerificationEngine
from jabfy_bus.verification.policies import Policy


@dataclass
class DemoStack:
    """Pipeline complet câblé, prêt à tourner."""

    bus: UniversalJsonBus
    lab: SimulationLab
    registry: EntityRegistry
    engine: VerificationEngine
    executor: ExecutionLayer
    audit: AuditLog
    motion: SimulatedMotionSensor
    lamp: SimulatedSwitch


class MotionLightRule:
    """Raisonnement minimal : mouvement détecté -> proposer d'allumer la lampe.

    C'est un stub du futur Reasoning Engine : il ne publie jamais de
    commande native, uniquement des command.requested sur le bus.
    """

    def __init__(self, bus: UniversalJsonBus, motion_entity: str, lamp_device: str) -> None:
        self.bus = bus
        self.motion_entity = motion_entity
        self.lamp_device = lamp_device
        self.proposals = 0

    def attach(self) -> None:
        self.bus.subscribe(MessageType.SIMULATION.value, self.on_message, name="motion_light_rule")
        self.bus.subscribe(MessageType.TELEMETRY.value, self.on_message, name="motion_light_rule")

    def on_message(self, message: BusMessage) -> None:
        if message.entity is None or message.entity.id != self.motion_entity:
            return
        if message.value is None or message.value.normalized is not True:
            return
        self.proposals += 1
        request = new_message(
            MessageType.COMMAND_REQUESTED,
            adapter="reasoning_stub",
            protocol="internal",
            entity=Entity(
                id=f"switch.{self.lamp_device}",
                domain=Domain.SWITCH.value,
                entity_class=EntityClass.SWITCHABLE.value,
                location="salon",
            ),
            command={
                "action": Action.TURN_ON.value,
                "target": self.lamp_device,
                "protocol": "simulation",
                "params": {},
            },
            trust_level=TrustLevel.INTERNAL,
            correlation_id=message.message_id,
            raw={"triggered_by": message.entity.id},
        )
        self.bus.publish(request)


def build_demo_stack(audit_path: str | None = None) -> DemoStack:
    """Câble le pipeline complet du scénario motion -> light."""
    bus = UniversalJsonBus()
    audit = AuditLog(audit_path)
    audit.attach(bus)

    registry = EntityRegistry()
    registry.attach(bus)

    lab = SimulationLab(bus)
    motion = lab.add_device(SimulatedMotionSensor("salon_motion", location="salon", probability=0.0, seed=7))
    lamp = lab.add_device(SimulatedSwitch("salon_lamp", location="salon"))
    lab.add_device(SimulatedTemperatureSensor("salon_temp", location="salon", seed=7))

    engine = VerificationEngine(
        bus,
        policies=[
            Policy(
                name="home_light_low_risk_v1",
                effect="allow",
                max_risk=RiskLevel.MEDIUM,
                domains={Domain.SWITCH.value, Domain.LIGHT.value},
                actions={Action.TURN_ON.value, Action.TURN_OFF.value, Action.TOGGLE.value},
                min_trust=TrustLevel.INTERNAL,
            ),
        ],
    )
    engine.attach()

    executor = ExecutionLayer(bus, audit=audit)
    executor.register_transport("simulation", lab.transport)
    executor.attach()

    rule = MotionLightRule(bus, "binary_sensor.salon_motion", "salon_lamp")
    rule.attach()

    return DemoStack(
        bus=bus,
        lab=lab,
        registry=registry,
        engine=engine,
        executor=executor,
        audit=audit,
        motion=motion,
        lamp=lamp,
    )


def run_motion_light_demo(steps: int = 10, audit_path: str | None = None) -> DemoStack:
    """Fait tourner le scénario : mouvement forcé au 3e tick."""
    stack = build_demo_stack(audit_path)
    for step in range(steps):
        if step == 3:
            stack.motion.force(True)
        stack.lab.tick()
    return stack
