# LAB 4 : Interroger les bases scientifiques et collecter les études
**Application à ma SLR : ML et télédétection pour la détection des maladies et du stress de l'olivier**

> Dans ma SLR, seules Scopus et Web of Science ont été interrogées (15/11/2026). IEEE Xplore et OpenAlex ont été interrogées le 22/11/2026 **uniquement pour ce lab** : leurs résultats ne sont pas inclus dans le flux PRISMA de la SLR (215 → 143 → 22). ACM Digital Library n'a pas pu être interrogée (accès limité).

## 1. Rappel de la stratégie de recherche (Lab 3)

Quatre groupes reliés par AND, synonymes reliés par OR :

- **G1 Culture** : olive, olives, "Olea europaea", "olive grove*", "olive orchard*"
- **G2 Plateforme / capteur** : uav*, uas, drone*, "unmanned aerial", airborne, aircraft, "remote sensing", satellite*, sentinel*, hyperspectral, multispectral, thermal, lidar
- **G3 Cible** : disease*, pathogen*, xylella, verticillium, "olive knot", "peacock spot", infect*, symptom*, "water stress", drought, "water status", stress
- **G4 Méthode** : "machine learning", "deep learning", "artificial intelligence", "neural network*", cnn, "random forest", "support vector", svm, xgboost, "gradient boosting", yolo, "transfer learning", "discriminant analysis", classif*

## 2. Requêtes adaptées à chaque base

### Scopus (SLR, 15/11/2026)
```
TITLE-ABS-KEY(olive OR olives OR "Olea europaea" OR "olive grove*" OR "olive orchard*") AND TITLE-ABS-KEY(uav* OR uas OR drone* OR "unmanned aerial" OR airborne OR aircraft OR "remote sensing" OR satellite* OR sentinel* OR hyperspectral OR multispectral OR thermal OR lidar) AND TITLE-ABS-KEY(disease* OR pathogen* OR xylella OR verticillium OR "olive knot" OR "peacock spot" OR infect* OR symptom* OR "water stress" OR drought OR "water status" OR stress) AND TITLE-ABS-KEY("machine learning" OR "deep learning" OR "artificial intelligence" OR "neural network*" OR cnn OR "random forest" OR "support vector" OR svm OR xgboost OR "gradient boosting" OR yolo OR "transfer learning" OR "discriminant analysis" OR classif*) AND PUBYEAR > 2012 AND PUBYEAR < 2027
```
Filtres : 2013–2026. Aucun filtre de langue ni de type de document dans la base (appliqués au screening, critères E7 et E8). Résultats : **118**.

### Web of Science Core Collection (SLR, 15/11/2026)
```
TS=(olive OR olives OR "Olea europaea" OR "olive grove*" OR "olive orchard*") AND TS=(UAV* OR UAS OR drone* OR "unmanned aerial" OR airborne OR aircraft OR "remote sensing" OR satellite* OR Sentinel* OR hyperspectral OR multispectral OR thermal OR LiDAR) AND TS=(disease* OR pathogen* OR Xylella OR Verticillium OR "olive knot" OR "peacock spot" OR infect* OR symptom* OR "water stress" OR drought OR "water status" OR stress) AND TS=("machine learning" OR "deep learning" OR "artificial intelligence" OR "neural network*" OR CNN OR "random forest" OR "support vector" OR SVM OR XGBoost OR "gradient boosting" OR YOLO OR "transfer learning" OR "discriminant analysis" OR classif*) AND PY=(2013-2026)
```
Filtres : 2013–2026, toutes les éditions de l'abonnement institutionnel. Résultats : **97**.

