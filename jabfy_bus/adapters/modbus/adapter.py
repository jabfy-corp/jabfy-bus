"""Adapter Modbus TCP.

Le lecteur/écrivain Modbus est injectable (pymodbus en production,
simulateur en lab/test). Chaque valeur publiée garde le registre brut
et la conversion appliquée.
"""

from __future__ import annotations

import logging
from typing import Callable, Protocol

from jabfy_bus.adapters.base import BaseAdapter
from jabfy_bus.adapters.modbus.registers import RegisterMap, RegisterSpec, RegisterType
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.errors import AdapterNotReady, WriteNotAllowed
from jabfy_bus.core.message import Entity, Value, new_message
from jabfy_bus.core.types import AdapterMode, MessageType, TrustLevel

logger = logging.getLogger(__name__)

# reader(unit_id, register_type, address) -> valeur brute
Reader = Callable[[int, RegisterType, int], int | bool]


class ModbusWriter(Protocol):
    def write(self, unit_id: int, register_type: RegisterType, address: int, value: int) -> None: ...


class ModbusAdapter(BaseAdapter):
    """Poll les registres d'un RegisterMap et publie les valeurs décodées."""

    protocol = "modbus_tcp"

    def __init__(
        self,
        bus: UniversalJsonBus,
        register_map: RegisterMap,
        host: str,
        port: int = 502,
        reader: Reader | None = None,
        writer: ModbusWriter | None = None,
        name: str = "modbus_adapter",
        mode: AdapterMode = AdapterMode.READ_ONLY,
        trust_level: TrustLevel = TrustLevel.LOCAL_NETWORK,
    ) -> None:
        super().__init__(bus, name=name, mode=mode, trust_level=trust_level)
        self.register_map = register_map
        self.host = host
        self.port = port
        self.reader = reader
        self.writer = writer
        self.read_errors = 0

    def start(self) -> None:
        if self.reader is None:
            raise AdapterNotReady(self.name, "no Modbus reader injected")
        self._running = True
        self.report_health(
            "started",
            {"host": self.host, "port": self.port, "registers": len(self.register_map.specs())},
        )

    def poll_once(self) -> int:
        """Lit tous les registres du map. Retourne le nb de messages émis."""
        if self.reader is None:
            raise AdapterNotReady(self.name, "no Modbus reader injected")
        emitted = 0
        for spec in self.register_map.readable():
            try:
                raw = self.reader(self.register_map.unit_id, spec.register_type, spec.address)
            except Exception as exc:  # noqa: BLE001 - un registre HS ne bloque pas le poll
                self.read_errors += 1
                logger.warning(
                    "read failed unit=%s %s@%s: %s",
                    self.register_map.unit_id,
                    spec.register_type.value,
                    spec.address,
                    exc,
                )
                continue
            self._emit_register(spec, raw)
            emitted += 1
        return emitted

    def _emit_register(self, spec: RegisterSpec, raw: int | bool) -> None:
        normalized = spec.decode(raw)
        capabilities = ["read"]
        if spec.write_allowed:
            capabilities.append("write")
        msg = new_message(
            MessageType.TELEMETRY,
            adapter=self.name,
            protocol=self.protocol,
            raw_address=f"{spec.register_type.value}:{spec.address}",
            host=self.host,
            unit_id=self.register_map.unit_id,
            register_type=spec.register_type.value,
            address=spec.address,
            entity=Entity(
                id=spec.entity_id,
                domain=spec.domain.value,
                entity_class=spec.entity_class.value if spec.entity_class else None,
                asset=spec.asset,
            ),
            value=Value(
                raw=raw,
                normalized=normalized,
                unit=spec.unit,
                datatype=type(normalized).__name__,
                scale=spec.scale,
            ),
            capabilities=capabilities,
            trust_level=self.trust_level,
            raw={
                "unit_id": self.register_map.unit_id,
                "register_type": spec.register_type.value,
                "address": spec.address,
                "value": raw,
            },
        )
        # write_allowed est porté par la sécurité du message, pas seulement le spec
        msg.security.write_allowed = spec.write_allowed and self.mode is AdapterMode.READ_WRITE
        self.emit(msg)

    # -- écriture --------------------------------------------------------------

    def write_register(self, register_type: RegisterType, address: int, value: float | bool) -> None:
        """Écrit un registre : triple contrôle (mode adapter, spec, type de registre)."""
        self.ensure_writable()
        spec = self.register_map.get(register_type, address)
        if spec is None or not spec.write_allowed:
            raise WriteNotAllowed(self.name)
        if self.writer is None:
            raise AdapterNotReady(self.name, "no Modbus writer injected")
        self.writer.write(self.register_map.unit_id, register_type, address, spec.encode(value))
