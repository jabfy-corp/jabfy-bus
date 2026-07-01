"""Tests du journal d'audit append-only."""

import tempfile
import unittest
from pathlib import Path

from jabfy_bus.audit.log import AuditLog, verify_file


class TestAuditChain(unittest.TestCase):
    def test_empty_log_verifies(self):
        self.assertTrue(AuditLog().verify())

    def test_appended_records_chain(self):
        log = AuditLog()
        log.append({"kind": "test", "n": 1})
        log.append({"kind": "test", "n": 2})
        log.append({"kind": "test", "n": 3})
        self.assertEqual(len(log), 3)
        self.assertTrue(log.verify())

    def test_records_reference_previous_hash(self):
        log = AuditLog()
        first = log.append({"n": 1})
        second = log.append({"n": 2})
        self.assertEqual(second.prev_hash, first.hash)

    def test_tampering_breaks_chain(self):
        log = AuditLog()
        log.append({"amount": 10})
        log.append({"amount": 20})
        log.records()  # copie, ne doit pas permettre la falsification
        log._records[0].body["amount"] = 9999  # falsification directe
        self.assertFalse(log.verify())


class TestAuditPersistence(unittest.TestCase):
    def test_file_roundtrip_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            log = AuditLog(path)
            log.append({"kind": "command.execution", "success": True})
            log.append({"kind": "command.execution", "success": False})

            reloaded = AuditLog(path)
            self.assertEqual(len(reloaded), 2)
            self.assertTrue(reloaded.verify())
            self.assertTrue(verify_file(path))

    def test_reloaded_log_continues_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            AuditLog(path).append({"n": 1})
            reloaded = AuditLog(path)
            reloaded.append({"n": 2})
            self.assertTrue(AuditLog(path).verify())

    def test_tampered_file_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            log = AuditLog(path)
            log.append({"secret": "original"})
            content = path.read_text(encoding="utf-8").replace("original", "tampered")
            path.write_text(content, encoding="utf-8")
            self.assertFalse(verify_file(path))


if __name__ == "__main__":
    unittest.main()