### IEEE Xplore (lab uniquement, 22/11/2026)
Les troncatures à l'intérieur des guillemets sont mal gérées par IEEE : formes simples utilisées.
```
(("All Metadata":olive OR "All Metadata":"Olea europaea") AND ("All Metadata":UAV OR "All Metadata":drone OR "All Metadata":"remote sensing" OR "All Metadata":satellite OR "All Metadata":hyperspectral OR "All Metadata":multispectral) AND ("All Metadata":disease OR "All Metadata":xylella OR "All Metadata":verticillium OR "All Metadata":"water stress" OR "All Metadata":drought) AND ("All Metadata":"machine learning" OR "All Metadata":"deep learning" OR "All Metadata":"neural network" OR "All Metadata":CNN OR "All Metadata":SVM))
```
Filtre de période : non appliqué au moment du relevé. Résultats : **15** (14 conférences, 1 revue).

### ACM Digital Library (non interrogée)
Accès limité : la recherche n'a pas pu être réalisée. Requête prévue (non exécutée) :
```
[[Abstract: olive] OR [Abstract: "olea europaea"]] AND [[Abstract: uav] OR [Abstract: drone] OR [Abstract: "remote sensing"] OR [Abstract: satellite] OR [Abstract: hyperspectral]] AND [[Abstract: disease] OR [Abstract: xylella] OR [Abstract: verticillium] OR [Abstract: "water stress"] OR [Abstract: drought]] AND [[Abstract: "machine learning"] OR [Abstract: "deep learning"] OR [Abstract: "neural network"]]
```

### OpenAlex (lab uniquement, 22/11/2026)
```
(olive OR "Olea europaea") AND (uav OR drone OR "remote sensing" OR satellite OR hyperspectral OR multispectral OR thermal) AND (disease OR xylella OR verticillium OR "water stress" OR drought) AND ("machine learning" OR "deep learning" OR "neural network" OR "random forest" OR svm)
```
Type : works. Filtre de période : non appliqué au moment du relevé (la plage affichée allait de 2002 à 2026). Résultats : **75 works**.

## 3. Tableau de suivi de la recherche

| Base | Date | Requête utilisée | Filtres | Résultats | Format exporté | Inclus dans la SLR |
|---|---|---|---|---|---|---|
| Scopus | 15/11/2026 | Section 2 (TITLE-ABS-KEY) | 2013–2026 | 118 | CSV | Oui |
| Web of Science | 15/11/2026 | Section 2 (TS=) | 2013–2026 | 97 | RIS | Oui |
| IEEE Xplore | 22/11/2026 | Section 2 | Aucun filtre de période | 15 | BibTeX | Non (lab) |
| ACM DL | Non interrogée | Section 2 (prévue) | Accès limité | n/a | n/a | Non |
| OpenAlex | 22/11/2026 | Section 2 | Aucun filtre de période | 75 | CSV | Non (lab) |

Règle respectée : une requête exécutée n'est jamais modifiée ; tout ajustement crée une nouvelle ligne.

## 4. Gestion des références avec Zotero

Zotero n'a pas été utilisé. Les exports des bases ont été fusionnés directement dans un fichier unique (titres, abstracts, mots-clés, auteurs, DOI), puis dédupliqués par script.

## 5. Dataset brut pour la déduplication

Colonnes : `id`, `title`, `authors`, `year`, `source`, `doi`.
Après fusion de Scopus et WoS : **215 enregistrements**.

```python
import pandas as pd, re

df = pd.concat([df_scopus.assign(source="Scopus"), df_wos.assign(source="WoS")], ignore_index=True)

df["doi_norm"] = (df["doi"].fillna("").str.lower()
                  .str.replace(r"^https?://(dx\.)?doi\.org/", "", regex=True).str.strip())
df["title_norm"] = df["title"].fillna("").str.lower().apply(lambda t: re.sub(r"[^a-z0-9]", "", t))

df.to_csv("raw_bibliographic_dataset.csv", index=False)
print(len(df), "références")
```

## 6. Analyse des doublons potentiels

Méthode : déduplication **exacte** en deux temps, d'abord par DOI normalisé (minuscules, sans préfixe de résolveur), puis par titre normalisé (minuscules, caractères alphanumériques seulement) pour les enregistrements sans correspondance DOI.

