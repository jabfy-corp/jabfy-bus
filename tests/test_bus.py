"""Tests du bus pub/sub interne."""

import unittest

from jabfy_bus.core.bus import UniversalJsonBus, match_pattern
from jabfy_bus.core.message import new_message
from jabfy_bus.core.types import MessageType, TrustLevel


def make(message_type: MessageType):
    return new_message(
        message_type,
        adapter="test_adapter",
        protocol="internal",
        trust_level=TrustLevel.INTERNAL,
        command={"action": "turn_on", "target": "x", "protocol": "simulation"}
        if message_type.value.startswith("command.")
        else None,
    )


class TestPatternMatching(unittest.TestCase):
    def test_star_matches_everything(self):
        self.assertTrue(match_pattern("*", "telemetry"))
        self.assertTrue(match_pattern("*", "command.requested"))

    def test_prefix_wildcard(self):
        self.assertTrue(match_pattern("command.*", "command.requested"))
        self.assertTrue(match_pattern("command.*", "command.approved"))
        self.assertFalse(match_pattern("command.*", "telemetry"))

    def test_exact_match(self):
        self.assertTrue(match_pattern("state.changed", "state.changed"))
        self.assertFalse(match_pattern("state.changed", "state.other"))


class TestBus(unittest.TestCase):
    def setUp(self):
        self.bus = UniversalJsonBus()

    def test_subscriber_receives_matching_message(self):
        received = []
        self.bus.subscribe("health", received.append)
        self.bus.publish(make(MessageType.HEALTH))
        self.assertEqual(len(received), 1)

    def test_subscriber_ignores_non_matching(self):
        received = []
        self.bus.subscribe("command.*", received.append)
        self.bus.publish(make(MessageType.TELEMETRY))
        self.assertEqual(received, [])

    def test_duplicate_message_id_deduplicated(self):
        received = []
        self.bus.subscribe("*", received.append)
        msg = make(MessageType.TELEMETRY)
        self.bus.publish(msg)
        self.bus.publish(msg)
        self.assertEqual(len(received), 1)

    def test_failing_handler_does_not_block_others(self):
        received = []

        def bad_handler(message):
            raise RuntimeError("boom")

        self.bus.subscribe("*", bad_handler)
        self.bus.subscribe("*", received.append)
        self.bus.publish(make(MessageType.TELEMETRY))
        self.assertEqual(len(received), 1)

    def test_unsubscribe(self):
        received = []
        sub = self.bus.subscribe("*", received.append)
        self.bus.unsubscribe(sub)
        self.bus.publish(make(MessageType.TELEMETRY))
        self.assertEqual(received, [])

    def test_history_filtered_by_pattern(self):
        self.bus.publish(make(MessageType.TELEMETRY))
        self.bus.publish(make(MessageType.COMMAND_REQUESTED))
        self.bus.publish(make(MessageType.COMMAND_APPROVED))
        self.assertEqual(len(self.bus.history()), 3)
        self.assertEqual(len(self.bus.history("command.*")), 2)
        self.assertEqual(len(self.bus.history("command.*", limit=1)), 1)


if __name__ == "__main__":
    unittest.main()
