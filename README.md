# JABFY Universal JSON Bus

Couche de normalisation d'événements IoT multi-protocoles : chaque
protocole (MQTT, Zigbee, Modbus, HTTP…) est traduit vers un langage
JSON commun, **chaque action est vérifiée avant exécution**, chaque
décision est traçable dans un audit append-only.

```text
Data Ingestion Layer
        ↓
Protocol Adapters        MQTT · HTTP · Zigbee2MQTT · Modbus TCP · CoAP
        ↓
Universal JSON Bus       messages normalisés v1.0, pub/sub interne
        ↓
Reasoning Engine         propose des command.requested (jamais d'exécution directe)
        ↓
Verification Engine      risque + policies, default deny
        ↓
Execution Layer          traducteurs par protocole, transports injectables
        ↓
Audit Logs               append-only, chaînage SHA-256
```

## Principes

1. **Aucun protocole externe ne dicte le modèle interne.**
2. **La normalisation ne supprime jamais la donnée brute** (`value.raw`,
   `source.raw_address`, payload complet dans `raw`).
3. **Toute commande passe par le Verification Engine** — l'Execution
   Layer rejette tout contournement (`VerificationBypass`).
4. **Read-only par défaut** : l'écriture est un opt-in explicite.
5. **Tout est traçable** : `correlation_id` relie requête → décision →
   exécution, l'audit détecte la falsification.

## Démarrage rapide

```bash
# aucune dépendance requise pour le cœur (stdlib uniquement)
make test          # 81 tests unitaires
make demo          # scénario motion -> light en simulation
```

```text
$ jabfy-bus demo --steps 10
ticks           : 10
entities        : 3
decisions       : 1
executed        : 1
lamp state      : ON
audit records   : 4
audit verified  : True
```

Autres commandes :

```bash
jabfy-bus validate message.json      # valide contre le schéma bus v1.0
jabfy-bus audit-verify audit.jsonl   # vérifie la chaîne d'audit
jabfy-bus serve --config config.yaml # API HTTP + WebSocket (extra [api])
```

## Installation

```bash
pip install .            # cœur, stdlib uniquement
pip install ".[all]"     # + paho-mqtt, fastapi/uvicorn, pymodbus, pyyaml
```

## Conteneur et déploiement

Chaque push sur `main` publie une image OCI :

```text
ghcr.io/jabfy-corp/jabfy-bus:latest
ghcr.io/jabfy-corp/jabfy-bus:sha-<commit>
```

L'image lance l'API du bus sur le port `8080`. Utiliser son digest immuable pour
un déploiement et, si nécessaire, fournir une configuration montée en volume :

```bash
docker run --rm -p 8080:8080 \
  -e JABFY_BUS_HOST=0.0.0.0 \
  ghcr.io/jabfy-corp/jabfy-bus@sha256:<digest>
```

## Exemple de message normalisé

```json
{
  "bus_version": "1.0",
  "message_type": "telemetry",
  "source": {
    "adapter": "zigbee2mqtt_adapter",
    "protocol": "zigbee",
    "bridge": "zigbee2mqtt",
    "raw_address": "zigbee2mqtt/salon_temp",
    "device_id": "salon_temp"
  },
  "entity": { "id": "sensor.salon_temp_temperature", "domain": "sensor", "class": "temperature" },
  "value": { "raw": 21.7, "normalized": 21.7, "unit": "°C" },
  "capabilities": ["read"],
  "security": { "trust_level": "local_gateway" },
  "raw": { "topic": "zigbee2mqtt/salon_temp", "payload": { "temperature": 21.7, "battery": 87 } }
}
```

## Documentation

| Document | Contenu |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Architecture et flux des messages |
| [docs/message-schema.md](docs/message-schema.md) | Schéma de message v1.0 |
| [docs/security.md](docs/security.md) | Règles de sécurité, risques, policies |
| [docs/adapters.md](docs/adapters.md) | Guide des adapters existants et à venir |
| [docs/roadmap.md](docs/roadmap.md) | Phases 1 à 4 |
| [audit_protocoles_iot…md](audit_protocoles_iot_jabfy_universal_json_bus.md) | Audit complet des protocoles IoT |

## État du projet

Phase 1 (base solide) terminée : bus, adapters P0, verification,
execution, audit, simulation, API de consultation, CLI, CI.
Voir la [roadmap](docs/roadmap.md) pour les phases suivantes
(Matter, Home Assistant bridge, OPC UA, BACnet…).

## Licence

Propriétaire — © 2026 Jabfy Corp. Voir [LICENSE](LICENSE).
