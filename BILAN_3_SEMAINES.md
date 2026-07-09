# Bilan des 3 dernières semaines — JABFY Universal JSON Bus

**Période : 23 juin → 6 juillet 2026** · Réunion du 9 juillet 2026, 19h

---

## Résumé exécutif (les 30 premières secondes)

En 3 semaines, je suis parti de zéro et j'ai livré la **version 0.1.0** du bus JSON
universel Jabfy : un pipeline IoT complet et fonctionnel qui normalise plusieurs
protocoles (MQTT, Zigbee2MQTT, HTTP, Modbus TCP) vers un langage JSON commun,
**vérifie chaque commande avant exécution** et trace chaque décision dans un
**audit infalsifiable**. Le tout est testé (**81 tests unitaires**), documenté
(6 documents), intégré en CI, et **démontrable en live sans aucun matériel**
grâce à un lab de simulation.

```text
Data Ingestion → Protocol Adapters → Universal JSON Bus → Reasoning Engine
              → Verification Engine → Execution Layer → Audit Logs
```

## Chiffres clés

| Indicateur | Valeur |
|---|---|
| Commits | 51 |
| Lignes ajoutées | ~6 900 (dont ~2 270 de code Python dans le paquet) |
| Fichiers dans le dépôt | 67 |
| Tests unitaires | 81, répartis sur 9 fichiers de tests |
| Documents rédigés | 6 (architecture, schéma, sécurité, adapters, roadmap, audit protocoles) |
| Adapters livrés | 4 complets (MQTT, HTTP, Zigbee2MQTT, Modbus TCP) + 1 squelette (CoAP) |
| Dépendances du cœur | **Zéro** — stdlib Python uniquement (extras optionnels pour MQTT/API/Modbus/YAML) |
| Version | 0.1.0 — phase 1 de la roadmap terminée |

---

## Semaine 1 (23–25 juin) — Étude et fondations du bus

**Objectif : poser un socle propre avant d'écrire le moindre adapter.**

### Audit des protocoles IoT (23 juin)
- Rédaction d'un audit complet (~1 900 lignes) des protocoles du marché :
  forces, faiblesses, modèles de données, sécurité. C'est ce document qui a
  fixé les choix d'architecture (quels protocoles en priorité P0, quel modèle
  de message, quelles garanties de sécurité).
- Mise en place du projet : structure du paquet Python, `pyproject.toml`,
  licence propriétaire, README initial, **document d'architecture cible**.

