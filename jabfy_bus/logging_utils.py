"""Configuration du logging du bus.

Deux formats : lisible (dev/lab) ou JSON lines (production, ingestion
par la stack d'observabilité).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Une ligne JSON par événement de log."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """Configure le logger racine `jabfy_bus`."""
    root = logging.getLogger("jabfy_bus")
    root.setLevel(level.upper())
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    if json_format:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
        )
    root.addHandler(handler)
    root.propagate = False
