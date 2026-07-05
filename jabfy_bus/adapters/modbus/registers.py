"""Register map Modbus avec sémantique.

Modbus dit "registre 40001 = 217". Sans mapping externe, cette valeur
ne veut rien dire. Le RegisterMap attache à chaque registre son sens
(entité, classe, unité, échelle) et sa politique d'écriture.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from jabfy_bus.core.types import Domain, EntityClass


class RegisterType(str, Enum):
    COIL = "coil"
    DISCRETE_INPUT = "discrete_input"
    INPUT_REGISTER = "input_register"
    HOLDING_REGISTER = "holding_register"

    @property
    def writable_type(self) -> bool:
        return self in (RegisterType.COIL, RegisterType.HOLDING_REGISTER)


@dataclass(frozen=True)
class RegisterSpec:
    """Sémantique d'un registre Modbus."""

    address: int
    register_type: RegisterType
    entity_id: str
    domain: Domain
    entity_class: EntityClass | None = None
    unit: str | None = None
    scale: float = 1.0
    offset: float = 0.0
    asset: str | None = None
    write_allowed: bool = False  # opt-in explicite, jamais par défaut

    def decode(self, raw: int | bool) -> float | bool:
        """Valeur brute registre -> valeur physique."""
        if isinstance(raw, bool) or self.register_type in (
            RegisterType.COIL,
            RegisterType.DISCRETE_INPUT,
        ):
            return bool(raw)
        return raw * self.scale + self.offset

    def encode(self, value: float | bool) -> int:
        """Valeur physique -> valeur brute registre (pour écriture)."""
        if self.register_type in (RegisterType.COIL, RegisterType.DISCRETE_INPUT):
            return int(bool(value))
        return round((float(value) - self.offset) / self.scale)


class RegisterMap:
    """Ensemble des registres connus d'un équipement (unit_id)."""

    def __init__(self, unit_id: int, specs: list[RegisterSpec] | None = None) -> None:
        self.unit_id = unit_id
        self._by_key: dict[tuple[RegisterType, int], RegisterSpec] = {}
        for spec in specs or []:
            self.add(spec)

    def add(self, spec: RegisterSpec) -> "RegisterMap":
        if spec.write_allowed and not spec.register_type.writable_type:
            raise ValueError(
                f"register {spec.address} ({spec.register_type.value}) cannot be writable"
            )
        self._by_key[(spec.register_type, spec.address)] = spec
        return self

    def get(self, register_type: RegisterType, address: int) -> RegisterSpec | None:
        return self._by_key.get((register_type, address))

    def specs(self) -> list[RegisterSpec]:
        return list(self._by_key.values())

    def readable(self) -> list[RegisterSpec]:
        return self.specs()

    def writable(self) -> list[RegisterSpec]:
        return [s for s in self.specs() if s.write_allowed]
