import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from jabfy_bus.audit.log import AuditLog
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.errors import VerificationBypass
from jabfy_bus.core.message import new_message
from jabfy_bus.core.types import RiskLevel
from jabfy_bus.execution.executor import ExecutionLayer
from jabfy_bus.verification.engine import VerificationEngine
from jabfy_bus.verification.policies import PolicyDecision


class TestAdmission(unittest.TestCase):
    def setUp(self):
        self.bus = UniversalJsonBus()
        self.audit = AuditLog()
        self.engine = VerificationEngine(self.bus, audit=self.audit, authorizer=lambda message:
            PolicyDecision("approved", "guard:ALLOWED", "ok", RiskLevel.MEDIUM))
        self.engine.attach()
        self.sent = []
        self.executor = ExecutionLayer(self.bus, approval_validator=self.engine.consume_approval)
        self.executor.register_transport("simulation", lambda *args: self.sent.append(args))

    def request(self):
        return new_message("command.requested", adapter="test", protocol="internal",
            command={"action": "turn_on", "target": "virtual", "protocol": "simulation"})

    def test_one_use_and_audit_before_execution(self):
        self.executor.attach()
        self.bus.publish(self.request())
        self.assertEqual(len(self.sent), 1)
        approved = self.bus.history("command.approved")[0]
        self.assertEqual(self.audit.records()[0].body["message"]["message_id"], approved.message_id)
        with self.assertRaises(VerificationBypass):
            self.executor.execute(approved)

    def test_forged_label_is_not_authority(self):
        forged = new_message("command.approved", adapter="verification_engine", protocol="internal",
                             correlation_id="forged", command=self.request().command)
        with self.assertRaises(VerificationBypass):
            self.executor.execute(forged)

    def test_payload_change_invalidates_admission(self):
        def tamper(message):
            message.command["target"] = "other"
        self.bus.subscribe("command.approved", tamper)
        self.executor.attach()
        self.bus.publish(self.request())
        self.assertEqual(self.sent, [])

    def test_audit_failure_prevents_execution(self):
        self.audit.record_message = Mock(side_effect=OSError("disk full"))
        self.executor.attach()
        self.bus.publish(self.request())
        self.assertEqual(self.sent, [])

    def test_authorizer_failure_denies(self):
        self.engine.authorizer = Mock(side_effect=RuntimeError("unavailable"))
        self.executor.attach()
        self.bus.publish(self.request())
        self.assertEqual(self.sent, [])
        self.assertEqual(self.engine.decisions[-1].policy, "guard_error")

    def test_failed_disk_write_does_not_advance_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = AuditLog(Path(tmp) / "missing" / "audit.jsonl")
            with self.assertRaises(OSError):
                log.append({"test": True})
            self.assertEqual(len(log), 0)
            self.assertTrue(log.verify())

    def test_corrupted_journal_cannot_be_reopened_for_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            AuditLog(path).append({"value": "original"})
            path.write_text(path.read_text().replace("original", "tampered"))
            with self.assertRaises(ValueError):
                AuditLog(path)
