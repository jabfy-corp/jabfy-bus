"""Chargement de configuration (JSON natif, YAML si PyYAML est présent)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jabfy_bus.verification.policies import Policy, policy_from_dict


@dataclass
class AdapterConfig:
    type: str
    name: str
    mode: str = "read_only"
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class BusConfig:
    """Configuration racine du bus JABFY."""

    adapters: list[AdapterConfig] = field(default_factory=list)
    policies: list[Policy] = field(default_factory=list)
    audit_path: str | None = None
    history_size: int = 500
    api_host: str = "127.0.0.1"
    api_port: int = 8080

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BusConfig":
        adapters = [
            AdapterConfig(
                type=a["type"],
                name=a.get("name", a["type"]),
                mode=a.get("mode", "read_only"),
                options=a.get("options", {}),
            )
            for a in data.get("adapters", [])
        ]
        policies = [policy_from_dict(p) for p in data.get("policies", [])]
        return cls(
            adapters=adapters,
            policies=policies,
            audit_path=data.get("audit_path"),
            history_size=data.get("history_size", 500),
            api_host=data.get("api", {}).get("host", "127.0.0.1"),
            api_port=data.get("api", {}).get("port", 8080),
        )


def load_config(path: str | Path) -> BusConfig:
    """Charge un fichier de config .json, .yaml ou .yml."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml  # noqa: PLC0415 - dépendance optionnelle
        except ImportError as exc:
            raise RuntimeError(
                "PyYAML is required for YAML configs: pip install 'jabfy-bus[yaml]'"
            ) from exc
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"config root must be a mapping, got {type(data).__name__}")
    return BusConfig.from_dict(data)
