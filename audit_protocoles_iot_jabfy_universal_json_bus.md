# Audit des protocoles IoT pour l’Universal JSON Bus JABFY

## Contexte

Ce document sert de base d’audit technique pour la conception de l’**Universal JSON Bus** du projet **JABFY**.

L’objectif de JABFY n’est pas simplement de “supporter tous les protocoles IoT”, mais de construire une couche capable de **normaliser des événements, états, commandes et capacités** provenant de protocoles hétérogènes.

Dans l’architecture JABFY, le bus JSON universel se situe entre les couches d’ingestion/adapters et les couches de raisonnement, vérification et exécution.

Architecture cible simplifiée :

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

Le scope court terme est centré sur :

- l’environnement **Smart Home / IoT** ;
- la normalisation fiable des données ;
- un **Verification Engine** safety-first ;
- une exécution locale à faible latence ;
- un lab de simulation permettant de tester des scénarios sans matériel réel.

---

# 1. Synthèse rapide

## 1.1 Ce que doit faire l’Universal JSON Bus

Le bus doit absorber des entrées provenant de sources très différentes :

```text
MQTT topic
Zigbee cluster
Matter attribute
Modbus register
OPC UA node
BACnet object
LoRaWAN payload
HTTP webhook
```

et les transformer en objets JSON normalisés.

Exemple :

```json
{
  "bus_version": "1.0",
  "event_type": "telemetry.state_changed",
  "source": {
    "adapter": "zigbee2mqtt",
    "protocol": "zigbee",
    "device_id": "living_room_temp_01"
  },
  "entity": {
    "domain": "sensor",
    "class": "temperature",
    "name": "Living Room Temperature"
  },
  "value": {
    "raw": 21.7,
    "normalized": 21.7,
    "unit": "°C"
  },
  "capabilities": ["read"],
  "security": {
    "trust_level": "local_gateway",
    "verified": true
  },
  "timestamp": "2026-06-25T10:00:00+02:00"
}
```

Point critique : **la normalisation ne doit jamais supprimer l’information brute d’origine**.

Il faut toujours garder :

- le protocole source ;
- l’adresse brute ;
- le topic MQTT ;
- le registre Modbus ;
- le cluster Zigbee ;
- le node id OPC UA ;
- le payload original ;
- les métadonnées radio ou réseau si utiles.

Sinon, le debug devient un rituel païen à base de logs incomplets, ce qui est très humain, donc probablement évitable.

---

# 2. Classification des protocoles IoT

Tous les protocoles IoT ne jouent pas le même rôle. Certains transportent des données, d’autres structurent les objets, d’autres permettent de commander, découvrir ou gérer les appareils.

Il faut donc distinguer plusieurs familles.

---

## 2.1 Protocoles réseau / radio

| Protocole | Rôle | Usage typique | Intérêt pour JABFY |
|---|---|---|---|
| Wi-Fi | Réseau IP haut débit | Caméras, prises, hubs, appareils cloud/local | Important, mais souvent abstrait via HTTP/MQTT/Matter |
| Ethernet | Réseau IP filaire | Automates, serveurs, passerelles, équipements industriels | Très fiable, excellent pour lab local |
| Bluetooth LE | Radio courte portée | Capteurs, pairing, wearables, présence | Utile, mais parfois instable |
| Zigbee | Mesh basse consommation | Ampoules, capteurs, prises, domotique | Prioritaire via passerelle |
| Z-Wave | Mesh Sub-GHz domotique | Sécurité, capteurs, serrures, prises | Important mais plus niche en Europe |
| Thread | Mesh IPv6 basse consommation | Smart home moderne, Matter over Thread | Très stratégique |
| LoRaWAN | Longue portée basse consommation | Agriculture, villes, capteurs isolés | Pas prioritaire smart home, intéressant simulation |
| 6LoWPAN | IPv6 sur réseaux contraints | Base de Thread / IoT basse consommation | À connaître, rarement intégré directement |
| NB-IoT / LTE-M | IoT cellulaire | Compteurs, tracking, industrie | Hors scope immédiat sauf simulation |

---

## 2.2 Protocoles applicatifs / messagerie

| Protocole | Modèle | Usage | Priorité JABFY |
|---|---|---|---|
| MQTT | Pub/Sub via broker | Télémétrie, commandes IoT | Très haute |
| CoAP | REST léger sur UDP | Objets contraints, capteurs | Moyenne |
| HTTP REST | Requête/réponse | APIs locales, webhooks | Très haute |
| WebSocket | Temps réel bidirectionnel | Interfaces, gateways, stream local | Haute |
| Matter | Standard applicatif smart home IP | Interopérabilité domotique moderne | Très haute |
| OPC UA | Interop industrielle sémantique | Machines, automates, supervision | Haute pour futur industriel |
| Modbus | Registres industriels simples | Automates, énergie, capteurs | Haute pour simulation/industrie |
| BACnet | Bâtiment technique | HVAC, éclairage, GTB | Moyenne/haute |
| KNX | Bâtiment/domotique filaire ou RF | Installations pro bâtiment | Moyenne |
| LwM2M | Device management IoT | Provisioning, firmware, monitoring | Moyenne |
| DDS | Pub/Sub temps réel | Robotique, systèmes critiques | Basse pour smart home, haute en robotique |
| AMQP | Messaging robuste | Cloud/entreprise | Basse pour JABFY local-first |

---

# 3. Les protocoles majeurs à auditer

---

# 3.1 MQTT

## Description

MQTT est probablement le premier protocole à supporter dans JABFY.

C’est un protocole **client/serveur publish-subscribe**, léger, conçu pour les environnements contraints et très utilisé en IoT/M2M.

La version 5.0 est un standard OASIS publié en 2019.

## Fonctionnement

