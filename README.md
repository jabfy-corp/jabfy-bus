# JABFY Universal JSON Bus

Couche de normalisation d'événements IoT multi-protocoles pour le
projet JABFY : chaque protocole (MQTT, Zigbee, Modbus, HTTP…) est
traduit vers un langage JSON commun, chaque action est vérifiée avant
exécution, chaque décision est traçable.

## Statut

🚧 Travaux en cours. L'audit des protocoles est disponible dans
[`audit_protocoles_iot_jabfy_universal_json_bus.md`](audit_protocoles_iot_jabfy_universal_json_bus.md).

## Architecture cible

```text
Data Ingestion Layer
        ↓
Protocol Adapters
        ↓
Universal JSON Bus
        ↓
Reasoning Engine
        ↓
Verification Engine
        ↓
Execution Layer
        ↓
Audit Logs
```
