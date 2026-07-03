"""Tests de l'Execution Layer et des traducteurs."""

import unittest

from jabfy_bus.audit.log import AuditLog
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.errors import UnknownProtocol, VerificationBypass
from jabfy_bus.core.message import Entity, new_message
from jabfy_bus.core.types import MessageType, RiskLevel, TrustLevel
from jabfy_bus.execution.executor import ExecutionLayer
from jabfy_bus.execution.translators import to_http, to_mqtt, translate
from jabfy_bus.verification.engine import VerificationEngine
from jabfy_bus.verification.policies import Policy


class TestTranslators(unittest.TestCase):
    def test_mqtt_turn_on(self):
        native = to_mqtt({"action": "turn_on", "target": "zigbee2mqtt/salon_lamp"})
        self.assertEqual(native["target"], "zigbee2mqtt/salon_lamp/set")
        self.assertEqual(native["payload"], {"state": "ON"})

    def test_mqtt_set_brightness(self):
        native = to_mqtt({
            "action": "set_brightness",
            "target": "zigbee2mqtt/salon_lamp",
            "params": {"brightness": 128},
        })
        self.assertEqual(native["payload"], {"brightness": 128})

    def test_http_turn_off(self):
        native = to_http({"action": "turn_off", "target": "http://192.168.1.42/relay/0"})
        self.assertEqual(native["target"], "http://192.168.1.42/relay/0?turn=off")
        self.assertEqual(native["method"], "POST")

    def test_unknown_protocol_raises(self):
        with self.assertRaises(UnknownProtocol):
            translate("carrier_pigeon", {"action": "turn_on", "target": "x"})


class TestExecutionLayer(unittest.TestCase):
    """Pipeline complet : requested -> approved -> executed."""

    def setUp(self):
        self.bus = UniversalJsonBus()
        self.audit = AuditLog()
        self.sent = []

        engine = VerificationEngine(self.bus, policies=[
            Policy(name="allow_switches", max_risk=RiskLevel.MEDIUM,
                   domains={"switch"}, min_trust=TrustLevel.INTERNAL)
        ])
        engine.attach()

        self.executor = ExecutionLayer(self.bus, audit=self.audit)
        self.executor.register_transport(
            "simulation", lambda target, payload: self.sent.append((target, payload))
        )
        self.executor.attach()

        self.executed = []
        self.bus.subscribe("command.executed", self.executed.append)

    def request(self, protocol="simulation"):
        return new_message(
            MessageType.COMMAND_REQUESTED,
            adapter="reasoning_stub",
            protocol="internal",
            entity=Entity(id="switch.salon_lamp", domain="switch"),
            command={"action": "turn_on", "target": "salon_lamp", "protocol": protocol},
            trust_level=TrustLevel.INTERNAL,
        )

    def test_approved_command_is_executed(self):
        self.bus.publish(self.request())
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.executor.executed, 1)
        self.assertEqual(len(self.executed), 1)
        self.assertTrue(self.executed[0].raw["success"])

    def test_execution_writes_audit(self):
        self.bus.publish(self.request())
        kinds = [b.get("kind") for b in self.audit.iter_bodies()]
        self.assertIn("command.execution", kinds)
        self.assertTrue(self.audit.verify())

    def test_missing_transport_fails_gracefully(self):
        self.bus.publish(self.request(protocol="mqtt"))
        self.assertEqual(self.executor.failed, 1)
        self.assertEqual(len(self.executed), 1)
        self.assertFalse(self.executed[0].raw["success"])

    def test_forged_approval_raises_bypass(self):
        forged = new_message(
            MessageType.COMMAND_APPROVED,
            adapter="rogue_agent",  # pas verification_engine
            protocol="internal",
            command={"action": "turn_on", "target": "salon_lamp", "protocol": "simulation"},
            trust_level=TrustLevel.INTERNAL,
        )
        with self.assertRaises(VerificationBypass):
            self.executor.execute(forged)
        self.assertEqual(self.sent, [])


if __name__ == "__main__":
    unittest.main()