MQTT repose sur le modèle :

```text
Publisher -> Broker -> Subscriber
```

Exemple :

```text
zigbee2mqtt/salon/temperature -> broker -> jabfy-adapter-mqtt
```

Un appareil publie sur un **topic**, et les consommateurs s’abonnent à des topics.

## Concepts importants

| Élément | Description |
|---|---|
| Broker | Serveur central MQTT |
| Topic | Canal logique, par exemple `home/salon/temp` |
| Payload | Données envoyées, souvent JSON |
| QoS 0 | Au plus une fois |
| QoS 1 | Au moins une fois |
| QoS 2 | Exactement une fois |
| Retain | Garde la dernière valeur du topic |
| Last Will | Message publié si un client se déconnecte brutalement |

## Avantages

- Simple.
- Très utilisé.
- Fonctionne très bien avec Home Assistant, Zigbee2MQTT, ESPHome, Node-RED, n8n.
- Très adapté à un JSON Bus.
- Excellent pour simulation.
- Très bon pour centraliser des événements IoT.

## Risques

| Risque | Explication |
|---|---|
| Topics non standardisés | Chaque intégration peut inventer son propre format |
| Payloads incohérents | JSON parfois propre, parfois très spécifique au firmware |
| Sécurité oubliée | Broker sans TLS, sans ACL ou avec accès anonyme |
| Commandes dangereuses | Un simple publish peut ouvrir une porte ou couper une charge |
| Retained messages piégeux | Une vieille commande conservée peut être rejouée involontairement |

## Stratégie JABFY

MQTT doit être un **adapter prioritaire**.

Il faut prévoir des champs comme :

```json
{
  "source": {
    "protocol": "mqtt",
    "topic": "zigbee2mqtt/salon/temperature",
    "qos": 1,
    "retain": true
  },
  "payload": {
    "raw": {},
    "normalized": {}
  }
}
```

À éviter :

```json
{
  "temperature": 21.7
}
```

Ce format est trop pauvre. Il détruit le contexte source, empêche l’audit, complique la sécurité et rend le debug inutilement douloureux.

## Verdict

| Critère | Note |
|---|---:|
| Pertinence JABFY | 10/10 |
| Facilité d’intégration | 9/10 |
| Risque sécurité | Moyen à élevé |
| Priorité | P0 |

---

# 3.2 HTTP REST

## Description

HTTP REST est omniprésent. Beaucoup d’appareils IoT exposent une API locale :

```text
GET /api/devices
POST /api/light/on
```

Ce n’est pas un protocole IoT spécialisé, mais il est incontournable.

## Avantages

- Facile à tester.
- Compatible avec tous les langages.
- Très bon pour les adapters.
- Très bon pour exposer l’API interne de JABFY.
- Simple à sécuriser avec TLS, tokens, mTLS ou reverse proxy.
- Très utile pour intégrer des équipements locaux ou des gateways.

## Inconvénients

- Pas naturellement temps réel.
- Chaque API a son format.
- Beaucoup d’appareils ont une API mal documentée.
- Risque de commandes directes sans vérification.

## Stratégie JABFY

HTTP REST doit servir à deux choses :

1. adapter entrant pour devices/API locales ;
2. API interne contrôlée pour piloter JABFY.

Exemple d’entrée normalisée :

```json
{
  "event_type": "device.telemetry",
  "source": {
    "protocol": "http",
    "method": "GET",
    "endpoint": "http://192.168.1.42/api/status",
    "adapter": "shelly_http"
  },
  "entity": {
    "domain": "switch",
    "id": "shelly_plug_01"
  },
  "state": "on"
}
```

## Verdict

| Critère | Note |
|---|---:|
| Pertinence JABFY | 9/10 |
| Facilité d’intégration | 9/10 |
| Risque sécurité | Moyen |
| Priorité | P0 |

---

# 3.3 WebSocket

## Description

WebSocket permet une connexion persistante bidirectionnelle.

C’est utile pour :

- dashboards ;
- streaming d’événements ;
- gateways ;
- interfaces locales ;
- flux de simulation ;
- supervision temps réel.

## Avantages

- Temps réel.
- Plus adapté qu’un polling HTTP.
- Bon pour UI locale.
- Bon pour simulation lab.
- Bon pour observer le bus interne.

## Inconvénients

- Connexions longues à gérer.
- Authentification/session à sécuriser.
- Risque de spam événementiel.
- Gestion plus complexe des reconnexions.

## Stratégie JABFY

WebSocket est très intéressant pour exposer le flux du JSON Bus :

```text
/adapters/events
/bus/events
/verification/decisions
/simulation/events
/audit/live
```

Il ne doit pas remplacer le bus interne, mais servir de **canal de lecture temps réel** ou de communication contrôlée.

## Verdict

| Critère | Note |
|---|---:|
| Pertinence JABFY | 8/10 |
| Facilité d’intégration | 7/10 |
| Risque sécurité | Moyen |
| Priorité | P1 |

---

# 3.4 CoAP

## Description

CoAP est un protocole web léger conçu pour objets contraints.

Il ressemble conceptuellement à HTTP, mais fonctionne généralement sur UDP.

Exemple :

```text
GET coap://device.local/sensors/temp
PUT coap://device.local/light/state
```

## Avantages

- Léger.
- Très adapté aux microcontrôleurs.
- Bon modèle ressource/action.
- Compatible avec des environnements contraints.
- Moins verbeux que HTTP.

## Inconvénients

- Moins courant dans la domotique grand public que MQTT.
- Sécurité DTLS/OSCORE plus pénible à gérer.
- Debug moins simple qu’HTTP/MQTT.
- Écosystème plus niche.

## Stratégie JABFY

CoAP n’est pas prioritaire pour un prototype, mais il est intéressant pour montrer que JABFY peut gérer des objets contraints.

