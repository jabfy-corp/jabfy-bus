"""Journal d'audit append-only avec chaînage de hash.

Chaque enregistrement contient le hash SHA-256 du précédent : toute
altération a posteriori casse la chaîne et se détecte via `verify()`.
Format : JSON Lines, un enregistrement par ligne.
"""

from __future__ import annotations

import hashlib
import json
import os
from threading import RLock
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.message import BusMessage

GENESIS = "0" * 64


def _canonical(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _record_hash(prev_hash: str, body: dict[str, Any]) -> str:
    return hashlib.sha256((prev_hash + _canonical(body)).encode("utf-8")).hexdigest()


@dataclass
class AuditRecord:
    seq: int
    timestamp: str
    body: dict[str, Any]
    prev_hash: str
    hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "timestamp": self.timestamp,
            "body": self.body,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }


class AuditLog:
    """Journal append-only. `path=None` = journal en mémoire (tests, simulation)."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else None
        self._records: list[AuditRecord] = []
        self._last_hash = GENESIS
        self._lock = RLock()
        self._failed = False
        if self.path is not None and self.path.exists():
            self._load()
            if not self.verify():
                raise ValueError("Audit chain is invalid; refusing to append")

    # -- écriture -----------------------------------------------------------

    def append(self, body: dict[str, Any]) -> AuditRecord:
        with self._lock:
            return self._append(body)

    def _append(self, body: dict[str, Any]) -> AuditRecord:
        if self._failed:
            raise OSError("Audit writer failed; reopen and verify the journal before retrying")
        record = AuditRecord(
            seq=len(self._records),
            timestamp=datetime.now(timezone.utc).isoformat(),
            body=body,
            prev_hash=self._last_hash,
            hash="",
        )
        record.hash = _record_hash(record.prev_hash, {
            "seq": record.seq,
            "timestamp": record.timestamp,
            "body": record.body,
        })
        if self.path is not None:
            try:
                with self.path.open("a", encoding="utf-8") as fh:
                    fh.write(_canonical(record.to_dict()) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            except OSError:
                self._failed = True
                raise
        self._records.append(record)
        self._last_hash = record.hash
        return record

    def record_message(self, message: BusMessage) -> AuditRecord:
        """Trace un message du bus tel quel."""
        return self.append({"kind": "bus_message", "message": message.to_dict()})

    def attach(self, bus: UniversalJsonBus, patterns: tuple[str, ...] = ("command.*", "audit")) -> None:
        """Trace automatiquement les messages sensibles du bus."""
        for pattern in patterns:
            bus.subscribe(pattern, self.record_message, name="audit_log")

    # -- lecture / vérification ------------------------------------------------

    def __len__(self) -> int:
        return len(self._records)

    def records(self) -> list[AuditRecord]:
        return list(self._records)

    def iter_bodies(self) -> Iterator[dict[str, Any]]:
        for record in self._records:
            yield record.body

    def verify(self) -> bool:
        """Vérifie l'intégrité de toute la chaîne."""
        prev = GENESIS
        for record in self._records:
            if record.prev_hash != prev:
                return False
            expected = _record_hash(prev, {
                "seq": record.seq,
                "timestamp": record.timestamp,
                "body": record.body,
            })
            if record.hash != expected:
                return False
            prev = record.hash
        return True

    # -- persistance -------------------------------------------------------------

    def _load(self) -> None:
        assert self.path is not None
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                record = AuditRecord(**data)
                self._records.append(record)
                self._last_hash = record.hash


def verify_file(path: str | Path) -> bool:
    """Vérifie un fichier d'audit sans le charger dans un AuditLog actif."""
    try:
        return AuditLog(path).verify()
    except (ValueError, TypeError, KeyError):
        return False
