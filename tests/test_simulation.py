"""Tests du Simulation Lab et du scénario complet motion -> light."""

import unittest

from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.simulation.devices import (
    SimulatedMotionSensor,
    SimulatedPowerMeter,
    SimulatedSwitch,
    SimulatedTemperatureSensor,
)
from jabfy_bus.simulation.lab import SimulationLab
from jabfy_bus.simulation.scenarios import run_motion_light_demo


class TestSimulatedDevices(unittest.TestCase):
    def test_temperature_stays_bounded(self):
        sensor = SimulatedTemperatureSensor("t1", base=21.0, seed=42)
        for _ in range(500):
            reading = sensor.tick()[0]
        self.assertGreater(reading.value, 10.0)
        self.assertLess(reading.value, 32.0)

    def test_motion_force(self):
        sensor = SimulatedMotionSensor("m1", probability=0.0, seed=1)
        self.assertFalse(sensor.tick()[0].value)
        sensor.force(True)
        self.assertTrue(sensor.tick()[0].value)
        self.assertFalse(sensor.tick()[0].value)  # le forçage ne dure qu'un tick

    def test_switch_commands(self):
        switch = SimulatedSwitch("s1")
        self.assertFalse(switch.state)
        switch.apply_command("turn_on")
        self.assertTrue(switch.state)
        switch.apply_command("toggle")
        self.assertFalse(switch.state)

    def test_power_meter_accumulates_energy(self):
        meter = SimulatedPowerMeter("p1", base_power=1000.0, seed=3)
        for _ in range(60):
            meter.tick()
        self.assertGreater(meter.energy_kwh, 0.5)


class TestSimulationLab(unittest.TestCase):
    def test_tick_publishes_on_bus(self):
        bus = UniversalJsonBus()
        received = []
        bus.subscribe("simulation", received.append)
        lab = SimulationLab(bus)
        lab.add_device(SimulatedTemperatureSensor("t1", seed=1))
        lab.add_device(SimulatedPowerMeter("p1", seed=2))
        emitted = lab.tick()
        self.assertEqual(emitted, 3)  # 1 temp + 2 lectures compteur
        self.assertEqual(len(received), 3)
        self.assertTrue(all(m.source.protocol == "simulation" for m in received))


class TestMotionLightScenario(unittest.TestCase):
    """Le scénario de démo Phase 1, de bout en bout."""

    def test_full_pipeline(self):
        stack = run_motion_light_demo(steps=10)

        # le mouvement forcé a déclenché une proposition, approuvée et exécutée
        self.assertTrue(stack.lamp.state, "lamp should be ON after motion")
        self.assertGreaterEqual(stack.executor.executed, 1)
        self.assertEqual(stack.executor.failed, 0)

        # la décision est tracée et la chaîne d'audit est intègre
        self.assertGreaterEqual(len(stack.audit), 1)
        self.assertTrue(stack.audit.verify())

        # le registre a vu les entités simulées
        self.assertIsNotNone(stack.registry.get("binary_sensor.salon_motion"))
        self.assertIsNotNone(stack.registry.get("switch.salon_lamp"))

        # correlation chain : executed -> approved -> requested
        executed = stack.bus.history("command.executed")
        self.assertEqual(len(executed), 1)
        approved = stack.bus.history("command.approved")
        self.assertEqual(executed[0].correlation_id, approved[0].correlation_id)


if __name__ == "__main__":
    unittest.main()