Mapping recommandé :

```json
{
  "source": {
    "protocol": "coap",
    "method": "GET",
    "uri": "coap://sensor-01/temp"
  },
  "entity": {
    "domain": "sensor",
    "class": "temperature"
  },
  "value": {
    "normalized": 21.4,
    "unit": "°C"
  }
}
```

## Verdict

| Critère | Note |
|---|---:|
| Pertinence JABFY | 6/10 |
| Facilité d’intégration | 5/10 |
| Risque sécurité | Moyen |
| Priorité | P2 |

---

# 4. Protocoles domotiques radio

---

# 4.1 Zigbee

## Description

Zigbee est une solution mesh basse consommation très utilisée dans la domotique.

Elle couvre notamment :

- ampoules ;
- prises connectées ;
- capteurs de température ;
- détecteurs de mouvement ;
- capteurs d’ouverture ;
- boutons ;
- relais ;
- scènes domotiques.

## Fonctionnement

Architecture courante :

```text
Device Zigbee -> Coordinateur USB -> Zigbee2MQTT / ZHA -> MQTT/API -> JABFY
```

Dans JABFY, il ne faut probablement pas parler Zigbee brut directement au début.

Il vaut mieux passer par :

- Zigbee2MQTT ;
- Home Assistant ZHA ;
- deCONZ ;
- passerelle vendor si nécessaire.

## Concepts importants

| Élément | Description |
|---|---|
| Coordinator | Clé/passerelle principale |
| Router | Appareil secteur relayant le mesh |
| End Device | Capteur batterie |
| Cluster | Groupe de fonctions, ex : OnOff, Temperature |
| Attribute | Valeur dans un cluster |
| Binding | Association entre devices |
| Interview | Découverte des capacités |

## Avantages

- Énorme écosystème.
- Parfait pour capteurs/actionneurs smart home.
- Très bon candidat pour simulation.
- Zigbee2MQTT simplifie énormément l’intégration.
- Coût matériel bas.
- Très répandu en DIY.

## Inconvénients

- Interopérabilité parfois approximative.
- Appareils exotiques avec comportements non standards.
- Dépendance au coordinateur.
- Sécurité à surveiller pendant l’appairage.
- Réseau 2.4 GHz parfois perturbé par le Wi-Fi.

## Stratégie JABFY

Ne pas faire un adapter Zigbee brut en premier.

Faire plutôt :

```text
Zigbee2MQTT -> MQTT Adapter -> JSON Bus
```

Puis garder dans le JSON :

```json
{
  "source": {
    "protocol": "zigbee",
    "bridge": "zigbee2mqtt",
    "mqtt_topic": "zigbee2mqtt/salon_motion",
    "ieee_address": "0x00158d000123abcd",
    "manufacturer": "Aqara",
    "model": "RTCGQ11LM"
  },
  "entity": {
    "domain": "binary_sensor",
    "class": "motion"
  },
  "state": "detected"
}
```

## Verdict

| Critère | Note |
|---|---:|
| Pertinence JABFY | 10/10 |
| Facilité via Zigbee2MQTT | 8/10 |
| Facilité en brut | 3/10 |
| Risque sécurité | Moyen |
| Priorité | P0 via Zigbee2MQTT |

---

# 4.2 Z-Wave

## Description

Z-Wave est une technologie RF sans fil orientée contrôle, monitoring et lecture d’état.

Elle est souvent utilisée pour :

- serrures ;
- capteurs de porte ;
- capteurs de mouvement ;
- alarmes ;
- prises ;
- modules encastrés ;
- équipements sécurité.

## Fonctionnement

Architecture classique :

```text
Device Z-Wave -> Contrôleur USB -> Z-Wave JS -> MQTT/WebSocket/API -> JABFY
```

## Avantages

- Très bon pour serrures, sécurité, capteurs.
- Fréquences Sub-GHz, souvent moins saturées que le 2.4 GHz.
- Bon historique domotique.
- Bonne intégration via Z-Wave JS.
- Meilleure portée dans certains environnements.

## Inconvénients

- Écosystème plus cher.
- Moins populaire que Zigbee en DIY Europe.
- Association/exclusion parfois pénible.
- Support dépend beaucoup du contrôleur.
- Régions/fréquences à respecter.

## Stratégie JABFY

Même logique que Zigbee : ne pas parler Z-Wave brut au début.

Passer par Z-Wave JS.

Mapping :

```json
{
  "source": {
    "protocol": "zwave",
    "bridge": "zwave-js",
    "node_id": 12,
    "command_class": "Binary Sensor"
  },
  "entity": {
    "domain": "binary_sensor",
    "class": "door"
  },
  "state": "open"
}
```

## Verdict

| Critère | Note |
|---|---:|
| Pertinence JABFY | 7/10 |
| Facilité via gateway | 7/10 |
| Risque sécurité | Moyen |
| Priorité | P2 |

---

# 4.3 Thread

## Description

Thread est un protocole mesh IPv6 basse consommation.

Il est important car il sert souvent de couche réseau à **Matter over Thread**.

En simplifié :

```text
Thread = réseau IP basse consommation
Matter = langage applicatif smart home
```

## Avantages

- IP natif.
- Mesh basse consommation.
- Pas besoin de bridge applicatif propriétaire au même niveau que Zigbee.
- Très aligné avec Matter.
- Très bon pour futur smart home propre.
- Sécurité intégrée au design.

## Inconvénients

- Besoin d’un Thread Border Router.
- Écosystème encore en consolidation.
- Débogage réseau plus complexe.
- Pas “magiquement universel”.
- Intégration souvent indirecte via Matter.

## Stratégie JABFY

Ne pas intégrer Thread seul en priorité.

