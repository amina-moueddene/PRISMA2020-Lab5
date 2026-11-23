# LAB 5 : Fusionner les résultats et supprimer les doublons
**Application à ma SLR : ML et télédétection pour la détection des maladies et du stress de l'olivier**

> Seules les exports de Scopus et Web of Science (recherche du 15/11/2026) sont fusionnés et dédupliqués, car ce sont les bases de ma SLR. IEEE Xplore et OpenAlex (Lab 4) ont été interrogées pour le lab seulement ; ACM DL n'a pas pu l'être. Elles ne font pas partie du flux PRISMA.

## 1. Importation et exploration des données brutes

| Source | Références importées |
|---|---|
| Scopus | 118 |
| Web of Science | 97 |
| **Total brut** | **215** |

Chaque export contient les titres, abstracts, mots-clés, auteurs et DOI. Les fichiers ont été chargés puis concaténés dans un seul tableau.

```python
import pandas as pd

df_scopus = pd.read_csv("data/scopus_results.csv", encoding="utf-8")
df_wos = pd.read_csv("data/wos_results.csv", encoding="utf-8")
print(f"Scopus: {len(df_scopus)} | WoS: {len(df_wos)}")   # 118 | 97
```

## 2. Harmonisation des métadonnées

Schéma commun : `ID`, `Titre`, `DOI`, `Auteurs`, `Année`, `Source`. La colonne `Source` (Scopus ou WoS) est conservée pour toute la suite afin de garder la provenance.

```python
def harmonize(df, source):
    df = df.copy()
    df["Source"] = source
    df["ID"] = [f"{source[:3].upper()}-{i+1:04d}" for i in range(len(df))]
    return df   # après renommage des colonnes de l'export vers le schéma commun

df_combined = pd.concat([harmonize(df_scopus, "Scopus"), harmonize(df_wos, "WoS")], ignore_index=True)
print(len(df_combined))   # 215
```

## 3. Normalisation des titres et des DOI

Règles appliquées :
- **DOI** : minuscules, sans préfixe de résolveur (`https://doi.org/`, `http://dx.doi.org/`), espaces supprimés.
- **Titre** : minuscules, **uniquement les caractères alphanumériques conservés** (ponctuation, espaces et caractères spéciaux supprimés).

Les colonnes d'origine sont conservées ; la normalisation crée de nouvelles colonnes de comparaison.

```python
import re

def normalize_doi(doi):
    if pd.isna(doi): return ""
    d = str(doi).lower().strip()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d)

def normalize_title(t):
    if pd.isna(t): return ""
    return re.sub(r"[^a-z0-9]", "", str(t).lower())

df_combined["DOI_Normalise"] = df_combined["DOI"].apply(normalize_doi)
df_combined["Titre_Normalise"] = df_combined["Titre"].apply(normalize_title)
```

## 4. Stratégie de déduplication par priorité

Stratégie appliquée dans ma SLR, en deux niveaux :

| Priorité | Critère | Doublons supprimés |
|---|---|---|
| 1 | DOI normalisé identique | **70** |
| 2 | Titre normalisé identique (enregistrements sans correspondance DOI) | **2** (dont un enregistrement indexé deux fois dans Scopus) |
| 3 à 5 | Similarité floue, titre + année, vérification manuelle | Non utilisées comme critères automatiques ; voir sections 7 et 8 |

## 5. Détection par DOI et par titre
> Le script ci-dessous reproduit la méthode appliquée (déduplication par DOI normalisé, puis par titre normalisé). Il est donné à titre d'illustration ; le script exact utilisé lors de la recherche n'a pas été conservé.

