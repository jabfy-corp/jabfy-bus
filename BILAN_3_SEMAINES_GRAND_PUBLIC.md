# Ce que j'ai fait ces 3 dernières semaines — projet Jabfy Bus

**Du 23 juin au 6 juillet 2026** · Version pour public non technique

---

## Le projet, expliqué simplement

Dans une maison ou un bâtiment connecté, les objets (capteurs, lampes,
compteurs, machines…) parlent tous **des langues différentes**. Un capteur
Zigbee ne dit pas les choses de la même façon qu'un compteur industriel ou
qu'une caméra connectée. Résultat : les faire travailler ensemble est
compliqué, fragile et souvent peu sûr.

**Jabfy Bus est un traducteur universel** : quel que soit l'objet et sa
« langue », tout est converti vers un seul langage commun. Et surtout,
c'est un traducteur **prudent** :

- **Il écoute tout, mais ne touche à rien sans autorisation.** Par défaut,
  le système ne fait qu'observer. Agir sur un équipement (allumer, éteindre,
  régler) demande une permission explicite.
- **Chaque action passe par un contrôle de sécurité.** Avant d'exécuter un
  ordre, le système vérifie qu'il est autorisé, à quel niveau de risque il
  correspond, et même s'il a lieu au bon moment de la journée. Ce qui n'est
  pas explicitement permis est **refusé**.
- **Tout est enregistré dans un journal impossible à falsifier.** Chaque
  décision laisse une trace. Si quelqu'un modifie ou efface une ligne du
  journal, le système le détecte immédiatement.

## Ce qui existe aujourd'hui, après 3 semaines

Le système fonctionne **de bout en bout**. Exemple concret que je peux
montrer en direct : *un détecteur de mouvement repère quelqu'un → le système
propose d'allumer la lampe → le contrôle de sécurité vérifie que c'est
autorisé à cette heure-ci → la lampe s'allume → tout est consigné dans le
journal.* Et cette démonstration tourne **sans aucun matériel** : j'ai
construit un environnement de simulation avec des objets virtuels
(capteur de température, détecteur de mouvement, interrupteur…).

Le système sait déjà comprendre **4 familles d'objets** parmi les plus
répandues : les objets domotiques grand public (2 familles), les objets qui
communiquent par internet, et les équipements industriels/bâtiment. Une
5e famille est préparée pour la suite.

## Le déroulé, semaine par semaine

### Semaine 1 — Étudier et poser les fondations
- J'ai commencé par une **étude comparative des langages des objets
  connectés** du marché (un document d'une cinquantaine de pages) : c'est
  elle qui a guidé tous les choix ensuite.
- Puis j'ai construit le **cœur du système** : le « langage commun » dans
  lequel tout est traduit, et le « centre de tri » qui fait circuler les
  informations entre les composants.

### Semaine 2 — Brancher les premiers objets et sécuriser
- J'ai créé les **deux premiers traducteurs** (domotique et internet).
- Puis toute la **couche de sécurité**, la vraie valeur du projet :
  le contrôle qui autorise ou refuse chaque action, les règles configurables
  (par exemple « la lumière peut s'allumer automatiquement seulement entre
  18h et 23h »), et le **journal infalsifiable**.

### Semaine 3 — Élargir, démontrer et livrer
- Deux **traducteurs supplémentaires** : l'un pour la domotique avancée,
  l'autre pour les équipements industriels et de bâtiment.
- L'**environnement de simulation** qui permet de tout démontrer sans matériel.
- Un **tableau de bord consultable** (on peut voir l'état des objets et les
  décisions en temps réel, mais uniquement consulter — pas agir).
- La **finition** : documentation complète, vérifications automatiques à
  chaque modification du code, et livraison de la **première version
  officielle (0.1.0)**.

## En chiffres

| | |
|---|---|
| Durée | 3 semaines, en partant de zéro |
| Familles d'objets comprises | 4 complètes + 1 préparée |
| Vérifications automatiques | 81 tests qui valident le système à chaque modification |
| Documentation | 6 documents (fonctionnement, sécurité, feuille de route…) |
| Résultat | Première version livrée, démontrable en direct |

## Pourquoi c'est important

1. **Ouverture** : on n'est prisonnier d'aucune marque ni d'aucune
   technologie — tout objet peut être raccordé en ajoutant un traducteur.
2. **Sécurité dès la conception** : la prudence n'est pas une option qu'on
   ajoute après, elle est dans les fondations. Le système ne peut
   *structurellement* pas exécuter un ordre non contrôlé.
3. **Confiance et traçabilité** : on peut toujours répondre à la question
   « qui a fait quoi, quand, et pourquoi ça a été autorisé ? ».

## La suite

- Raccorder les **grands écosystèmes domotiques du marché** pour toucher
  plus d'équipements grand public.
- Ajouter les **protocoles industriels majeurs** (gestion technique de
  bâtiment, supervision d'usine).
- Renforcer l'**intelligence des décisions**, avec une validation humaine
  obligatoire pour les actions sensibles.
- Et le prochain jalon concret : **tester sur de vrais équipements** (tout
  a été validé en simulation jusqu'ici, c'était voulu pour aller vite et sûr).

## Ce que je peux montrer en réunion (2 minutes)

Une démonstration en direct du scénario « détection de mouvement → lampe
allumée », avec le journal de sécurité vérifié à la fin. Aucun matériel
nécessaire, tout tourne sur mon ordinateur.