### Le module `core` (24–25 juin)
- **Vocabulaire commun** : types et énumérations partagés par tout le système
  (domaines d'entités, types de messages, niveaux de confiance, capacités…).
- **Modèle de message normalisé v1.0** (`jabfy_bus/core/message.py`) : le contrat
  central du projet. Chaque événement, quelle que soit sa provenance, devient un
  message JSON avec `source`, `entity`, `value` (brut **et** normalisé), `capabilities`,
  `security.trust_level`, `correlation_id` et le payload brut conservé dans `raw`.
- **JSON Schema publié** (`schemas/bus-message-1.0.json`) : le format est validable
  par n'importe quel outil externe, pas seulement par notre code.
- **Bus pub/sub interne** : abonnements par pattern, déduplication des messages,
  historique, isolation des handlers (un handler qui plante ne casse pas les autres).
- **Registre d'entités** : inventaire vivant de tout ce qui a été vu sur le bus.
- Exceptions dédiées, premiers tests (message + bus), et **spécification détaillée
  du schéma de message** dans `docs/message-schema.md`.

**Livrable de la semaine : un cœur de bus testé, sans dépendance, avec un format
de message versionné et documenté.**

---

## Semaine 2 (27 juin – 1er juillet) — Adapters P0 et couche de sécurité

**Objectif : brancher les premiers protocoles et rendre le système sûr par construction.**

### Adapters (27–28 juin)
- **Classe de base des adapters** : contrat commun, et surtout **read-only par
  défaut** — un adapter ne peut pas écrire vers le terrain sans opt-in explicite.
- **Adapter MQTT** : mapping **déclaratif** des topics vers les entités (pas de
  code à écrire pour ajouter un device), client injectable donc testable sans broker.
  Les topics inconnus sont droppés proprement, les écritures refusées par défaut.
- **Adapter HTTP** : deux modes — polling (fetcher injectable) et **réception de
  webhooks** avec normaliseurs par route.
- Configuration du logging (texte lisible ou JSON lines pour l'exploitation).

### Couche de sécurité (30 juin – 1er juillet) — le cœur de la valeur ajoutée
- **Classification du risque des commandes** : chaque commande reçoit un niveau
  de risque (low / medium / high / critical) selon le domaine et l'action.
- **Policies déclaratives** : règles d'autorisation avec conditions, dont des
  **fenêtres horaires** (ex. « la lumière du salon peut s'allumer sur détection
  de mouvement uniquement entre 18h et 23h »).
- **Verification Engine en default deny** : au-delà du risque faible, tout ce qui
  n'est pas explicitement autorisé est **rejeté**. Chaque décision (approve/reject)
  est motivée et journalisée.
- **Journal d'audit append-only avec chaînage de hash SHA-256** : chaque
  enregistrement contient le hash du précédent. Toute falsification (modification,
  suppression, insertion) casse la chaîne et est détectée — testé explicitement.
- **Execution Layer avec anti-bypass** : les traducteurs convertissent une commande
  approuvée vers le protocole cible (MQTT, HTTP, Modbus, simulation), et la couche
  d'exécution **refuse toute commande qui n'est pas passée par la vérification**
  (exception `VerificationBypass`). Il est architecturalement impossible de
  court-circuiter la sécurité.
- Chargement de configuration JSON/YAML + exemple complet, et rédaction de
  `docs/security.md`.

**Livrable de la semaine : le pipeline `command.requested → verified → approved →
executed → audité` complet, avec la sécurité intégrée dans l'architecture, pas
ajoutée après coup.**

---

## Semaine 3 (3–6 juillet) — Zigbee, Modbus, simulation, API et finition 0.1.0

**Objectif : élargir les protocoles, rendre le tout démontrable et livrer proprement.**

### Nouveaux adapters (3 et 5–6 juillet)
- **Zigbee2MQTT** : base de connaissance des devices (exposes), un message normalisé
  par expose (un capteur multi-valeurs devient N entités propres), gestion de
  l'inventaire du bridge, inversion des capteurs de contact testée.
- **Modbus TCP** (orientation industriel/bâtiment) : **register map sémantique**
  (chaque registre a un sens métier, une unité, un facteur d'échelle) et **triple
  contrôle avant écriture** (adapter autorisé en écriture + registre marqué
  writable + commande approuvée par la vérification). Les erreurs de lecture d'un
  registre sont isolées et ne bloquent pas les autres.
- **CoAP** : squelette d'adapter posé — le contrat de normalisation est défini,
  l'implémentation complète est en phase suivante.

### Lab de simulation (3–4 juillet)
- **Devices simulés** : capteur de température, détecteur de mouvement, switch,
  compteur — avec comportements réalistes.
- **Lab à temps discret** branché directement sur le bus : on fait avancer le temps
  tick par tick et on observe tout le pipeline.
- **Scénario de démo `motion → light`** câblé de bout en bout : détection de
  mouvement → message normalisé → règle de raisonnement → `command.requested` →
  vérification (policy + fenêtre horaire) → exécution → lampe allumée → audit vérifié.

### API, CLI et finition (4–6 juillet)
- **API HTTP de consultation** (lecture seule, volontairement) : état des entités,
  historique, décisions.
- **Flux WebSocket temps réel** : `/bus/events`, `/verification/decisions`, `/audit/live`.
- **CLI `jabfy-bus`** : `demo` (scénario en simulation), `validate` (valider un
  message contre le schéma), `audit-verify` (vérifier l'intégrité d'un journal
  d'audit), `serve` (lancer l'API).
- **Makefile + CI GitHub Actions** (les 81 tests tournent à chaque push).
- Documentation finale : guide des adapters, **roadmap en 4 phases**, README complet.
- **Tag 0.1.0 — phase 1 terminée.**

**Livrable de la semaine : un produit démontrable, installable (`pip install .`),
documenté et sous CI.**

---

## Les 5 principes d'architecture (si on me demande « pourquoi c'est fait comme ça »)

1. **Aucun protocole externe ne dicte le modèle interne** — le bus a son propre
   langage, les adapters traduisent.
2. **La normalisation ne détruit jamais la donnée brute** — `value.raw` et le
   payload d'origine sont toujours conservés à côté de la valeur normalisée.
3. **Toute commande passe par le Verification Engine** — l'exécution rejette
   tout contournement.
4. **Read-only par défaut** — l'écriture vers le terrain est un opt-in explicite,
   à chaque niveau (adapter, registre, policy).
5. **Tout est traçable** — le `correlation_id` relie requête → décision →
   exécution, et l'audit détecte la falsification.

## Démo possible en réunion (2 minutes, zéro matériel)

```bash
make test          # 81 tests verts
jabfy-bus demo --steps 10
```

Sortie attendue :

```text
ticks           : 10
entities        : 3
decisions       : 1
executed        : 1
lamp state      : ON
audit records   : 4
audit verified  : True
```

## Et la suite ? (roadmap)

- **Phase 2 — domotique sérieuse** : déjà entamée en avance (Zigbee2MQTT ✅,
  WebSocket ✅). Reste : bridge Home Assistant, adapter Matter expérimental,
  découverte automatique des capacités.
- **Phase 3 — industriel/bâtiment** : Modbus TCP déjà livré ✅. Reste : OPC UA,
  BACnet, KNX, policies avancées avec validation humaine pour les commandes
  high/critical.
- **Phase 4 — IoT étendu** : LoRaWAN, LwM2M, BLE, gestion du cycle de vie des devices.

## Points d'attention à mentionner honnêtement

- L'adapter **CoAP n'est qu'un squelette** (contrat posé, pas d'implémentation réseau).
- Le **Reasoning Engine** est volontairement minimal en phase 1 (règles simples
  type motion → light) ; c'est la couche qui montera en puissance ensuite.
- Pas encore testé sur du **matériel réel** — tout est validé via clients
  injectables et simulation ; c'est le prochain jalon naturel.
