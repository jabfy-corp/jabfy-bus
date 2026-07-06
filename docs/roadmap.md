# Roadmap technique

## Phase 1 — Base solide ✅

Pipeline complet, démontrable, propre :

- [x] Modèle de message v1.0 + validation + JSON Schema
- [x] Bus pub/sub interne (dédup, historique, isolation des handlers)
- [x] MQTT Adapter (mapping déclaratif, client injectable)
- [x] HTTP Adapter (polling + webhooks)
- [x] Verification Engine minimal (risque + policies + default deny)
- [x] Execution Layer (traducteurs mqtt/http/modbus/simulation)
- [x] Audit append-only à chaînage de hash
- [x] Simulation Lab + scénario motion → light

Démo : `jabfy-bus demo --steps 10`

## Phase 2 — Domotique sérieuse

- [x] Zigbee2MQTT deep mapping (exposes, inventaire bridge)
- [ ] Home Assistant bridge
- [ ] Matter adapter expérimental
- [x] WebSocket event stream (`/bus/events`, `/verification/decisions`, `/audit/live`)
- [ ] Capability discovery automatique

## Phase 3 — Industriel / bâtiment

- [x] Modbus TCP adapter (register map sémantique)
- [ ] OPC UA read/subscribe adapter
- [ ] BACnet adapter
- [ ] KNX IP adapter
- [ ] Risk policies avancées (validation humaine pour high/critical)

## Phase 4 — IoT étendu

- [ ] LoRaWAN application adapter
- [ ] LwM2M adapter
- [ ] BLE adapter (présence, capteurs)
- [ ] Device lifecycle management
