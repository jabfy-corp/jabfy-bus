"""Tests du modèle de message (schéma bus v1.0)."""

import unittest

from jabfy_bus.core.errors import InvalidMessage
from jabfy_bus.core.message import BusMessage, Entity, Value, new_message
from jabfy_bus.core.types import MessageType, TrustLevel


def make_telemetry() -> BusMessage:
    return new_message(
        MessageType.TELEMETRY,
        adapter="mqtt_adapter",
        protocol="mqtt",
        raw_address="zigbee2mqtt/salon/temp",
        entity=Entity(id="sensor.salon_temperature", domain="sensor", entity_class="temperature"),
        value=Value(raw=217, normalized=21.7, unit="°C", datatype="float", scale=0.1),
        capabilities=["read"],
        trust_level=TrustLevel.LOCAL_GATEWAY,
        raw={"topic": "zigbee2mqtt/salon/temp", "payload": {"temperature": 21.7}},
    )


class TestNewMessage(unittest.TestCase):
    def test_valid_message_passes_validation(self):
        msg = make_telemetry()
        msg.validate()  # ne doit pas lever

    def test_message_has_uuid_and_timestamp(self):
        msg = make_telemetry()
        self.assertTrue(msg.message_id)
        self.assertIn("T", msg.timestamp)
        self.assertEqual(msg.bus_version, "1.0")

    def test_user_situation_message_is_valid(self):
        msg = new_message(
            "user_situation",
            adapter="core",
            protocol="internal",
            trust_level=TrustLevel.INTERNAL,
            raw={"prompt": "allume le salon", "model": "agent"},
        )
        self.assertEqual(msg.message_type, MessageType.USER_SITUATION.value)

    def test_two_messages_have_distinct_ids(self):
        self.assertNotEqual(make_telemetry().message_id, make_telemetry().message_id)

    def test_raw_value_is_preserved_alongside_normalized(self):
        msg = make_telemetry()
        self.assertEqual(msg.value.raw, 217)
        self.assertEqual(msg.value.normalized, 21.7)


class TestValidation(unittest.TestCase):
    def test_unknown_message_type_rejected(self):
        msg = make_telemetry()
        msg.message_type = "banana"
        with self.assertRaises(InvalidMessage):
            msg.validate()

    def test_missing_adapter_rejected(self):
        msg = make_telemetry()
        msg.source.adapter = ""
        with self.assertRaises(InvalidMessage):
            msg.validate()

    def test_command_without_action_rejected(self):
        msg = make_telemetry()
        msg.message_type = MessageType.COMMAND_REQUESTED.value
        msg.command = {"target": "salon_lamp"}
        with self.assertRaises(InvalidMessage):
            msg.validate()

    def test_confidence_out_of_range_rejected(self):
        msg = make_telemetry()
        msg.quality.confidence = 1.5
        with self.assertRaises(InvalidMessage):
            msg.validate()

    def test_unknown_trust_level_rejected(self):
        msg = make_telemetry()
        msg.security.trust_level = "cosmic"
        with self.assertRaises(InvalidMessage):
            msg.validate()


class TestSerialization(unittest.TestCase):
    def test_roundtrip_dict(self):
        original = make_telemetry()
        data = original.to_dict()
        restored = BusMessage.from_dict(data)
        self.assertEqual(restored.message_id, original.message_id)
        self.assertEqual(restored.entity.id, original.entity.id)
        self.assertEqual(restored.value.normalized, 21.7)
        self.assertEqual(restored.raw["payload"]["temperature"], 21.7)

    def test_entity_class_serialized_as_class(self):
        data = make_telemetry().to_dict()
        self.assertIn("class", data["entity"])
        self.assertNotIn("entity_class", data["entity"])
        self.assertEqual(data["entity"]["class"], "temperature")


if __name__ == "__main__":
    unittest.main()