```python
df_combined["Est_Doublon"] = False
df_combined["Raison_Doublon"] = ""

# Priorité 1 : DOI (on garde la première occurrence)
has_doi = df_combined["DOI_Normalise"] != ""
dup_doi = has_doi & df_combined.duplicated(subset=["DOI_Normalise"], keep="first")
df_combined.loc[dup_doi, ["Est_Doublon", "Raison_Doublon"]] = [True, "DOI identique"]

# Priorité 2 : titre normalisé, parmi les enregistrements non déjà marqués
dup_title = (~df_combined["Est_Doublon"]) & df_combined.duplicated(subset=["Titre_Normalise"], keep="first")
df_combined.loc[dup_title, ["Est_Doublon", "Raison_Doublon"]] = [True, "Titre normalisé identique"]

print(dup_doi.sum(), dup_title.sum())   # 70, 2
```

## 6. Similarité des titres et comparaison des auteurs

Aucune suppression n'a été faite sur la base d'une similarité floue : la suppression automatique est limitée aux correspondances exactes (DOI, puis titre normalisé), qui évitent les faux positifs. Une vérification par similarité (`difflib` ou `rapidfuzz`, seuil élevé) combinée à la comparaison des auteurs ne servirait qu'à **signaler** des cas à examiner à la main.

## 7. Vérification manuelle et distinction entre doublon réel et publications distinctes

La distinction a été faite en pratique pendant le screening, au niveau de l'étude :

- **Même étude, deux rapports (comptés une fois)** : une étude décrite dans deux communications de conférence du même groupe (Kallel et al. ; Makhloufi et al.), avec les mêmes parcelles et la même méthode. Les deux rapports ont été **liés et comptés comme une seule étude**.
- **Études différentes malgré des données communes (gardées séparées)** : l'étude de Ottaviano et al. réutilise les 24 arbres de Garofalo et al. lors d'une autre saison. Les deux sont **conservées comme deux études distinctes**, car les données ont été acquises à des saisons différentes. Elles ne sont toutefois pas indépendantes, ce qui est signalé dans les limites.

Critères de décision : DOI identique, type de document (conférence ou revue), saison et données acquises, lecture du texte intégral.

## 8. Suppression des doublons et conservation de la provenance

Règle : on conserve la première occurrence et on garde la provenance (colonne `Source`). Un log des enregistrements supprimés est produit avant toute suppression.

```python
dups = df_combined[df_combined["Est_Doublon"]]
dups[["ID", "Titre", "DOI", "Source", "Raison_Doublon"]].to_csv("log_doublons_supprimes.csv", index=False)

df_clean = df_combined[~df_combined["Est_Doublon"]].reset_index(drop=True)
print(len(df_combined), len(dups), len(df_clean))   # 215 72 143
```

Provenance des 143 enregistrements uniques :

| Indexés dans | Nombre |
|---|---|
| Les deux bases | 71 |
| Scopus seul | 46 |
| Web of Science seul | 26 |
| **Total** | **143** |

Contrôle de cohérence : Scopus 118 = 71 + 46 + 1 (enregistrement indexé deux fois) ; WoS 97 = 71 + 26.

## 9. Traçabilité PRISMA et documentation

| Étape du flux PRISMA | Nombre |
|---|---|
| Enregistrements identifiés (Scopus 118 + WoS 97) | 215 |
| Doublons supprimés (70 par DOI, 2 par titre normalisé) | 72 |
| Enregistrements évalués sur titre et résumé | 143 |
| Exclus au titre/résumé | 90 |
| Rapports recherchés en texte intégral | 53 |
| Rapports non retrouvés | 15 |
| Rapports évalués en texte intégral | 38 |
| Rapports exclus en texte intégral | 15 |
| **Études incluses (23 rapports)** | **22** |

Rapport par source :

| Source | Importé | Dans le dataset unique |
|---|---|---|
| Scopus | 118 | 117 (71 communs + 46 propres) |
| Web of Science | 97 | 97 (71 communs + 26 propres) |
| Total | 215 | 143 (après regroupement des 71 communs et du doublon interne) |

Flux : Scopus (118) + WoS (97) → fusion (215) → déduplication DOI puis titre (−72) → 143 enregistrements uniques → screening.

## 10. Préparation du dataset final pour le screening