Il vaut mieux intégrer **Matter**, puis traiter Thread comme une couche de transport.

Dans le JSON Bus, garder :

```json
{
  "source": {
    "protocol": "matter",
    "transport": "thread",
    "fabric_id": "home-main",
    "node_id": "0x1234"
  }
}
```

## Verdict

| Critère | Note |
|---|---:|
| Pertinence JABFY | 9/10 |
| Facilité actuelle | 5/10 |
| Risque sécurité | Moyen |
| Priorité | P1 via Matter |

---

# 4.4 Bluetooth LE / Bluetooth Mesh

## Description

Bluetooth LE est très utilisé pour :

- pairing ;
- capteurs proches ;
- wearables ;
- détection de présence ;
- beacons ;
- onboarding d’appareils.

Bluetooth Mesh ajoute une logique de réseau mesh au-dessus de BLE.

## Avantages

- Présent partout.
- Bon pour présence/proximité.
- Utile pour onboarding.
- Beaucoup de capteurs BLE abordables.
- Peut être utile pour des scénarios locaux.

## Inconvénients

- Portée limitée.
- Stabilité variable.
- Scan BLE consommateur CPU/énergie.
- Identifiants MAC randomisés selon appareils.
- Mesh moins naturel à intégrer que Zigbee/Thread.

## Stratégie JABFY

À intégrer plus tard via :

```text
ble_adapter -> JSON Bus
```

Cas utiles :

- détection présence smartphone ;
- capteur BLE température ;
- beacon ;
- mesure proximité ;
- onboarding local.

## Verdict

| Critère | Note |
|---|---:|
| Pertinence JABFY | 6/10 |
| Facilité | 5/10 |
| Risque sécurité | Moyen |
| Priorité | P2/P3 |

---

# 5. Matter : le gros morceau moderne

## 5.1 Description

Matter est un protocole de connectivité **IP-based** porté par la Connectivity Standards Alliance.

Il vise à permettre l’interopérabilité entre équipements smart home et écosystèmes différents.

Matter peut fonctionner notamment sur :

```text
Matter over Wi-Fi
Matter over Thread
Matter over Ethernet
```

Matter définit des concepts comme :

- nodes ;
- endpoints ;
- clusters ;
- attributes ;
- commands ;
- events ;
- fabrics ;
- commissioning ;
- multi-admin.

## Pourquoi Matter est important pour JABFY

Matter est proche de ce que JABFY veut faire, mais au niveau smart home standardisé.

Il apporte :

- modèle d’appareil ;
- commandes ;
- attributs ;
- événements ;
- sécurité ;
- commissioning ;
- multi-admin ;
- interopérabilité entre écosystèmes.

Mais JABFY n’est pas un clone de Matter.

JABFY doit être au-dessus :

```text
Matter / Zigbee / MQTT / Modbus / OPC UA
        ↓
Protocol Adapters
        ↓
Universal JSON Bus
        ↓
Verification Engine
        ↓
Execution Layer
```

## Avantages

| Avantage | Pourquoi c’est important |
|---|---|
| Standard moderne | Moins de bricolage par fabricant |
| Local-first possible | Aligné avec JABFY |
| IP-based | Plus propre que certains bridges historiques |
| Sécurité native | Bon socle |
| Multi-écosystème | Peut parler à plusieurs plateformes |

## Limites

| Limite | Impact |
|---|---|
| Support encore variable | Tous les devices ne supportent pas tout |
| Debug plus complexe | Certificats, fabrics, commissioning |
| Écosystème jeune | Changements fréquents |
| Certaines catégories manquent ou évoluent | Attention au scope |

## Stratégie JABFY

JABFY doit avoir un **Matter Adapter** en P1, mais probablement pas en premier si l’objectif est de produire vite une démonstration stable.

Chemin pragmatique :

1. P0 : MQTT + HTTP + Zigbee2MQTT.
2. P1 : Matter via librairie existante.
3. P2 : Thread diagnostics / BLE onboarding.

Mapping Matter vers JSON Bus :

```json
{
  "source": {
    "protocol": "matter",
    "transport": "thread",
    "fabric_id": "jabfy-home",
    "node_id": "0x0000000000001234",
    "endpoint_id": 1,
    "cluster": "OnOff",
    "attribute": "OnOff"
  },
  "entity": {
    "domain": "light",
    "class": "switchable",
    "name": "Kitchen Light"
  },
  "state": {
    "value": true,
    "semantic": "on"
  },
  "capabilities": ["read", "write", "command.on", "command.off"]
}
```

## Verdict

| Critère | Note |
|---|---:|
| Pertinence JABFY | 10/10 |
| Facilité court terme | 5/10 |
| Valeur long terme | 10/10 |
| Risque sécurité | Moyen |
| Priorité | P1 |

---

# 6. Protocoles longue portée / capteurs distribués

---

# 6.1 LoRaWAN

## Description

LoRaWAN est un protocole LPWAN longue portée basse consommation.

Architecture typique :

```text
End Device -> Gateway LoRaWAN -> Network Server -> Application Server -> JABFY
```

## Classes LoRaWAN

| Classe | Usage |
|---|---|
| Class A | Plus basse consommation, downlink après uplink |
| Class B | Fenêtres de réception planifiées |
| Class C | Réception quasi continue, plus énergivore |

## Avantages

- Très longue portée.
- Très basse consommation.
- Bon pour agriculture, compteurs, capteurs isolés.
- Très intéressant pour simulation smart city ou site industriel.
- Bonne séparation entre réseau et couche applicative.

## Inconvénients

- Très faible débit.
- Pas fait pour les commandes temps réel.
- Downlink limité.
- Payload souvent binaire compact.
- Dépend d’un Network Server.

## Stratégie JABFY

Pas prioritaire pour maison, mais très utile pour montrer que le JSON Bus peut absorber des payloads contraints.

