"""Tests du Verification Engine et des policies."""

import unittest
from datetime import datetime, time

from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.message import Entity, new_message
from jabfy_bus.core.types import Action, MessageType, RiskLevel, TrustLevel
from jabfy_bus.verification.engine import VerificationEngine
from jabfy_bus.verification.policies import Policy, TimeWindow, policy_from_dict
from jabfy_bus.verification.risk import classify_risk


def command_request(action="turn_on", domain="switch", entity_id="switch.salon_lamp",
                    trust=TrustLevel.INTERNAL):
    return new_message(
        MessageType.COMMAND_REQUESTED,
        adapter="reasoning_stub",
        protocol="internal",
        entity=Entity(id=entity_id, domain=domain),
        command={"action": action, "target": "salon_lamp", "protocol": "simulation"},
        trust_level=trust,
    )


class TestRiskClassification(unittest.TestCase):
    def test_light_on_is_medium(self):
        entity = Entity(id="light.kitchen", domain="light")
        self.assertIs(classify_risk(Action.TURN_ON, entity), RiskLevel.MEDIUM)

    def test_unlock_is_high(self):
        entity = Entity(id="lock.front_door", domain="lock")
        self.assertIs(classify_risk(Action.UNLOCK, entity), RiskLevel.HIGH)

    def test_lock_domain_raises_floor(self):
        entity = Entity(id="lock.front_door", domain="lock")
        self.assertIs(classify_risk(Action.TURN_ON, entity), RiskLevel.HIGH)

    def test_machine_domain_is_critical(self):
        entity = Entity(id="machine.press_01", domain="machine")
        self.assertIs(classify_risk(Action.START, entity), RiskLevel.CRITICAL)

    def test_cover_position_is_medium(self):
        entity = Entity(id="cover.salon_blind", domain="cover")
        self.assertIs(classify_risk(Action.SET_POSITION, entity), RiskLevel.MEDIUM)

    def test_unknown_action_is_critical(self):
        self.assertIs(classify_risk("frobnicate"), RiskLevel.CRITICAL)


class TestTimeWindow(unittest.TestCase):
    def test_normal_window(self):
        window = TimeWindow(time(8, 0), time(22, 0))
        self.assertTrue(window.contains(time(12, 0)))
        self.assertFalse(window.contains(time(23, 0)))

    def test_overnight_window(self):
        window = TimeWindow(time(22, 0), time(6, 0))
        self.assertTrue(window.contains(time(23, 30)))
        self.assertTrue(window.contains(time(5, 0)))
        self.assertFalse(window.contains(time(12, 0)))


class TestVerificationEngine(unittest.TestCase):
    def setUp(self):
        self.bus = UniversalJsonBus()
        self.approved = []
        self.rejected = []
        self.bus.subscribe("command.approved", self.approved.append)
        self.bus.subscribe("command.rejected", self.rejected.append)

    def make_engine(self, policies, at=datetime(2026, 7, 1, 14, 0)):
        engine = VerificationEngine(self.bus, policies=policies, clock=lambda: at)
        engine.attach()
        return engine

    def test_matching_allow_policy_approves(self):
        self.make_engine([
            Policy(name="lights_ok", max_risk=RiskLevel.MEDIUM,
                   domains={"switch", "light"}, min_trust=TrustLevel.INTERNAL)
        ])
        self.bus.publish(command_request())
        self.assertEqual(len(self.approved), 1)
        self.assertEqual(self.rejected, [])
        self.assertEqual(self.approved[0].raw["decision"]["policy"], "lights_ok")

    def test_no_policy_medium_risk_default_denied(self):
        self.make_engine([])
        self.bus.publish(command_request())
        self.assertEqual(self.approved, [])
        self.assertEqual(len(self.rejected), 1)
        self.assertEqual(self.rejected[0].raw["decision"]["policy"], "default_deny")

    def test_deny_policy_rejects(self):
        self.make_engine([
            Policy(name="no_switches", effect="deny", max_risk=RiskLevel.CRITICAL,
                   domains={"switch"}, min_trust=TrustLevel.UNTRUSTED)
        ])
        self.bus.publish(command_request())
        self.assertEqual(len(self.rejected), 1)

    def test_policy_outside_time_window_falls_through(self):
        self.make_engine(
            [Policy(name="day_only", max_risk=RiskLevel.MEDIUM,
                    time_window=TimeWindow(time(8, 0), time(20, 0)),
                    min_trust=TrustLevel.INTERNAL)],
            at=datetime(2026, 7, 1, 23, 0),
        )
        self.bus.publish(command_request())
        self.assertEqual(len(self.rejected), 1)

    def test_low_trust_source_not_matched_by_high_trust_policy(self):
        self.make_engine([
            Policy(name="trusted_only", max_risk=RiskLevel.MEDIUM,
                   min_trust=TrustLevel.INTERNAL)
        ])
        self.bus.publish(command_request(trust=TrustLevel.LOCAL_NETWORK))
        self.assertEqual(len(self.rejected), 1)

    def test_decision_carries_correlation_id(self):
        self.make_engine([])
        request = command_request()
        self.bus.publish(request)
        self.assertEqual(self.rejected[0].correlation_id, request.message_id)


class TestPolicyFromDict(unittest.TestCase):
    def test_full_roundtrip(self):
        policy = policy_from_dict({
            "name": "home_light_low_risk_v1",
            "effect": "allow",
            "max_risk": "medium",
            "domains": ["light", "switch"],
            "actions": ["turn_on", "turn_off"],
            "min_trust": "internal",
            "time_window": {"start": "07:00", "end": "23:00"},
        })
        self.assertEqual(policy.name, "home_light_low_risk_v1")
        self.assertIs(policy.max_risk, RiskLevel.MEDIUM)
        self.assertIn("light", policy.domains)
        self.assertTrue(policy.time_window.contains(time(12, 0)))


if __name__ == "__main__":
    unittest.main()