```python
final_columns = ["ID", "Titre", "DOI", "Auteurs", "Année", "Source"]
df_final = df_clean[final_columns].copy()
df_final.to_csv("dataset_final_screening.csv", index=False, encoding="utf-8-sig")

assert len(df_final) == 143
assert not df_final["Titre"].isna().any()
assert not df_final["Source"].isna().any()
dois = df_final["DOI"].dropna()
assert not dois.str.lower().duplicated().any()
```

Validations : 143 lignes ; aucun DOI dupliqué ; titres non vides ; colonne `Source` remplie. Les enregistrements sans DOI ne peuvent pas être contrôlés par cette dernière vérification (leur nombre n'a pas été comptabilisé).

## 11. Outils et alternatives

Python (pandas) a été utilisé : il est reproductible, gratuit et personnalisable, et convient au nombre limité d'enregistrements. Zotero, EndNote, Mendeley et Rayyan permettent aussi de dédupliquer, mais n'ont pas été utilisés dans ma SLR.

## 12. Questions de vérification

**Q1. Pourquoi normaliser les titres avant de les comparer ?**
Pour éviter les faux négatifs dus à des variations de forme qui n'ont aucun sens bibliographique. Exemples : « Android Security » et « android security » (casse) ; « AI: A Review » et « AI A Review » (ponctuation). Dans ma SLR, la normalisation garde uniquement les caractères alphanumériques en minuscules, ce qui rend ces variantes identiques.

**Q2. Différence entre doublon réel et publications distinctes ?**
Un doublon réel est la même publication indexée plusieurs fois (même DOI ou mêmes métadonnées). Deux publications distinctes peuvent concerner la même étude : par exemple une communication de conférence et sa version étendue en revue, ou une étude qui reprend les mêmes arbres à une autre saison (Ottaviano et al. et Garofalo et al. dans ma SLR). On les distingue par le DOI, le type de publication, la pagination et la lecture du résumé ou du texte intégral.

**Q3. Pourquoi la traçabilité PRISMA est-elle essentielle ?**
Elle garantit la reproductibilité et la transparence : un lecteur peut retrouver le nombre de références à chaque étape (215 → 143 → 22). Sans le nombre de doublons supprimés, le diagramme PRISMA est incohérent et on ne peut pas vérifier qu'aucun article n'a été éliminé à tort.

**Défi 1 : doublons dans le jeu de références**

| Paire | Verdict | Justification |
|---|---|---|
| R1 et R2 | **Doublon réel** | Même titre, même DOI (10.123/abc), même année ; « Smith, J. » et « Smith, John » ne sont que deux écritures du même auteur |
| R1 et R3 | **Distinctes** | DOI différents et titres différents (« …Android » et « …Android Security ») |
| R1 et R4 | **Distinctes** | Même titre, mais DOI, auteur et année différents : titres identiques par coïncidence |
| R3 et R4 | **Distinctes** | Titres, DOI et auteurs différents |

**Défi 2 : stratégie de détection sans DOI**
1. Titre normalisé identique, avec contrôle de l'année et des auteurs.
2. Titre très similaire (similarité élevée, par exemple supérieure à 0,9) avec les mêmes premiers auteurs et la même année.
3. Même titre et même année, mais auteurs différents : cas signalé pour vérification manuelle.
4. Pour les cas ambigus : comparer le type de document, la revue ou conférence, la pagination et le résumé ; en cas de doute, **conserver les deux références** et trancher pendant le screening.
5. Consigner chaque décision dans un log (raison, source) pour la traçabilité.

## 13. Résumé

Fusion des exports de Scopus (118) et Web of Science (97) en un dataset de 215 enregistrements, normalisation des DOI et des titres, déduplication exacte par priorité (70 par DOI, 2 par titre normalisé), soit 72 doublons supprimés et 143 enregistrements uniques, avec provenance conservée (71 communs, 46 Scopus seul, 26 WoS seul). Le flux est documenté jusqu'aux 22 études incluses. Prochaine étape : le screening titre/résumé.