Exemple :

```json
{
  "source": {
    "protocol": "lorawan",
    "dev_eui": "70B3D57ED005BEEF",
    "gateway_id": "gw-bbr-01",
    "fport": 2
  },
  "radio": {
    "rssi": -112,
    "snr": 5.2,
    "spreading_factor": 9
  },
  "entity": {
    "domain": "sensor",
    "class": "soil_moisture"
  },
  "value": {
    "normalized": 37.2,
    "unit": "%"
  }
}
```

## Verdict

| Critère | Note |
|---|---:|
| Pertinence smart home | 3/10 |
| Pertinence IoT général | 8/10 |
| Facilité | 5/10 |
| Priorité | P3 |

---

# 7. Protocoles industriels et bâtiment

---

# 7.1 Modbus

## Description

Modbus est un protocole industriel ancien, simple et très répandu.

Il existe principalement en :

- Modbus RTU sur série RS-485 ;
- Modbus TCP sur Ethernet/IP ;
- Modbus Security avec TLS.

## Fonctionnement

Modbus manipule des registres.

| Type | Exemple |
|---|---|
| Coil | Booléen lecture/écriture |
| Discrete Input | Booléen lecture seule |
| Input Register | Entier lecture seule |
| Holding Register | Entier lecture/écriture |

Exemple :

```text
Unit ID 1
Holding Register 40001 = température x10
```

## Avantages

- Ultra courant.
- Simple à simuler.
- Très utile pour énergie, automates, HVAC, compteurs.
- Facile à intégrer en Python.
- Bon candidat pour un lab industriel.

## Inconvénients

- Peu sémantique.
- Sécurité souvent inexistante en Modbus TCP classique.
- Risque élevé si écriture autorisée.
- Le sens des registres dépend de la documentation constructeur.
- Une même valeur peut représenter n’importe quoi sans mapping externe.

## Stratégie JABFY

Modbus est excellent pour le **Simulation Lab** et une future orientation industrielle.

Mais le JSON Bus doit enrichir les registres avec une couche sémantique.

Mauvais :

```json
{
  "register": 40001,
  "value": 217
}
```

Bon :

```json
{
  "source": {
    "protocol": "modbus_tcp",
    "host": "192.168.10.20",
    "unit_id": 1,
    "register_type": "holding_register",
    "address": 40001
  },
  "entity": {
    "domain": "sensor",
    "class": "temperature",
    "asset": "boiler_01"
  },
  "value": {
    "raw": 217,
    "normalized": 21.7,
    "unit": "°C",
    "scale": 0.1
  },
  "capabilities": ["read"],
  "safety": {
    "write_allowed": false
  }
}
```

## Verdict

| Critère | Note |
|---|---:|
| Pertinence JABFY smart home | 5/10 |
| Pertinence industriel | 10/10 |
| Facilité | 8/10 |
| Risque sécurité | Élevé |
| Priorité | P1 pour lab industriel |

---

# 7.2 OPC UA

## Description

OPC UA est un standard industriel moderne d’interopérabilité.

Il peut représenter :

- des données ;
- des hiérarchies ;
- des objets ;
- des méthodes ;
- des événements ;
- des abonnements ;
- des modèles d’information.

## Pourquoi c’est important

OPC UA est beaucoup plus riche que Modbus.

Modbus dit :

```text
registre 40001 = 217
```

OPC UA peut dire :

```text
Machine > Boiler > TemperatureSensor > CurrentValue = 21.7 °C
```

Avec métadonnées, type, hiérarchie, méthode, événement et parfois historique.

## Avantages

- Très sémantique.
- Sécurité native.
- Très bon pour industrie 4.0.
- Subscriptions et events.
- Information model puissant.
- Meilleur contexte que Modbus.

## Inconvénients

- Complexe.
- Mauvaise configuration sécurité fréquente.
- Plus lourd à intégrer.
- Les modèles varient selon constructeurs.
- Peut être surdimensionné pour un prototype smart home.

## Stratégie JABFY

OPC UA est presque un “JSON Bus industriel” à lui seul.

Le bus JABFY doit donc respecter sa richesse au lieu de l’écraser.

Mapping :

```json
{
  "source": {
    "protocol": "opcua",
    "endpoint": "opc.tcp://192.168.10.50:4840",
    "node_id": "ns=2;s=Boiler1.Temperature",
    "browse_path": "/Factory/Line1/Boiler1/Temperature"
  },
  "entity": {
    "domain": "sensor",
    "class": "temperature",
    "asset": "boiler_1"
  },
  "value": {
    "normalized": 81.2,
    "unit": "°C"
  },
  "quality": {
    "source_quality": "good"
  },
  "capabilities": ["read", "subscribe"]
}
```

## Verdict

| Critère | Note |
|---|---:|
| Pertinence smart home | 2/10 |
| Pertinence industriel | 10/10 |
| Facilité | 5/10 |
| Risque sécurité | Moyen à élevé si mal configuré |
| Priorité | P2 ou P1 si démonstration industrielle |

---

# 7.3 BACnet

## Description

BACnet est un standard de communication pour les réseaux d’automatisation et de contrôle des bâtiments.

Il est utilisé pour :

- HVAC ;
- éclairage ;
- contrôle d’accès ;
- ascenseurs ;
- sécurité ;
- détection incendie ;
- GTB/GTC.

## Avantages

- Très utilisé bâtiment tertiaire.
- Modèle objet plus riche que Modbus.
- Interopérabilité vendor-independent.
- Très pertinent pour énergie/bâtiment.
- Bon candidat pour supervision locale.

## Inconvénients

- Découverte réseau parfois bavarde.
- Sécurité historique souvent faible si BACnet/IP exposé.
- Intégration moins triviale que MQTT/HTTP.
- Beaucoup de variabilité terrain.
- Documentation des objets parfois incomplète.

