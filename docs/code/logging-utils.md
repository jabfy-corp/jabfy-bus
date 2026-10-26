# `jabfy_bus/logging_utils.py`

> **Rôle** — Logs JSON structurés.

Dépôt : [jabfy-bus](README.md) · 43 lignes · statut : **actif**

Docstring du module : *Configuration du logging du bus.*

## À retenir

- `JsonFormatter` l.15, `setup_logging` l.30.

## Contenu (ligne → élément)

| ligne | élément | note |
|---|---|---|
| 15 | classe `JsonFormatter` | Une ligne JSON par événement de log. — méthodes : `format` 18 |
| 30 | `setup_logging()` | Configure le logger racine `jabfy_bus`. |

## Relations

- **Utilise** : aucun fichier JABFY documenté (bibliothèques externes seulement)
- **Utilisé par** : [examples/demo_pipeline.py](examples-demo-pipeline.md), [jabfy_bus/cli.py](cli.md)
