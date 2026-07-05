"""Tests de l'adapter Modbus et du register map."""

import unittest

from jabfy_bus.adapters.modbus.adapter import ModbusAdapter
from jabfy_bus.adapters.modbus.registers import RegisterMap, RegisterSpec, RegisterType
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.errors import WriteNotAllowed
from jabfy_bus.core.types import AdapterMode, Domain, EntityClass

BOILER_TEMP = RegisterSpec(
    address=40001,
    register_type=RegisterType.HOLDING_REGISTER,
    entity_id="sensor.boiler_temperature",
    domain=Domain.SENSOR,
    entity_class=EntityClass.TEMPERATURE,
    unit="°C",
    scale=0.1,
    asset="boiler_01",
)

PUMP_COIL = RegisterSpec(
    address=1,
    register_type=RegisterType.COIL,
    entity_id="switch.pump_01",
    domain=Domain.SWITCH,
    write_allowed=True,
)


class TestRegisterSpec(unittest.TestCase):
    def test_decode_applies_scale(self):
        self.assertAlmostEqual(BOILER_TEMP.decode(217), 21.7)

    def test_encode_reverses_scale(self):
        self.assertEqual(BOILER_TEMP.encode(21.7), 217)

    def test_coil_decodes_to_bool(self):
        self.assertIs(PUMP_COIL.decode(1), True)
        self.assertIs(PUMP_COIL.decode(0), False)

    def test_writable_input_register_rejected(self):
        with self.assertRaises(ValueError):
            RegisterMap(1).add(
                RegisterSpec(
                    address=30001,
                    register_type=RegisterType.INPUT_REGISTER,
                    entity_id="sensor.x",
                    domain=Domain.SENSOR,
                    write_allowed=True,
                )
            )


class FakeWriter:
    def __init__(self):
        self.writes = []

    def write(self, unit_id, register_type, address, value):
        self.writes.append((unit_id, register_type, address, value))


class TestModbusAdapter(unittest.TestCase):
    def setUp(self):
        self.bus = UniversalJsonBus()
        self.received = []
        self.bus.subscribe("telemetry", self.received.append)
        self.register_map = RegisterMap(1, [BOILER_TEMP, PUMP_COIL])
        self.values = {
            (RegisterType.HOLDING_REGISTER, 40001): 217,
            (RegisterType.COIL, 1): 0,
        }
        self.adapter = ModbusAdapter(
            self.bus,
            self.register_map,
            host="192.168.10.20",
            reader=lambda unit, rt, addr: self.values[(rt, addr)],
        )

    def test_poll_emits_decoded_values(self):
        emitted = self.adapter.poll_once()
        self.assertEqual(emitted, 2)
        by_id = {m.entity.id: m for m in self.received}
        temp = by_id["sensor.boiler_temperature"]
        self.assertEqual(temp.value.raw, 217)
        self.assertAlmostEqual(temp.value.normalized, 21.7)
        self.assertEqual(temp.value.unit, "°C")
        self.assertEqual(temp.entity.asset, "boiler_01")
        self.assertEqual(temp.source.raw_address, "holding_register:40001")

    def test_read_only_adapter_never_marks_write_allowed(self):
        self.adapter.poll_once()
        for msg in self.received:
            self.assertFalse(msg.security.write_allowed)

    def test_failing_register_does_not_block_poll(self):
        def flaky(unit, rt, addr):
            if addr == 40001:
                raise ConnectionError("timeout")
            return self.values[(rt, addr)]

        self.adapter.reader = flaky
        emitted = self.adapter.poll_once()
        self.assertEqual(emitted, 1)
        self.assertEqual(self.adapter.read_errors, 1)

    def test_write_requires_read_write_mode(self):
        with self.assertRaises(WriteNotAllowed):
            self.adapter.write_register(RegisterType.COIL, 1, True)

    def test_write_requires_spec_opt_in(self):
        writer = FakeWriter()
        adapter = ModbusAdapter(
            self.bus, self.register_map, host="x",
            reader=lambda u, rt, a: 0, writer=writer, mode=AdapterMode.READ_WRITE,
        )
        # registre non write_allowed -> refus même en read-write
        with self.assertRaises(WriteNotAllowed):
            adapter.write_register(RegisterType.HOLDING_REGISTER, 40001, 25.0)
        # coil autorisé -> ok
        adapter.write_register(RegisterType.COIL, 1, True)
        self.assertEqual(writer.writes, [(1, RegisterType.COIL, 1, 1)])


if __name__ == "__main__":
    unittest.main()