## Stratégie JABFY

BACnet est pertinent pour futur B2B bâtiment/énergie.

Mapping :

```json
{
  "source": {
    "protocol": "bacnet",
    "device_instance": 12345,
    "object_type": "analogInput",
    "object_instance": 2,
    "property": "presentValue"
  },
  "entity": {
    "domain": "sensor",
    "class": "temperature",
    "asset": "ahu_01"
  },
  "value": {
    "normalized": 19.8,
    "unit": "°C"
  }
}
```

## Verdict

| Critère | Note |
|---|---:|
| Pertinence smart home | 3/10 |
| Pertinence bâtiment | 9/10 |
| Facilité | 5/10 |
| Risque sécurité | Moyen/élevé |
| Priorité | P2 |

---

# 7.4 KNX

## Description

KNX est un standard ouvert pour maison et bâtiment, très présent dans les installations professionnelles.

Il est souvent utilisé pour :

- éclairage ;
- stores ;
- chauffage ;
- ventilation ;
- scénarios bâtiment ;
- capteurs muraux ;
- actionneurs tableau électrique.

## Avantages

- Très robuste.
- Très utilisé en bâtiment pro.
- Stable dans le temps.
- Bon candidat pour supervision locale.
- Écosystème professionnel mature.

## Inconvénients

- Matériel coûteux.
- Besoin ETS/configuration.
- Bus parfois complexe à comprendre.
- Sémantique dépend de la bonne documentation projet.
- Pas forcément adapté à un prototype rapide.

## Stratégie JABFY

KNX doit être intégré via gateway IP ou librairie existante.

Mapping :

```json
{
  "source": {
    "protocol": "knx",
    "group_address": "1/2/15",
    "dpt": "9.001"
  },
  "entity": {
    "domain": "sensor",
    "class": "temperature",
    "location": "meeting_room"
  },
  "value": {
    "normalized": 22.1,
    "unit": "°C"
  }
}
```

## Verdict

| Critère | Note |
|---|---:|
| Pertinence smart home DIY | 4/10 |
| Pertinence bâtiment pro | 9/10 |
| Facilité | 5/10 |
| Priorité | P2/P3 |

---

# 8. Protocoles de gestion IoT

---

# 8.1 LwM2M

## Description

OMA Lightweight M2M est un protocole orienté gestion d’objets IoT.

Il sert notamment à :

- provisionner ;
- configurer ;
- mettre à jour ;
- superviser ;
- diagnostiquer ;
- gérer un parc d’appareils.

## Avantages

- Très bon pour lifecycle management.
- Plus structuré que MQTT brut.
- Adapté aux appareils contraints.
- Bon modèle d’objets.
- Intéressant pour des flottes IoT.

## Inconvénients

- Moins présent en domotique classique.
- Plus orienté IoT opérateur/industrie.
- Plus complexe que MQTT.
- Pas nécessaire pour le prototype smart home.

## Stratégie JABFY

Pas prioritaire en smart home, mais intéressant si JABFY devient une couche de gestion de parc IoT.

Mapping :

```json
{
  "source": {
    "protocol": "lwm2m",
    "endpoint_name": "sensor-node-42",
    "object_id": 3303,
    "instance_id": 0,
    "resource_id": 5700
  },
  "entity": {
    "domain": "sensor",
    "class": "temperature"
  },
  "value": {
    "normalized": 23.4,
    "unit": "°C"
  }
}
```

## Verdict

| Critère | Note |
|---|---:|
| Pertinence smart home | 3/10 |
| Pertinence parc IoT | 8/10 |
| Facilité | 5/10 |
| Priorité | P3 |

---

# 8.2 DDS

## Description

DDS est un standard publish-subscribe temps réel, utilisé dans des contextes plus critiques ou industriels.

Il est surtout présent dans :

- robotique ;
- ROS 2 ;
- défense ;
- aéronautique ;
- véhicules autonomes ;
- systèmes critiques.

## Avantages

- Très puissant.
- Très bon temps réel.
- QoS riche.
- Excellent pour systèmes distribués critiques.
- Adapté aux systèmes complexes.

## Inconvénients

- Trop lourd pour le scope smart home initial.
- Complexité élevée.
- Pas nécessaire pour le premier prototype.
- Courbe d’apprentissage plus importante.

## Stratégie JABFY

À garder dans la cartographie long terme.

Pas en P0.

## Verdict

| Critère | Note |
|---|---:|
| Pertinence smart home | 1/10 |
| Pertinence robotique/simulation | 8/10 |
| Facilité | 3/10 |
| Priorité | P4 |

---

# 9. Matrice globale de priorité pour JABFY

---

## 9.1 P0 — à faire en premier

| Protocole / intégration | Pourquoi |
|---|---|
| MQTT | Base universelle simple, compatible Zigbee2MQTT, simulation, Home Assistant |
| HTTP REST | APIs locales, adapters simples, webhooks |
| WebSocket interne | Flux temps réel du bus |
| Zigbee via Zigbee2MQTT | Énorme valeur smart home, rapide à intégrer |
| Home Assistant bridge | Pas un protocole, mais excellent agrégateur initial |

---

## 9.2 P1 — après la base

| Protocole | Pourquoi |
|---|---|
| Matter | Standard smart home moderne, long terme |
| Modbus TCP | Simulation industrielle, énergie, supervision |
| OPC UA minimal read/subscribe | Excellent pour vision industrielle |
| Thread via Matter | Pas directement, mais transport important |

---

## 9.3 P2 — utile mais pas vital au départ

