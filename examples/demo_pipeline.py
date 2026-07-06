#!/usr/bin/env python3
"""Démo du pipeline complet JABFY, sans matériel réel.

    Capteur mouvement salon détecte présence
    ↓
    Adapter simulation normalise
    ↓
    Reasoning (stub) propose d'allumer la lampe
    ↓
    Verification Engine valide (risque moyen + policy)
    ↓
    Execution Layer actionne le switch simulé
    ↓
    Audit log append-only

Lancer :  python examples/demo_pipeline.py
"""

from __future__ import annotations

import json

from jabfy_bus.logging_utils import setup_logging
from jabfy_bus.simulation.scenarios import build_demo_stack


def main() -> None:
    setup_logging("INFO")
    stack = build_demo_stack()

    print("=== JABFY Universal JSON Bus — démo motion -> light ===\n")

    print("[ticks 0-2] rien ne bouge…")
    stack.lab.run(3)
    print(f"  lampe : {'ON' if stack.lamp.state else 'OFF'}")

    print("\n[tick 3] mouvement forcé dans le salon")
    stack.motion.force(True)
    stack.lab.tick()
    print(f"  lampe : {'ON' if stack.lamp.state else 'OFF'}")

    print("\n[ticks 4-9] la vie continue…")
    stack.lab.run(6)

    print("\n--- Pipeline ---")
    for msg in stack.bus.history("command.*"):
        decision = msg.raw.get("decision", {})
        extra = f" policy={decision.get('policy')}" if decision else ""
        extra += f" success={msg.raw.get('success')}" if "success" in msg.raw else ""
        print(f"  {msg.message_type:<20} correlation={str(msg.correlation_id)[:8]}…{extra}")

    print("\n--- Entités observées ---")
    for record in stack.registry.list():
        print(f"  {record.entity_id:<35} = {record.last_value}")

    print("\n--- Audit ---")
    print(f"  enregistrements : {len(stack.audit)}")
    print(f"  chaîne intègre  : {stack.audit.verify()}")
    last = stack.audit.records()[-1]
    print("  dernier enregistrement :")
    print("  " + json.dumps(last.body, indent=2, ensure_ascii=False).replace("\n", "\n  "))


if __name__ == "__main__":
    main()
