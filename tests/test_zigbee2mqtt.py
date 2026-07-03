"""Tests de l'adapter Zigbee2MQTT."""

import json
import unittest

from jabfy_bus.adapters.zigbee2mqtt.adapter import Zigbee2MQTTAdapter
from jabfy_bus.core.bus import UniversalJsonBus


class TestZigbee2MQTTAdapter(unittest.TestCase):
    def setUp(self):
        self.bus = UniversalJsonBus()
        self.received = []
        self.bus.subscribe("telemetry", self.received.append)
        self.bus.subscribe("state.*", self.received.append)
        self.adapter = Zigbee2MQTTAdapter(self.bus)
        self.adapter.start()

    def test_multi_expose_payload_produces_one_message_per_expose(self):
        emitted = self.adapter.handle_mqtt(
            "zigbee2mqtt/salon_climate",
            b'{"temperature": 21.7, "humidity": 48.2, "battery": 87, "linkquality": 120}',
        )
        self.assertEqual(emitted, 4)
        classes = {m.entity.entity_class for m in self.received}
        self.assertEqual(classes, {"temperature", "humidity", "battery", "signal_strength"})

    def test_contact_sensor_inverted(self):
        # contact=true signifie fermé -> door normalisé False (pas ouvert)
        self.adapter.handle_mqtt("zigbee2mqtt/porte_entree", b'{"contact": true}')
        msg = self.received[0]
        self.assertEqual(msg.entity.entity_class, "door")
        self.assertEqual(msg.value.raw, True)
        self.assertEqual(msg.value.normalized, False)

    def test_state_on_normalized_to_bool(self):
        self.adapter.handle_mqtt("zigbee2mqtt/prise_tv", b'{"state": "ON"}')
        msg = self.received[0]
        self.assertEqual(msg.message_type, "state.changed")
        self.assertIs(msg.value.normalized, True)

    def test_raw_payload_kept(self):
        payload = {"temperature": 20.1, "voltage": 2985}
        self.adapter.handle_mqtt("zigbee2mqtt/capteur", json.dumps(payload).encode())
        for msg in self.received:
            self.assertEqual(msg.raw["payload"], payload)

    def test_set_echo_and_foreign_topics_ignored(self):
        self.assertEqual(self.adapter.handle_mqtt("zigbee2mqtt/lamp/set", b'{"state":"ON"}'), 0)
        self.assertEqual(self.adapter.handle_mqtt("other/topic", b"{}"), 0)
        self.assertEqual(self.received, [])

    def test_bridge_devices_inventory(self):
        devices = [
            {
                "friendly_name": "salon_motion",
                "ieee_address": "0x00158d000123abcd",
                "definition": {"model": "RTCGQ11LM"},
            }
        ]
        self.adapter.handle_mqtt("zigbee2mqtt/bridge/devices", json.dumps(devices).encode())
        self.assertIn("salon_motion", self.adapter.devices)

        self.adapter.handle_mqtt("zigbee2mqtt/salon_motion", b'{"occupancy": true}')
        msg = self.received[0]
        self.assertEqual(msg.source.device_id, "salon_motion")
        self.assertEqual(msg.source.extra.get("manufacturer"), "Aqara")
        self.assertEqual(msg.source.extra.get("ieee_address"), "0x00158d000123abcd")


if __name__ == "__main__":
    unittest.main()