| Protocole | Pourquoi |
|---|---|
| Z-Wave via Z-Wave JS | Bon smart home, plus niche |
| BACnet | Bâtiment / GTB |
| KNX | Bâtiment pro |
| CoAP | IoT contraint propre |
| BLE sensors | Présence/capteurs |

---

## 9.4 P3/P4 — long terme

| Protocole | Pourquoi |
|---|---|
| LoRaWAN | IoT longue portée |
| LwM2M | Gestion parc IoT |
| DDS | Robotique/systèmes critiques |
| AMQP | Messaging entreprise |
| NB-IoT/LTE-M | IoT opérateur/cellulaire |

---

# 10. Proposition d’architecture Universal JSON Bus

---

## 10.1 Principe

Le bus ne doit pas avoir un seul type de message.

Il doit distinguer :

| Type | Description |
|---|---|
| `telemetry` | Mesure brute ou normalisée |
| `state` | État actuel d’une entité |
| `event` | Événement ponctuel |
| `command.requested` | Commande proposée |
| `command.approved` | Commande validée |
| `command.rejected` | Commande bloquée |
| `command.executed` | Commande exécutée |
| `capability.report` | Description de ce que sait faire un device |
| `health` | État d’un adapter/device |
| `audit` | Trace sécurité/action |
| `simulation` | Événement issu du lab |

---

## 10.2 Schéma commun minimal

```json
{
  "bus_version": "1.0",
  "message_id": "uuid",
  "correlation_id": "uuid-or-null",
  "timestamp": "2026-06-25T10:00:00+02:00",

  "message_type": "state.changed",

  "source": {
    "adapter": "mqtt_adapter",
    "protocol": "mqtt",
    "bridge": "zigbee2mqtt",
    "raw_address": "zigbee2mqtt/salon/temp",
    "device_id": "salon_temp_01"
  },

  "entity": {
    "id": "sensor.salon_temperature",
    "domain": "sensor",
    "class": "temperature",
    "location": "salon",
    "asset": null
  },

  "value": {
    "raw": 217,
    "normalized": 21.7,
    "unit": "°C",
    "datatype": "float"
  },

  "capabilities": ["read", "subscribe"],

  "quality": {
    "confidence": 1.0,
    "source_quality": "good",
    "stale": false
  },

  "security": {
    "trust_level": "local_gateway",
    "auth_context": "adapter_service_account",
    "verified": true,
    "write_allowed": false
  },

  "raw": {
    "topic": "zigbee2mqtt/salon/temp",
    "payload": {
      "temperature": 21.7,
      "battery": 87
    }
  }
}
```

---

## 10.3 Champs indispensables

| Champ | Pourquoi |
|---|---|
| `message_id` | Audit, déduplication |
| `correlation_id` | Relier décision IA, validation, exécution |
| `source.protocol` | Savoir d’où vient l’info |
| `source.raw_address` | Debug et traçabilité |
| `entity.domain` | Normalisation logique |
| `entity.class` | Sens réel de la donnée |
| `value.raw` | Ne jamais perdre l’origine |
| `value.normalized` | Exploitable par IA/règles |
| `security.trust_level` | Décider si l’action est risquée |
| `capabilities` | Savoir lire/écrire/commander |
| `raw` | Sauvegarde forensic |

---

# 11. Modèle de normalisation conseillé

---

## 11.1 Domaines d’entités

```text
sensor
binary_sensor
switch
light
cover
lock
climate
fan
valve
meter
alarm
camera
button
scene
automation
gateway
controller
machine
actuator
```

---

## 11.2 Classes sémantiques

```text
temperature
humidity
pressure
power
energy
voltage
current
motion
presence
door
window
smoke
co2
co
water_leak
illuminance
battery
signal_strength
position
speed
flow
level
setpoint
mode
fault
```

---

## 11.3 Actions normalisées

```text
turn_on
turn_off
toggle
set_value
set_brightness
set_color
set_temperature
open
close
stop
lock
unlock
arm
disarm
reset
acknowledge
start
stop_process
```

---

## 11.4 Exemple : mapping multi-protocoles

Même action logique : allumer une lumière.

| Protocole | Commande native | Commande JABFY |
|---|---|---|
| MQTT | publish `zigbee2mqtt/light/set {"state":"ON"}` | `command.turn_on` |
| Matter | OnOff cluster command `On` | `command.turn_on` |
| Zigbee | Cluster OnOff command | `command.turn_on` |
| HTTP | `POST /relay/0?turn=on` | `command.turn_on` |
| KNX | group write `1/1/4 = 1` | `command.turn_on` |
| Modbus | write coil `00001 = true` | `command.turn_on` |

Le Verification Engine doit valider la commande **normalisée**, puis l’Execution Layer traduit vers le protocole cible.

---

# 12. Sécurité : règles d’or pour le bus

---

## 12.1 Séparer lecture et écriture

Un adapter peut être :

```json
{
  "mode": "read_only"
}
```

ou :

```json
{
  "mode": "read_write"
}
```

Par défaut : **read-only**.

L’écriture doit être explicitement autorisée.

---

## 12.2 Toute commande doit passer par le Verification Engine

Pipeline obligatoire :

```text
Command Proposal
      ↓
Verification Engine
      ↓
Policy Decision
      ↓
Execution Layer
      ↓
Audit Log
```

À interdire absolument :

```text
AI -> MQTT publish
```

L’IA ne doit jamais publier directement une commande sur un protocole externe.

---

## 12.3 Niveaux de risque

| Niveau | Exemple | Validation |
|---|---|---|
| Low | Lire température | Auto |
| Medium | Allumer lumière | Règles simples |
| High | Ouvrir porte, désactiver alarme | Validation humaine ou règle forte |
| Critical | Action industrielle, chauffage fort, coupure énergie | Validation stricte + contexte + journalisation |

---

## 12.4 Données à auditer

Chaque action doit produire :

