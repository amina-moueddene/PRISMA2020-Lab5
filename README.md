# Lab 5 — Fusionner les résultats et supprimer les doublons

**Revue systématique :** *Machine learning and remote sensing for disease and stress detection in olive* (PRISMA 2020 / PRISMA-S)
**Sources :** exports Scopus (CSV) et Web of Science Core Collection (BibTeX) de la recherche du 15/11/2026 (requête V1 du Lab 3)
**Résultat :** 215 notices → 71 doublons supprimés → **144 références uniques** prêtes pour le tri

Ce dépôt refait la fusion et le dédoublonnage de la revue à partir des exports bruts, avec un script reproductible et une trace de chaque décision. Il met aussi en évidence **une erreur de dédoublonnage dans la version actuelle de la SLR** (section 9).

![tests](https://github.com/amina-moueddene/PRISMA2020-Lab5/actions/workflows/tests.yml/badge.svg)

## En bref

**Technologies.** **Python 3 + pandas** pour la fusion et le dédoublonnage ; `difflib` (bibliothèque standard) pour la similarité des titres ; `unittest` pour les tests. Les données sont des **exports bibliographiques** (CSV Scopus, BibTeX WoS), pas une base relationnelle : le lab ne demande **pas de SQL**.

**Résultat :** 215 notices → 70 doublons par DOI + 1 confirmé manuellement → **144 références uniques**. Ce résultat corrige la SLR, qui avait fusionné à tort une communication de conférence et l'article de revue de même titre (section 9).

**Correspondance étapes → fichiers**

| Étape du lab | Section | Fichiers |
|---|---|---|
| 1 Introduction | §1 | `README.md`, `requirements.txt` |
| 2 Import et exploration | §2 | `scripts/deduplicate.py` (`read_scopus`, `read_wos`), `output/00_exploration.txt` |
| 3 Harmonisation | §3 | `scripts/deduplicate.py`, `output/01_references_fusionnees_harmonisees.csv` |
| 4 Normalisation titres / DOI | §4 | `normalize_title`, `normalize_doi`, `surnames` ; `tests/test_normalisation.py` |
| 5 Priorité 1 : DOI | §5 | `scripts/deduplicate.py` (P1) |
| 6 Titre normalisé | §6 | `scripts/deduplicate.py` (P2) |
| 7 Similarité + auteurs | §7 | `scripts/deduplicate.py` (P3) |
| 8 Vérification manuelle | §8 | `output/02_verification_manuelle.csv` |
| 9 Doublon réel / distinct | §9 | `manual/manual_decisions.csv`, `tests/test_pipeline.py` (`TestPiegesEtape9`) |
| 10 Suppression + provenance | §10 | `output/03_log_doublons_supprimes.csv` |
| 11 Traçabilité PRISMA | §11 | `output/04_rapport_prisma.csv`, `output/06_controle_vs_SLR.txt` |
| 12 Dataset final | §12 | `output/05_dataset_final_screening_public.csv` |
| 13 Outils et alternatives | §13 | [`docs/etape13_outils_deduplication.md`](docs/etape13_outils_deduplication.md) |
| 14 Vérification et défis | §14 | [`docs/etape14_verification_defis.md`](docs/etape14_verification_defis.md), `tests/test_pipeline.py` (`TestDefi1`) |

**Tests** (21 tests, sans les exports bruts) : `python -m unittest discover -s tests -t . -v`
- `test_normalisation.py` : titres (casse, ponctuation, accents, espace insécable, tiret long), DOI (4 formats de préfixe), noms d'auteurs Scopus et WoS, lecture du BibTeX, union-find ;
- `test_pipeline.py` : pipeline complet sur des exports fictifs, dont le **défi 1** (R1 à R4) et les pièges de l'étape 9 ;
- `test_resultats_publies.py` : cohérence des résultats publiés (215 − 71 = 144, chaque notice conservée ou journalisée, aucun DOI en double, provenance 71/47/26, chaque cas ambigu justifié).

Ils sont exécutés automatiquement par GitHub Actions à chaque envoi (`.github/workflows/tests.yml`).

## Contenu du dépôt

| Fichier | Rôle |
|---|---|
| `README.md` | Rapport du lab (ce document) |
| `scripts/deduplicate.py` | Pipeline complet : import, harmonisation, normalisation, priorités P1–P4, journal, rapport PRISMA, dataset final |
| `manual/manual_decisions.csv` | Décisions manuelles sur les cas ambigus, avec justification (entrée du script) |
| `output/00_exploration.txt` | Exploration des exports (champs vides, types de documents) |
| `output/01_references_fusionnees_harmonisees.csv` | Les 215 notices dans le schéma commun, avec les colonnes normalisées (sans résumés) |
| `output/02_verification_manuelle.csv` | Tableau de travail des paires ambiguës et décision prise |
| `output/03_log_doublons_supprimes.csv` | Journal des 71 notices supprimées : raison, base d'origine, notice conservée |
| `output/04_rapport_prisma.csv` | Chiffres PRISMA par base |
| `output/05_dataset_final_screening_public.csv` | Dataset final (144 références, sans résumés) |
| `output/06_controle_vs_SLR.txt` | Comparaison avec le tableau de tri de la SLR |
| `data/Screening_ledger_olive_PRISMA2020.csv` | Tableau de tri de la SLR (143 lignes), utilisé pour le contrôle |
| `raw/README.md` | Où placer les exports bruts (non publiés) |
| `docs/etape13_outils_deduplication.md` | Étape 13 détaillée : outils, traitement des cas ambigus par chaque outil, choix |
| `docs/etape14_verification_defis.md` | Étape 14 détaillée : questions, défis 1 et 2, et tests qui les vérifient |
| `tests/` | 21 tests automatiques |
| `.github/workflows/tests.yml` | Exécution automatique des tests sur GitHub |

Non publiés (voir `.gitignore`) : les exports bruts et les deux versions du dataset final qui contiennent les résumés (`05_dataset_final_screening.csv` et `.ris`). Les résumés appartiennent aux bases et leur diffusion publique est restreinte par leurs conditions d'utilisation.

**Reproduire :** placer les deux exports dans `raw/`, puis
```bash
pip install -r requirements.txt
python scripts/deduplicate.py
```

---

## 1. Introduction et prérequis

Une même publication est souvent indexée dans plusieurs bases. Avant le tri, il faut donc fusionner les exports et ne garder qu'une notice par publication, **sans supprimer de publication distincte** et en gardant la trace de ce qui a été retiré (PRISMA 2020, item 16 et diagramme de flux).

Outils : Python 3 et pandas ; `difflib` (bibliothèque standard) pour la similarité des titres. Cette revue n'a interrogé que deux bases (Scopus et WoS). IEEE Xplore et ACM DL, cités dans l'énoncé, n'ont pas été interrogés (Lab 3, étape 13), mais le script s'étend à d'autres sources en ajoutant une fonction de lecture.

## 2. Importation et exploration des données brutes

| Base | Format | Notices | Sans DOI | Sans auteurs | Types de documents |
|---|---|---:|---:|---:|---|
| Scopus | CSV | 118 | 11 | 9 | Article 68 ; Conference paper 31 ; Conference review 9 ; Review 4 ; Book chapter 3 ; Book 2 ; Editorial 1 |
| Web of Science | BibTeX | 97 | 0 | 0 | Article 80 ; Proceedings Paper 17 |
| **Total brut** | | **215** | | | |

Les deux exports sont lus en UTF-8 (avec BOM). Le BibTeX de WoS est lu par un analyseur qui gère les accolades imbriquées et les champs sur plusieurs lignes. Les 9 notices Scopus sans auteurs sont des « Conference review », c'est-à-dire la présentation d'un volume d'actes.

## 3. Harmonisation des métadonnées

Les deux bases nomment différemment les mêmes champs. Schéma commun :

| Champ commun | Scopus (CSV) | WoS (BibTeX) |
|---|---|---|
| `ID` | `SCO-001` … `SCO-118` | `WOS-001` … `WOS-097` |
| `Source` | Scopus | WoS |
| `ID_base` | `EID` | clé `WOS:…` |
| `Titre` | `Title` | `Title` |
| `DOI` | `DOI` | `DOI` |
| `Auteurs` | `Authors` (`Nom I.; …`) | `Author` (`Nom, Prénom and …`) |
| `Annee` | `Year` | `Year` |
| `Type_document` | `Document Type` | type de notice (`@article`, `@inproceedings`) |
| `Revue_ou_conference` | `Source title` | `Journal` ou `Booktitle` |
| `Volume`, `Pages`, `ISBN` | `Volume`, `Page start`–`Page end`, `ISBN` | `Volume`, `Pages`, `ISBN` |
| `Resume`, `Mots_cles` | `Abstract`, `Author Keywords` + `Index Keywords` | `Abstract`, `Keywords` + `Keywords-Plus` |

Les types de documents sont regroupés en familles (`article`, `conference`, `livre`), car Scopus écrit « Conference paper » là où WoS écrit « Proceedings Paper ». La colonne `Source` n'est jamais supprimée : elle permet de dire de quelle(s) base(s) vient chaque référence finale.

## 4. Normalisation des titres et des DOI

Les colonnes normalisées sont **ajoutées** ; les colonnes d'origine sont conservées pour la vérification manuelle.

| Champ | Règles | Exemple |
|---|---|---|
| `Titre_norm` | suppression des accents (NFKD), minuscules, suppression des balises, ponctuation et tirets remplacés par une espace, espaces multiples réduits | `Spatio-Temporal Assessment…` → `spatio temporal assessment…` |
| `DOI_norm` | minuscules, suppression des préfixes `https://doi.org/`, `http://dx.doi.org/` et `doi:`, suppression de la ponctuation finale | `https://doi.org/10.3390/RS70505584` → `10.3390/rs70505584` |
| `Premier_auteur` | nom de famille du premier auteur, sans accents ni ponctuation, selon le format de chaque base | `Calderón R.` et `Calderon, Rocio` → `calderon` |

Par rapport au code de l'énoncé, la normalisation du titre traite aussi les tirets, les accents et les guillemets typographiques, et celle du DOI traite le préfixe `https://`, qui est le format utilisé par Scopus.

## 5. Stratégie de déduplication par priorité

| Priorité | Critère | Action |
|---|---|---|
| **P1** | DOI normalisé identique | Fusion automatique |
| **P2** | Titre normalisé identique, **sans contradiction** (DOI non contradictoires, même famille de document, année à ±1 an, même volume pour deux notices de la même base) | Fusion automatique ; s'il y a une contradiction → vérification manuelle |
| **P3** | Titre similaire (`difflib`) : ≥ 0,90 avec le même premier auteur ou une année à ±1 an, ou ≥ 0,80 avec le même premier auteur | Vérification manuelle |
| **P4** | Cas ambigus de P2 et P3 | Décision manuelle consignée dans `manual/manual_decisions.csv` |

Les notices fusionnées sont regroupées par union-find : si A = B et B = C, alors A, B et C forment un seul groupe.

**Résultat P1 :** 70 groupes de DOI identiques, chacun formé d'une notice Scopus et d'une notice WoS. Il n'y a aucun DOI répété à l'intérieur d'une même base.

## 6. Détection des doublons par titre normalisé

Après P1, **5 paires** de notices non fusionnées ont un titre normalisé identique. **Aucune n'a été fusionnée automatiquement**, car chacune présente une contradiction :

| Paire | Contradiction détectée |
|---|---|
| SCO-025 / SCO-093 | volumes différents (CCIS 2281 / 2280) |
| SCO-032 / SCO-049 | volumes différents (CCIS 2618 / 2617) |
| SCO-069 / SCO-102 | types différents (Conference paper / Article), années 2020 / 2021, volumes différents |
| SCO-069 / WOS-016 | types différents (Conference paper / Article) |
| SCO-117 / WOS-080 | DOI différents |

C'est l'écart principal avec le code de l'énoncé, qui marque comme doublon **tout** titre identique. Appliquée ici, cette règle aurait supprimé à tort trois publications distinctes (sections 8 et 9).

## 7. Similarité des titres et comparaison des auteurs

La similarité est calculée avec `difflib.SequenceMatcher` sur les titres normalisés de toutes les paires de groupes restants (environ 10 000 paires, calcul immédiat pour 145 groupes). Un filtre évite les calculs inutiles : si 2 × (longueur du titre le plus court) / (somme des longueurs) est sous le seuil, la similarité ne peut pas l'atteindre. **Aucune paire supplémentaire** n'atteint les seuils de P3 : tous les cas ambigus avaient déjà été repérés en P2.

Limite observée : la comparaison des auteurs dépend du format de la base. Dans les notices Scopus d'actes CEUR, les noms sont inversés (« Kostas B. » au lieu de « Blekos K. »), si bien que le premier auteur de SCO-069 devient `kostas` alors que celui de SCO-102 est `blekos`. Le critère automatique sur les auteurs aurait échoué ; c'est l'**identifiant d'auteur Scopus** (36738709800, identique dans les deux notices) qui a permis de conclure à la vérification manuelle.

Autre anomalie des données : le titre Scopus de SCO-079 commence par « ssessing » au lieu de « Assessing ». Une erreur de ce type empêche la correspondance exacte des titres, et seule une comparaison floue la retrouve (section 11).

## 8. Vérification manuelle des cas ambigus

Tableau de travail : [`output/02_verification_manuelle.csv`](output/02_verification_manuelle.csv). Il contient, pour chaque paire, le titre, le DOI, les auteurs, l'année, le type, la revue, le volume, les pages, l'ISBN et la base. Les décisions et leur justification sont dans [`manual/manual_decisions.csv`](manual/manual_decisions.csv).

| Paire | Décision | Justification |
|---|---|---|
| SCO-025 / SCO-093 | **Distinct** | Présentation de deux volumes différents des actes OL2A 2024 (CCIS 2281 et 2280) : ISBN et EID différents |
| SCO-032 / SCO-049 | **Distinct** | Même cas pour OL2A 2025 (CCIS 2618 et 2617) |
| SCO-069 / SCO-102 | **Distinct** | Communication de conférence (CEUR vol. 2844, 2020, p. 98–107, sans DOI) et article de revue étendu (*J. Sensor and Actuator Networks* 10, 2021) ; mêmes auteurs |
| SCO-069 / WOS-016 | **Distinct** | WOS-016 est la notice WoS du même article de revue 2021 |
| SCO-117 / WOS-080 | **Doublon** | Même communication du congrès IAHR 2025 : titre, auteurs, année et ISBN identiques ; DOI qui ne diffèrent que par le suffixe `-cd` (version CD des actes) ; pages décalées de 2 pour une même longueur |

## 9. Doublon réel ou publications distinctes

Les règles appliquées à la vérification manuelle :

| Indice | Doublon réel | Publications distinctes |
|---|---|---|
| DOI | identique, ou variante d'un même DOI | différents, ou un seul des deux a un DOI |
| Type | même famille | conférence / revue |
| Année | identique ou ±1 (indexation anticipée) | écart d'au moins un an avec un changement de support |
| Volume, pages, ISBN | identiques | différents |
| Auteurs | identiques | identiques ou proches (même équipe) |

**Cas Blekos (SCO-069 / SCO-102 / WOS-016) : erreur dans la SLR actuelle.** La version actuelle de la revue a fusionné la communication CEUR 2020 avec l'article de revue 2021 parce que leurs titres sont identiques. C'est le piège décrit dans le lab : ce sont **deux publications distinctes de la même étude**, l'une de conférence, l'autre une version étendue en revue. Elles doivent être gardées toutes les deux et rattachées à une même étude au moment du tri, comme la SLR l'a fait pour les deux rapports Kallel 2022 / Makhloufi 2022. La SLR décrivait aussi ce cas comme « une notice indexée deux fois dans Scopus », alors que ce sont deux publications différentes.

**Cas OL2A.** La règle « titre identique = doublon » aurait aussi fusionné les présentations de deux volumes différents d'un même congrès. La SLR les avait correctement gardés séparés.

## 10. Suppression des doublons et conservation de la provenance

Dans chaque groupe, la notice conservée est **la plus complète** : nombre de champs remplis parmi DOI, auteurs, année, résumé, mots-clés, revue et langue. En cas d'égalité, la notice Scopus est préférée, puis l'identifiant le plus petit. Les notices Scopus contiennent la langue et des mots-clés indexés absents de l'export BibTeX de WoS ; ce sont donc elles qui ont été conservées dans les 71 groupes mixtes.

La provenance n'est pas perdue :
- chaque référence finale indique ses `Bases` (`Scopus + WoS`, `Scopus` ou `WoS`) et ses `IDs_fusionnes` (ex. `SCO-044; WOS-070`) ;
- le journal [`output/03_log_doublons_supprimes.csv`](output/03_log_doublons_supprimes.csv) liste les 71 notices retirées avec leur base, leur identifiant d'origine, la raison (P1 ou P4) et la notice conservée.

**Contrôles d'intégrité** après suppression : 0 DOI dupliqué. Il reste 3 titres normalisés en double, tous justifiés à la section 8 (OL2A 2024, OL2A 2025, Blekos conférence / revue).

## 11. Traçabilité PRISMA et documentation

Rapport : [`output/04_rapport_prisma.csv`](output/04_rapport_prisma.csv).

| Base | Importées | Doublons retirés | Références uniques présentes dans la base | Uniquement dans cette base |
|---|---:|---:|---:|---:|
| Scopus | 118 | 0 | 118 | 47 |
| Web of Science | 97 | 71 | 97 | 26 |
| **Total** | **215** | **71** | **144** | 71 dans les deux bases |

Doublons retirés par critère : 70 par DOI (P1), 1 après vérification manuelle (P4), 0 par titre automatique (P2) et 0 par similarité (P3).

```
Scopus (118) ──┐
               ├──→ Fusion (215)
WoS (97) ──────┘
                      ↓
        P1 DOI identique ............ −70
                      ↓
        P2 Titre identique .......... 5 paires, 0 fusion automatique → vérification
                      ↓
        P3 Titre similaire + auteur . 0 paire supplémentaire
                      ↓
        P4 Vérification manuelle .... 5 paires : 1 doublon (−1), 4 distinctes
                      ↓
        Références uniques pour le tri : 144
        (71 dans les deux bases, 47 Scopus seul, 26 WoS seul)
```

**Contrôle par rapport à la SLR** ([`output/06_controle_vs_SLR.txt`](output/06_controle_vs_SLR.txt)). L'appariement un à un (DOI, puis titre, puis titre très similaire) retrouve 143 des 144 références dans le tableau de tri de la SLR (133 par DOI, 9 par titre, 1 par titre très similaire, celle du titre « ssessing »). La seule référence absente est la communication CEUR 2020 de Blekos et al. (SCO-069).

| | SLR actuelle | Ce lab |
|---|---:|---:|
| Notices importées | 215 | 215 |
| Doublons retirés | 72 (70 DOI + 2 titre) | **71** (70 DOI + 1 manuel) |
| Références uniques | 143 | **144** |
| Dans les deux bases / Scopus seul / WoS seul | 71 / 46 / 26 | 71 / **47** / 26 |

**Correction proposée pour la SLR :** 71 doublons retirés et 144 références triées. SCO-069 doit être triée ; c'est la version conférence d'une étude incluse (Blekos 2021), donc probablement un rapport supplémentaire rattaché à la même étude. Le nombre d'études incluses (22) ne devrait pas changer, mais ce sera à confirmer au tri.

## 12. Préparation du dataset final pour le screening

| Fichier | Contenu | Publié |
|---|---|---|
| `output/05_dataset_final_screening_public.csv` | 144 références : ID unique, titre, auteurs, année, DOI, type, revue, langue, bases, notices fusionnées | oui |
| `output/05_dataset_final_screening.csv` | idem + résumé et mots-clés, pour le tri sur titre et résumé | non (local) |
| `output/05_dataset_final_screening.ris` | même contenu au format RIS, importable directement dans Rayyan, Zotero ou EndNote | non (local) |

Validation : 144 lignes ; 0 DOI dupliqué ; aucun titre vide ; `Bases` remplie partout. Les seules valeurs manquantes viennent des exports eux-mêmes : 11 DOI absents (Scopus), 9 auteurs absents (présentations de volumes), langue absente pour les 26 notices propres à WoS (l'export BibTeX ne la fournit pas).

## 13. Outils et alternatives

Version détaillée : [`docs/etape13_outils_deduplication.md`](docs/etape13_outils_deduplication.md).

| Outil | Avantages | Limites pour cette revue |
|---|---|---|
| Zotero | Gratuit ; fusion des doublons dans l'interface | Fusion manuelle notice par notice ; pas de journal exportable des décisions |
| EndNote | « Find Duplicates » robuste | Payant ; règles peu visibles |
| Rayyan | Détection des doublons intégrée au tri | Seuils non documentés ; dépend d'une plateforme en ligne |
| Excel | Accessible | Pas de comparaison floue ; erreurs de manipulation difficiles à tracer |
| **Python (choisi)** | Règles explicites et versionnées ; journal complet ; rejouable à l'identique ; contrôle automatique par rapport à la SLR | Demande d'écrire et de maintenir du code |

Python a été choisi pour la reproductibilité : la même commande, à partir des mêmes exports, redonne exactement 215 → 71 → 144, et chaque suppression est justifiée dans un fichier. Pour un volume beaucoup plus grand, `rapidfuzz` remplacerait `difflib` pour la similarité.

## 14. Vérification et défis

Version détaillée, avec les tests qui exécutent les défis : [`docs/etape14_verification_defis.md`](docs/etape14_verification_defis.md).

**Q1. Pourquoi normaliser les titres avant de les comparer ?**
Parce que la même publication est écrite différemment selon les bases, et qu'une comparaison exacte la compterait deux fois (faux négatif). Mesuré sur nos données : parmi les 70 paires Scopus/WoS de même DOI, **19 ont des titres bruts différents** ; après normalisation, il n'en reste que **2**. Exemples réels :
- **casse** (11 paires) : *Soil temperature determines the reaction…* (Scopus) / *Soil Temperature Determines the Reaction…* (WoS), ou un titre entièrement en majuscules dans WoS ;
- **caractères invisibles ou typographiques** : dans *Olive Leaf Infection Detection Using the Cloud-Edge Continuum*, Scopus met une espace insécable avant « Cloud » et WoS une espace normale ; *TEBAKA – A technological platform* (tiret long) contre *TEBAKA - A technological platform* (trait d'union).

Les 2 paires restantes montrent les limites de la normalisation : *downsampled* / *down-sampled* (similarité 0,996) et un titre Scopus suivi de sa traduction turque entre crochets (similarité 0,63). Le DOI les rattrape ici ; sans DOI, il faudrait la similarité (P3) pour la première et la lecture manuelle pour la seconde.

**Q2. Doublon réel ou deux publications de la même étude ?**
Un doublon réel est **la même publication indexée deux fois** (ici, la notice Scopus et la notice WoS d'un même article). Deux publications de la même étude sont **deux documents différents**, par exemple une communication de conférence et sa version étendue en revue. En pratique, on compare le DOI, le type de document, l'année, le volume, les pages et l'ISBN, puis on lit les résumés. Exemple réel : Blekos et al., CEUR 2020 (sans DOI) et *JSAN* 2021 (DOI 10.3390/jsan10010015) ont le même titre et les mêmes auteurs mais sont deux publications. On les garde et on les rattache à la même étude au moment du tri.

**Q3. Pourquoi la traçabilité PRISMA est-elle essentielle ?**
Parce que le diagramme PRISMA doit permettre de vérifier que les nombres s'enchaînent (215 − 71 = 144), et qu'un lecteur doit pouvoir contrôler qu'aucune publication n'a été écartée à tort. Sans journal des doublons, l'erreur de la section 9 serait invisible. Avec le journal et le contrôle automatique, elle a été repérée et peut être corrigée.

**Défi 1. Identifier les doublons.**

| Paire | Décision | Justification |
|---|---|---|
| R1 / R2 | **Doublon réel** | Même DOI (10.123/abc), même titre, même année ; « Smith, J. » et « Smith, John » sont deux formats du même auteur |
| R1 / R3 | **Distinctes** | DOI différents et titre différent (« … Security »). Même auteur et même année : il peut s'agir de deux publications de la même étude, à rattacher au tri après lecture des résumés, pas à supprimer |
| R1 / R4 | **Distinctes** | Même titre, mais DOI, auteur et année différents : titre homonyme |
| R3 / R4 | **Distinctes** | Rien en commun hormis une partie du titre |

Résultat : 4 notices → 1 doublon supprimé (R2) → 3 références uniques.

**Défi 2. Détecter les doublons sans DOI.** Ordre proposé, appliqué dans ce lab :
1. **Titre normalisé identique**, fusionné automatiquement seulement si rien ne le contredit : même famille de document, année à ±1 an, volume, ISBN ou pages compatibles.
2. **Titre similaire** (similarité ≥ 0,90) **et** un indice indépendant : même premier auteur, identifiant d'auteur identique, même année et même revue. Tout cas qui ne remplit qu'une partie de ces critères va en vérification manuelle.
3. **Vérification manuelle** de tous les cas ambigus, avec un tableau côte à côte et une décision justifiée écrite dans un fichier.

Pour les titres légèrement différents, la similarité seule ne suffit pas : une version « … Security » d'un article peut être une autre publication. On exige donc un second indice (auteurs, année, revue). On se méfie aussi des formats d'auteurs propres à chaque base, comme les noms inversés de Scopus pour les actes CEUR : quand ils existent, on utilise de préférence les identifiants d'auteur (Scopus Author ID, ORCID).

## Références méthodologiques

- Page MJ et al. (2021). The PRISMA 2020 statement. *BMJ* 372:n71.
- Rethlefsen ML et al. (2021). PRISMA-S: an extension to the PRISMA statement for reporting literature searches in systematic reviews. *Systematic Reviews* 10:39.
