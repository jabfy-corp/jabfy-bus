"""Tests de la normalisation Matter (WIP)."""

import unittest

from jabfy_bus.adapters.matter.adapter import MatterAdapter
from jabfy_bus.core.bus import UniversalJsonBus


class TestMatterAdapter(unittest.TestCase):
    def setUp(self):
        self.bus = UniversalJsonBus()
        self.received = []
        self.bus.subscribe("telemetry", self.received.append)
        self.bus.subscribe("state.*", self.received.append)
        self.adapter = MatterAdapter(self.bus)

    def test_onoff_report_normalized(self):
        self.adapter.handle_attribute_report("0x1234", 1, "OnOff", "OnOff", True)
        msg = self.received[0]
        self.assertEqual(msg.message_type, "state.changed")
        self.assertEqual(msg.entity.domain, "light")
        self.assertIs(msg.value.normalized, True)
        self.assertEqual(msg.source.extra["fabric_id"], "jabfy-home")
        self.assertEqual(msg.source.raw_address, "0x1234/ep1/OnOff/OnOff")

    def test_temperature_scaled_from_centidegrees(self):
        self.adapter.handle_attribute_report(
            "0x1234", 2, "TemperatureMeasurement", "MeasuredValue", 2170
        )
        msg = self.received[0]
        self.assertAlmostEqual(msg.value.normalized, 21.7)
        self.assertEqual(msg.value.raw, 2170)
        self.assertEqual(msg.value.unit, "°C")

    def test_unmapped_cluster_dropped(self):
        emitted = self.adapter.handle_attribute_report("0x1", 1, "Basic", "VendorName", "x")
        self.assertEqual(emitted, 0)
        self.assertEqual(self.adapter.unmapped, 1)
        self.assertEqual(self.received, [])


if __name__ == "__main__":
    unittest.main()