```json
{
  "audit_type": "command.execution",
  "actor": {
    "type": "ai_agent",
    "id": "local_llm"
  },
  "decision": {
    "status": "approved",
    "policy": "home_light_low_risk_v1"
  },
  "command": {
    "normalized": "turn_on",
    "target": "light.kitchen"
  },
  "execution": {
    "adapter": "mqtt_adapter",
    "protocol": "mqtt",
    "success": true
  },
  "timestamp": "2026-06-25T10:00:00+02:00"
}
```

---

# 13. Recommandation de roadmap technique

---

## 13.1 Phase 1 — Base solide

Objectif : faire un pipeline complet, démontrable, propre.

À implémenter :

```text
MQTT Adapter
HTTP Adapter
Internal JSON Bus
Verification Engine minimal
Execution Layer MQTT/HTTP
Audit Logs
Simulation Lab basique
```

Scénario de démo :

```text
Capteur mouvement salon détecte présence
↓
MQTT Adapter normalise
↓
Reasoning propose allumer lampe
↓
Verification Engine valide car faible risque + heure autorisée
↓
Execution Layer publie commande MQTT
↓
Audit log append-only
```

---

## 13.2 Phase 2 — Domotique sérieuse

Ajouter :

```text
Zigbee2MQTT deep mapping
Home Assistant bridge
Matter adapter expérimental
WebSocket event stream
Capability discovery
```

---

## 13.3 Phase 3 — Industriel / bâtiment

Ajouter :

```text
Modbus TCP adapter
OPC UA read/subscribe adapter
BACnet adapter
KNX IP adapter
Risk policies avancées
```

---

## 13.4 Phase 4 — IoT étendu

Ajouter :

```text
LoRaWAN application adapter
LwM2M adapter
BLE adapter
Device lifecycle management
```

---

# 14. Classement final par intérêt pour l’Universal JSON Bus

| Rang | Protocole | Pourquoi |
|---:|---|---|
| 1 | MQTT | Le plus simple, le plus utile, parfait pour bus/event |
| 2 | HTTP REST | APIs locales, adapters faciles |
| 3 | Zigbee via Zigbee2MQTT | Smart home concret, rapide |
| 4 | Matter | Futur smart home standardisé |
| 5 | WebSocket | Flux temps réel interne |
| 6 | Modbus TCP | Excellent pour lab industriel |
| 7 | OPC UA | Sémantique industrielle puissante |
| 8 | Thread | Important via Matter |
| 9 | Z-Wave | Bon mais moins prioritaire |
| 10 | BACnet | Très utile bâtiment |
| 11 | KNX | Très utile bâtiment pro |
| 12 | CoAP | Propre mais moins courant |
| 13 | BLE | Présence/onboarding |
| 14 | LoRaWAN | Longue portée, pas smart home |
| 15 | LwM2M | Gestion parc IoT |
| 16 | DDS | Puissant mais hors scope initial |

---

# 15. Conclusion

Pour JABFY, la bonne stratégie n’est pas de créer “un bus compatible avec tout” dès le départ.

La bonne stratégie est :

1. définir un modèle JSON interne très propre ;
2. créer des adapters isolés par protocole ;
3. normaliser sans perdre les données brutes ;
4. mettre le Verification Engine entre toute décision et toute action ;
5. commencer par MQTT, HTTP, Zigbee2MQTT et simulation ;
6. ajouter Matter ensuite, car c’est stratégique mais plus lourd ;
7. garder Modbus/OPC UA pour démontrer la crédibilité industrielle.

Stack de départ recommandée :

```text
MQTT + HTTP + Zigbee2MQTT + WebSocket interne
↓
Universal JSON Bus
↓
Verification Engine
↓
Execution Layer
↓
Audit append-only
```

Règle architecturale à respecter :

```text
Aucun protocole externe ne doit dicter le modèle interne de JABFY.
Chaque protocole est traduit vers un langage commun.
Chaque action est vérifiée avant exécution.
Chaque décision est traçable.
```

---

# 16. Sources utiles

Sources principales consultées ou pertinentes pour approfondissement :

- README JABFY fourni dans le contexte projet.
- OASIS MQTT Version 5.0 : https://www.oasis-open.org/standard/mqtt-v5-0-os/
- IETF RFC 7252 — The Constrained Application Protocol : https://datatracker.ietf.org/doc/html/rfc7252
- W3C Web of Things Architecture : https://www.w3.org/TR/wot-architecture11/
- Connectivity Standards Alliance — Matter : https://csa-iot.org/all-solutions/matter/
- Connectivity Standards Alliance — Zigbee : https://csa-iot.org/all-solutions/zigbee/
- Thread Group : https://threadgroup.org/
- OpenThread Primer : https://openthread.io/guides/thread-primer
- Z-Wave Alliance : https://z-wavealliance.org/
- LoRa Alliance — LoRaWAN : https://lora-alliance.org/
- Modbus Specifications : https://www.modbus.org/modbus-specifications
- OPC Foundation — OPC UA : https://opcfoundation.org/about/opc-technologies/opc-ua/
- BACnet : https://bacnet.org/about-bacnet-standard/
- KNX : https://knx.org/
- OMA Lightweight M2M : https://www.openmobilealliance.org/specifications/lwm2m/
- OMG DDS Portal : https://www.omg.org/omg-dds-portal/

---

# 17. Note de transmission

Ce document est conçu comme une base de travail technique pour la personne chargée de réfléchir à l’architecture de l’Universal JSON Bus.

Il faut surtout en retenir trois idées :

1. **les protocoles doivent être des entrées vers le bus, jamais le modèle interne du bus ;**
2. **le bus doit garder les données brutes et produire une version normalisée ;**
3. **toute action doit passer par le Verification Engine avant exécution.**
