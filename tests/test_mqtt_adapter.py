"""Tests de l'adapter MQTT et du mapping de topics."""

import unittest

from jabfy_bus.adapters.mqtt.adapter import MQTTAdapter, parse_payload
from jabfy_bus.adapters.mqtt.mapping import TopicMapper, TopicRule, topic_matches
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.errors import WriteNotAllowed
from jabfy_bus.core.types import AdapterMode, Domain, EntityClass


class TestTopicMatching(unittest.TestCase):
    def test_plus_wildcard(self):
        captures = topic_matches("zigbee2mqtt/+/temperature", "zigbee2mqtt/salon/temperature")
        self.assertEqual(captures, {"wild_0": "salon"})

    def test_hash_wildcard(self):
        captures = topic_matches("shellies/#", "shellies/plug1/relay/0/power")
        self.assertEqual(captures, {"wild_0": "plug1/relay/0/power"})

    def test_no_match(self):
        self.assertIsNone(topic_matches("a/+/c", "a/b/d"))
        self.assertIsNone(topic_matches("a/b", "a/b/c"))


class TestParsePayload(unittest.TestCase):
    def test_json_payload(self):
        self.assertEqual(parse_payload(b'{"temperature": 21.7}'), {"temperature": 21.7})

    def test_scalar_json(self):
        self.assertEqual(parse_payload(b"21.7"), 21.7)

    def test_plain_text_fallback(self):
        self.assertEqual(parse_payload(b"ON"), "ON")


class FakeClient:
    def __init__(self):
        self.published = []
        self.subscribed = []
        self.connected = False

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def subscribe(self, topic):
        self.subscribed.append(topic)

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))


class TestMQTTAdapter(unittest.TestCase):
    def setUp(self):
        self.bus = UniversalJsonBus()
        self.received = []
        self.bus.subscribe("telemetry", self.received.append)
        self.mapper = TopicMapper([
            TopicRule(
                pattern="home/+/temperature",
                domain=Domain.SENSOR,
                entity_class=EntityClass.TEMPERATURE,
                unit="°C",
                value_key="value",
                entity_id="sensor.{wild_0}_temperature",
            )
        ])
        self.adapter = MQTTAdapter(self.bus, self.mapper, client=FakeClient())

    def test_mapped_topic_produces_normalized_message(self):
        self.adapter.handle_message("home/salon/temperature", b'{"value": 21.7}', qos=1)
        self.assertEqual(len(self.received), 1)
        msg = self.received[0]
        self.assertEqual(msg.entity.id, "sensor.salon_temperature")
        self.assertEqual(msg.value.normalized, 21.7)
        self.assertEqual(msg.source.raw_address, "home/salon/temperature")
        # le payload brut n'est jamais perdu
        self.assertEqual(msg.raw["payload"], {"value": 21.7})
        self.assertEqual(msg.raw["qos"], 1)

    def test_unmapped_topic_dropped(self):
        self.adapter.handle_message("other/topic", b"1")
        self.assertEqual(self.received, [])
        self.assertEqual(self.adapter.dropped, 1)

    def test_read_only_adapter_refuses_write(self):
        with self.assertRaises(WriteNotAllowed):
            self.adapter.write("home/salon/lamp/set", {"state": "ON"})

    def test_read_write_adapter_publishes(self):
        client = FakeClient()
        adapter = MQTTAdapter(
            self.bus, self.mapper, client=client, mode=AdapterMode.READ_WRITE
        )
        adapter.write("home/salon/lamp/set", {"state": "ON"})
        self.assertEqual(len(client.published), 1)
        self.assertEqual(client.published[0][0], "home/salon/lamp/set")

    def test_start_subscribes(self):
        client = FakeClient()
        adapter = MQTTAdapter(
            self.bus, self.mapper, client=client, subscriptions=["home/#"]
        )
        adapter.start()
        self.assertTrue(client.connected)
        self.assertEqual(client.subscribed, ["home/#"])


if __name__ == "__main__":
    unittest.main()