| Étape | Nombre |
|---|---|
| Enregistrements avant déduplication | 215 |
| Doublons supprimés par DOI | 70 |
| Doublons supprimés par titre | 2 (dont un enregistrement indexé deux fois dans Scopus) |
| **Enregistrements uniques** | **143** |
| Indexés dans les deux bases | 71 |
| Scopus seul | 46 |
| Web of Science seul | 26 |

Les doublons n'ont pas été supprimés sans vérification : les rapports d'une même étude publiés sous des titres différents ont été liés pendant le screening et comptés une seule fois au niveau de l'étude (23 rapports → 22 études).

## 7. Rayyan

Rayyan n'a pas été utilisé. La déduplication a été faite par script (DOI puis titre) et les décisions de screening sont tracées dans un ledger (Supplementary Material S1).

## 8. Vérification et questions de réflexion

**1. Comparaison Scopus (118) et Web of Science (97).** Les deux bases ne retournent pas les mêmes enregistrements : 71 sont communs, 46 sont propres à Scopus et 26 propres à WoS. Chaque base a sa propre couverture de revues et d'actes de conférence.

**2. Explication des écarts.** Pour une requête quasi identique, les résultats diffèrent à cause de :
- la couverture différente des revues et conférences (Scopus et WoS ne sélectionnent pas les mêmes sources) ;
- les champs interrogés (TITLE-ABS-KEY pour Scopus, Topic pour WoS) ;
- les algorithmes de recherche et le traitement des troncatures et des pluriels ;
- la qualité et l'exhaustivité des métadonnées indexées.

Le même effet se voit avec les bases du lab : IEEE Xplore (15 résultats, surtout des conférences) et OpenAlex (75 works) donnent des volumes très différents de Scopus et WoS, car leur couverture et leur syntaxe de recherche diffèrent.

**3. Qualité des données.** Dans le dataset dédupliqué (143 enregistrements), **10 n'ont pas de DOI** (environ 7 %) ; le nombre de références sans abstract n'a pas été comptabilisé. Les références sans DOI ne peuvent pas être dédupliquées par DOI : elles sont traitées par titre normalisé (2 cas dans la SLR). Pour les métadonnées incomplètes, la démarche prévue est de les compléter depuis le texte intégral ou la page de l'éditeur et de coder « not reported » plutôt que de laisser vide.

**Défi 1 : trois références présentes dans au moins 3 bases.**
Non réalisé. La SLR repose sur deux bases (Scopus, WoS) ; avec IEEE Xplore et OpenAlex, quatre bases ont été interrogées pour le lab, mais leurs exports n'ont pas été comparés aux DOI du dataset. Pour le réaliser, il faudrait croiser les DOI des quatre résultats.

**Défi 2 : une référence présente dans OpenAlex mais absente de Scopus et WoS.**
Non réalisé, pour la même raison : la comparaison des DOI n'a pas été faite. Un tel écart peut s'expliquer par le fait qu'OpenAlex indexe aussi des préprints, thèses, dépôts institutionnels et actes de conférence absents de Scopus et WoS, par la sélection de revues propre à chaque base, ou par des métadonnées différentes empêchant la correspondance. Rappel : les préprints et thèses sont exclus par le critère E7 de la SLR.

## 9. Résumé

Collecte de 215 enregistrements dans Scopus et Web of Science le 15/11/2026, fusion en un dataset unique et déduplication exacte (DOI puis titre) donnant 143 enregistrements uniques, avec traçabilité complète (requêtes exactes, filtres, nombres). IEEE Xplore (15 résultats) et OpenAlex (75 works) ont été interrogées le 22/11/2026 pour le lab seulement ; ACM DL n'a pas pu l'être (accès limité). Prochaine étape : le screening titre/abstract (Lab 5).
