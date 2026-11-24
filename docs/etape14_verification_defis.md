# Étape 14 — Vérification et défis

Ce document complète la section 14 du [README](../README.md). Le défi 1 est aussi **exécuté comme test automatique** : `tests/test_pipeline.py`, classe `TestDefi1`.


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


## Défi 1 vérifié par le script

Le test `TestDefi1` crée R1 et R3 dans un export Scopus fictif, R2 et R4 dans un export WoS fictif, puis lance le pipeline complet. Il vérifie que :
- R1 et R2 sont fusionnés par le DOI (priorité P1) ; R2 (`WOS-001`) est retiré et journalisé ;
- R1 et R4 (même titre, DOI différents) **ne sont pas fusionnés automatiquement** et partent en vérification manuelle ;
- R1 et R3 (similarité des titres ≥ 0,80, même premier auteur) partent en vérification manuelle ;
- après les décisions « Distinct », il reste 3 références, et le rapport PRISMA indique 4 importées, 1 doublon, 3 conservées.

Lancer : `python -m unittest tests.test_pipeline -v`

## Défi 2 vérifié par le script

`TestPiegesEtape9` reproduit les cas réels sans DOI : une communication de conférence et l'article de revue de même titre, et deux volumes d'actes de même titre. Le test vérifie qu'ils ne sont **jamais fusionnés automatiquement**. Il vérifie aussi qu'un doublon confirmé à la main (variante `-cd` d'un DOI) est bien retiré avec la raison « P4 Vérification manuelle ».
