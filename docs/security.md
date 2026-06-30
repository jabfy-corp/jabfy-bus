# Sécurité — règles d'or du bus

## 1. Lecture / écriture séparées

- Tout adapter est **read-only par défaut** (`AdapterMode.READ_ONLY`).
- L'écriture est un opt-in explicite à deux niveaux : le mode de
  l'adapter ET, pour Modbus, le `write_allowed` de chaque registre.
- `WriteNotAllowed` est levée sur toute tentative non autorisée.

## 2. Toute commande passe par le Verification Engine

```text
command.requested → Verification Engine → command.approved | command.rejected
                                              ↓
                                       Execution Layer
                                              ↓
                                         Audit append-only
```

Interdit absolu : `IA → publish MQTT direct`. L'Execution Layer lève
`VerificationBypass` si un `command.approved` ne provient pas du
Verification Engine ou n'a pas de `correlation_id`.

## 3. Niveaux de risque

| Niveau | Exemple | Validation |
|---|---|---|
| `low` | Lire une température | Auto (default allow) |
| `medium` | Allumer une lumière | Policy explicite requise |
| `high` | Ouvrir une porte, désactiver l'alarme | Policy stricte (default deny) |
| `critical` | Action machine, coupure énergie | Policy stricte + contexte (default deny) |

Le risque est `max(risque de l'action, plancher du domaine cible)` :
une action anodine sur une serrure reste `high`. Une action ou un
domaine inconnus sont classés `critical` (on ne devine jamais qu'une
commande est bénigne).

## 4. Policies

Déclaratives, évaluées dans l'ordre, première qui matche gagne.
Critères : risque max, domaines, actions, entités, lieux, niveau de
confiance minimal de la source, fenêtre horaire (gère les fenêtres
passant minuit). Sans match : **default deny** au-delà de `low`.

## 5. Niveaux de confiance

`untrusted < local_network < local_gateway < verified_device < internal`

Le `trust_level` est estampillé par l'adapter émetteur et entre dans
l'évaluation des policies (`min_trust`).

## 6. Audit

- Append-only, JSON Lines, un enregistrement par ligne.
- Chaînage SHA-256 : chaque enregistrement embarque le hash du
  précédent ; `jabfy-bus audit-verify <fichier>` détecte toute
  altération.
- Tracés automatiquement : tous les `command.*` + les messages `audit`.

## 7. Surfaces d'exposition

- L'API HTTP/WebSocket est **en lecture seule** : aucun endpoint
  d'exécution. Les commandes entrent uniquement par le bus.
- Broker MQTT : TLS + ACL obligatoires en production, jamais d'accès
  anonyme, attention aux retained messages (une vieille commande
  conservée peut être rejouée).
