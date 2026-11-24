# Étape 13 — Outils et alternatives pour la déduplication

Ce document complète la section 13 du [README](../README.md).

## Comparaison des outils

| Outil | Avantages | Limites pour cette revue |
|---|---|---|
| Zotero | Gratuit ; fusion des doublons dans l'interface | Fusion manuelle notice par notice ; pas de journal exportable des décisions |
| EndNote | « Find Duplicates » robuste | Payant ; règles peu visibles |
| Rayyan | Détection des doublons intégrée au tri | Seuils non documentés ; dépend d'une plateforme en ligne |
| Excel | Accessible | Pas de comparaison floue ; erreurs de manipulation difficiles à tracer |
| **Python (choisi)** | Règles explicites et versionnées ; journal complet ; rejouable à l'identique ; contrôle automatique par rapport à la SLR | Demande d'écrire et de maintenir du code |

Python a été choisi pour la reproductibilité : la même commande, à partir des mêmes exports, redonne exactement 215 → 71 → 144, et chaque suppression est justifiée dans un fichier. Pour un volume beaucoup plus grand, `rapidfuzz` remplacerait `difflib` pour la similarité.


## Comment chaque outil aurait traité les 5 cas ambigus de cette revue

| Cas | Bonne décision | Règle « titre identique = doublon » (énoncé, Excel) | Fusion automatique typique (Zotero, Mendeley, Rayyan) | Ce script |
|---|---|---|---|---|
| OL2A 2024, volumes CCIS 2280 et 2281 | Distinct | Doublon (erreur) | Doublon proposé, à refuser à la main | Envoyé en vérification (volumes différents), puis Distinct |
| OL2A 2025, volumes CCIS 2617 et 2618 | Distinct | Doublon (erreur) | Doublon proposé, à refuser à la main | Envoyé en vérification, puis Distinct |
| Blekos : conférence CEUR 2020 et revue JSAN 2021 | Distinct (même étude) | Doublon (erreur, faite dans la SLR) | Doublon proposé, car le DOI ne manque que d'un côté | Envoyé en vérification (types et années différents), puis Distinct |
| Atacama : DOI avec et sans suffixe `-cd` | Doublon | Doublon | Souvent non détecté, car les DOI diffèrent | Envoyé en vérification (DOI différents), puis Doublon |

La colonne « fusion automatique typique » décrit un comportement courant, pas le résultat d'un test de chaque logiciel ; les règles exactes varient selon les versions et les réglages.

## Quand utiliser quel outil ?

- **Moins de quelques centaines de références, un seul relecteur** : Zotero ou Rayyan suffisent, à condition de noter à la main chaque fusion refusée ou acceptée.
- **Revue systématique à publier** : un script (Python, R) ou EndNote avec un export du journal des doublons, pour pouvoir justifier chaque nombre du diagramme PRISMA.
- **Plusieurs milliers de références** : un script avec un index (blocage par année ou par premiers mots du titre) et `rapidfuzz` au lieu de `difflib`.

## Choix pour cette revue

Le script Python a été retenu pour trois raisons mesurables :
1. il redonne exactement 215 → 71 → 144 à chaque exécution (`tests/test_resultats_publies.py`) ;
2. chaque suppression est justifiée dans `output/03_log_doublons_supprimes.csv`, et chaque cas ambigu dans `manual/manual_decisions.csv` ;
3. il a permis de détecter une erreur de la SLR : la fusion des deux publications Blekos, causée par la règle « titre identique = doublon » utilisée dans la première version.
