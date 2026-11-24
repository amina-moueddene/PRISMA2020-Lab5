#!/usr/bin/env python3
"""Lab 5 - Fusion des résultats Scopus + Web of Science et suppression des doublons.

Revue : Machine learning and remote sensing for disease and stress detection in olive
Recherche du 15/11/2026. Entrées (non publiées, voir .gitignore) :
  raw/scopus_export_2026-11-15.csv   export CSV Scopus (118 notices)
  raw/wos_savedrecs_2026-11-15.bib   export BibTeX Web of Science (97 notices)
Décisions manuelles (entrée relue par le chercheur) :
  manual/manual_decisions.csv

Étapes (numérotées comme le lab) :
  2  import et exploration           -> output/00_exploration.txt
  3  harmonisation des métadonnées   -> schéma commun
  4  normalisation titres / DOI / auteurs
  5  priorité 1 : DOI identique
  6  priorité 2 : titre normalisé identique
  7  priorité 3 : titre similaire (difflib) + même premier auteur
  8  cas ambigus                      -> output/02_verification_manuelle.csv
  9  doublon réel / publication distincte (décisions manuelles)
  10 suppression + provenance        -> output/03_log_doublons_supprimes.csv
  11 traçabilité PRISMA              -> output/04_rapport_prisma.csv
  12 dataset final                   -> output/05_dataset_final_screening*.csv
  +  contrôle par rapport à la SLR   -> output/06_controle_vs_SLR.txt

Usage : python scripts/deduplicate.py      (pandas requis : pip install pandas)
"""
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
OUT = ROOT / "output"
MANUAL = ROOT / "manual" / "manual_decisions.csv"
SCOPUS = RAW / "scopus_export_2026-11-15.csv"
WOS = RAW / "wos_savedrecs_2026-11-15.bib"
LEDGER = ROOT / "data" / "Screening_ledger_olive_PRISMA2020.csv"  # facultatif, pour le contrôle

SIM_AUTO_REVIEW = 0.90  # titre très similaire -> vérification manuelle
SIM_LOW = 0.80          # titre assez similaire + même premier auteur -> vérification manuelle

COLS = ["ID", "Source", "ID_base", "Titre", "DOI", "Auteurs", "Annee", "Type_document",
        "Revue_ou_conference", "Volume", "Pages", "ISBN", "Langue", "Resume", "Mots_cles"]

# familles de types de document, pour comparer Scopus et WoS qui les nomment différemment
FAMILY = {"article": "article", "review": "article", "editorial": "article", "letter": "article",
          "conference paper": "conference", "proceedings paper": "conference", "conference review": "conference",
          "book": "livre", "book chapter": "livre"}


# ---------------------------------------------------------------- étape 2 : import
def read_scopus(path):
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    out = pd.DataFrame({
        "Source": "Scopus",
        "ID_base": df["EID"],
        "Titre": df["Title"],
        "DOI": df["DOI"],
        "Auteurs": df["Authors"],
        "Annee": df["Year"],
        "Type_document": df["Document Type"],
        "Revue_ou_conference": df["Source title"],
        "Volume": df["Volume"],
        "Pages": (df["Page start"] + "-" + df["Page end"]).str.strip("-"),
        "ISBN": df["ISBN"],
        "Langue": df["Language of Original Document"],
        "Resume": df["Abstract"],
        "Mots_cles": (df["Author Keywords"] + "; " + df["Index Keywords"]).str.strip("; "),
    })
    return out


def _bib_fields(entry):
    """Lit les champs Key = {valeur} d'une notice BibTeX, accolades imbriquées comprises."""
    fields, i, n = {}, 0, len(entry)
    for m in re.finditer(r"\n\s*([A-Za-z][A-Za-z0-9-]*)\s*=\s*\{", entry):
        if m.start() < i:
            continue
        key, j, depth = m.group(1), m.end(), 1
        while j < n and depth:
            if entry[j] == "{":
                depth += 1
            elif entry[j] == "}":
                depth -= 1
            j += 1
        fields[key.lower()] = entry[m.end():j - 1]
        i = j
    return fields


def _bib_clean(s):
    s = s.replace("\\&", "&").replace("\\%", "%").replace("\\_", "_")
    s = re.sub(r"[{}]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def read_wos(path):
    text = path.read_text(encoding="utf-8-sig")
    rows = []
    for entry in re.split(r"\n(?=@\w+\s*\{)", "\n" + text):
        m = re.match(r"\s*@(\w+)\s*\{\s*([^,]+),", entry)
        if not m:
            continue
        f = {k: _bib_clean(v) for k, v in _bib_fields(entry).items()}
        bibtype = m.group(1).lower()
        rows.append({
            "Source": "WoS",
            "ID_base": m.group(2).strip(),
            "Titre": f.get("title", ""),
            "DOI": f.get("doi", ""),
            "Auteurs": f.get("author", ""),
            "Annee": f.get("year", ""),
            "Type_document": f.get("type", "") or {"article": "Article", "inproceedings": "Proceedings Paper"}.get(bibtype, bibtype),
            "Revue_ou_conference": f.get("journal", "") or f.get("booktitle", ""),
            "Volume": f.get("volume", ""),
            "Pages": f.get("pages", "").replace("--", "-"),
            "ISBN": f.get("isbn", ""),
            "Langue": f.get("language", ""),
            "Resume": f.get("abstract", ""),
            "Mots_cles": "; ".join(x for x in (f.get("keywords", ""), f.get("keywords-plus", "")) if x),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- étape 4 : normalisation
def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalize_title(t):
    t = strip_accents(str(t)).lower()
    t = re.sub(r"<[^>]+>", " ", t)            # balises éventuelles (<i>, <sub>)
    t = re.sub(r"[^a-z0-9]+", " ", t)          # ponctuation, tirets, symboles
    return re.sub(r"\s+", " ", t).strip()


def normalize_doi(d):
    d = str(d).strip().lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    d = re.sub(r"^doi:\s*", "", d)
    return d.rstrip(".;, ")


def surnames(authors, source):
    """Liste des noms de famille normalisés (Scopus : 'Nom I.; ...' ; WoS : 'Nom, Prénom and ...')."""
    a = str(authors)
    if not a:
        return []
    if source == "WoS":
        parts = [p.split(",")[0] for p in re.split(r"\s+and\s+", a)]
    else:
        parts = [re.sub(r"(\s+[A-Z][a-z]?\.(-?[A-Z]\.)*)+$", "", p.strip()) for p in a.split(";")]
    return [re.sub(r"[^a-z]", "", strip_accents(p).lower()) for p in parts if p.strip()]


# ---------------------------------------------------------------- regroupement (union-find)
class Groups:
    def __init__(self, ids):
        self.parent = {i: i for i in ids}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra
            return True
        return False


def main():
    OUT.mkdir(exist_ok=True)
    for p in (SCOPUS, WOS):
        if not p.exists():
            sys.exit(f"Fichier manquant : {p}")

    # 2. import
    sco, wos = read_scopus(SCOPUS), read_wos(WOS)
    sco["ID"] = [f"SCO-{i + 1:03d}" for i in range(len(sco))]
    wos["ID"] = [f"WOS-{i + 1:03d}" for i in range(len(wos))]
    df = pd.concat([sco, wos], ignore_index=True)[COLS]

    with (OUT / "00_exploration.txt").open("w", encoding="utf-8") as f:
        for name, d in (("Scopus", sco), ("WoS", wos)):
            f.write(f"== {name} : {len(d)} notices\n")
            for c in ("Titre", "DOI", "Auteurs", "Annee", "Resume"):
                f.write(f"  {c:<8} vide : {(d[c].str.strip() == '').sum()}\n")
            f.write("  Types : " + "; ".join(f"{k} {v}" for k, v in d["Type_document"].value_counts().items()) + "\n")
        f.write(f"== Total brut : {len(df)}\n")

    # 4. normalisation (colonnes de travail ; les originales sont conservées)
    df["Titre_norm"] = df["Titre"].map(normalize_title)
    df["DOI_norm"] = df["DOI"].map(normalize_doi)
    df["Auteurs_norm"] = [surnames(a, s) for a, s in zip(df["Auteurs"], df["Source"])]
    df["Premier_auteur"] = df["Auteurs_norm"].map(lambda x: x[0] if x else "")
    df["Annee"] = df["Annee"].str.extract(r"(\d{4})", expand=False).fillna("")
    df["Famille_type"] = df["Type_document"].str.lower().map(FAMILY).fillna("autre")
    df["Volume_norm"] = df["Volume"].str.extract(r"(\d+)", expand=False).fillna("")
    df.drop(columns=["Resume", "Mots_cles", "Auteurs_norm", "Famille_type", "Volume_norm"]).to_csv(
        OUT / "01_references_fusionnees_harmonisees.csv", index=False, encoding="utf-8-sig")

    g = Groups(df["ID"])
    rec = df.set_index("ID")
    links = []  # (id_a, id_b, critère)

    # 5. priorité 1 : DOI identique
    for doi, grp in df[df["DOI_norm"] != ""].groupby("DOI_norm"):
        ids = list(grp["ID"])
        for other in ids[1:]:
            if g.union(ids[0], other):
                links.append((ids[0], other, "P1 DOI identique"))

    # 6. priorité 2 : titre normalisé identique.
    # Fusion automatique seulement si rien ne contredit le doublon : DOI non contradictoires,
    # même famille de document, année à +/- 1 an, volumes identiques s'ils sont renseignés.
    # Sinon -> vérification manuelle (étape 9 : publication distincte possible).
    review = []  # cas à vérifier manuellement
    seen_pairs = set()

    def contradictions(a, b):
        why = []
        da, db = rec.at[a, "DOI_norm"], rec.at[b, "DOI_norm"]
        if da and db and da != db:
            why.append("DOI différents")
        if rec.at[a, "Famille_type"] != rec.at[b, "Famille_type"]:
            why.append(f"types différents ({rec.at[a, 'Type_document']} / {rec.at[b, 'Type_document']})")
        ya, yb = rec.at[a, "Annee"], rec.at[b, "Annee"]
        if ya and yb and abs(int(ya) - int(yb)) > 1:
            why.append(f"années différentes ({ya} / {yb})")
        va, vb = rec.at[a, "Volume_norm"], rec.at[b, "Volume_norm"]
        if va and vb and va != vb and rec.at[a, "Source"] == rec.at[b, "Source"]:
            why.append(f"volumes différents ({rec.at[a, 'Volume']} / {rec.at[b, 'Volume']})")
        return why
    for t, grp in df[df["Titre_norm"] != ""].groupby("Titre_norm"):
        ids = list(grp["ID"])
        for a, b in combinations(ids, 2):
            if g.find(a) == g.find(b):
                continue
            why = contradictions(a, b)
            if why:
                review.append((a, b, 1.0, "Titre identique mais " + ", ".join(why)))
                seen_pairs.add(frozenset((a, b)))
            elif g.union(a, b):
                links.append((a, b, "P2 Titre normalisé identique"))

    # 7. priorité 3 : titre similaire + même premier auteur ; et même titre/année sans auteur commun
    reps = {}
    for i in df["ID"]:
        reps.setdefault(g.find(i), i)
    rep_ids = list(reps.values())
    for a, b in combinations(rep_ids, 2):
        if frozenset((a, b)) in seen_pairs:
            continue
        ta, tb = rec.at[a, "Titre_norm"], rec.at[b, "Titre_norm"]
        if not ta or not tb:
            continue
        # filtre rapide sur la longueur avant le calcul de similarité
        if min(len(ta), len(tb)) / max(len(ta), len(tb)) < SIM_LOW:
            continue
        sim = SequenceMatcher(None, ta, tb).ratio()
        if sim < SIM_LOW:
            continue
        same_first = rec.at[a, "Premier_auteur"] and rec.at[a, "Premier_auteur"] == rec.at[b, "Premier_auteur"]
        ya, yb = rec.at[a, "Annee"], rec.at[b, "Annee"]
        close_year = ya and yb and abs(int(ya) - int(yb)) <= 1
        if sim >= SIM_AUTO_REVIEW and (same_first or close_year):
            review.append((a, b, round(sim, 3), "Titre très similaire" + (" + même premier auteur" if same_first else " + année proche")))
        elif same_first:
            review.append((a, b, round(sim, 3), "Titre similaire + même premier auteur"))

    # 8. tableau de vérification manuelle
    rows = []
    for a, b, sim, why in review:
        rows.append({
            "ID_A": a, "ID_B": b, "Similarite_titre": sim, "Motif": why,
            "Titre_A": rec.at[a, "Titre"], "Titre_B": rec.at[b, "Titre"],
            "DOI_A": rec.at[a, "DOI"], "DOI_B": rec.at[b, "DOI"],
            "Auteurs_A": rec.at[a, "Auteurs"][:120], "Auteurs_B": rec.at[b, "Auteurs"][:120],
            "Annee_A": rec.at[a, "Annee"], "Annee_B": rec.at[b, "Annee"],
            "Type_A": rec.at[a, "Type_document"], "Type_B": rec.at[b, "Type_document"],
            "Volume_A": rec.at[a, "Volume"], "Volume_B": rec.at[b, "Volume"],
            "Pages_A": rec.at[a, "Pages"], "Pages_B": rec.at[b, "Pages"],
            "ISBN_A": rec.at[a, "ISBN"], "ISBN_B": rec.at[b, "ISBN"],
            "Revue_A": rec.at[a, "Revue_ou_conference"], "Revue_B": rec.at[b, "Revue_ou_conference"],
            "Source_A": rec.at[a, "Source"], "Source_B": rec.at[b, "Source"],
        })
    man = pd.DataFrame(rows)
    if MANUAL.exists() and len(man):
        dec = pd.read_csv(MANUAL, dtype=str).fillna("")
        key = {frozenset((r.ID_A, r.ID_B)): (r.Decision, r.Justification) for r in dec.itertuples()}
        man["Decision"] = [key.get(frozenset((a, b)), ("À vérifier", ""))[0] for a, b in zip(man.ID_A, man.ID_B)]
        man["Justification"] = [key.get(frozenset((a, b)), ("", ""))[1] for a, b in zip(man.ID_A, man.ID_B)]
    man.to_csv(OUT / "02_verification_manuelle.csv", index=False, encoding="utf-8-sig")

    # 9. application des décisions manuelles (Doublon / Distinct)
    decisions = pd.read_csv(MANUAL, dtype=str).fillna("") if MANUAL.exists() else pd.DataFrame(columns=["ID_A", "ID_B", "Decision"])
    decided = {frozenset((r.ID_A, r.ID_B)): r.Decision for r in decisions.itertuples()}
    pending = [r for r in rows if frozenset((r["ID_A"], r["ID_B"])) not in decided]
    for r in decisions.itertuples():
        if r.Decision.strip().lower() == "doublon" and g.union(r.ID_A, r.ID_B):
            links.append((r.ID_A, r.ID_B, "P4 Vérification manuelle"))

    # 10. choix de la notice conservée dans chaque groupe et journal des suppressions
    df["Groupe"] = df["ID"].map(g.find)
    filled = ["DOI", "Auteurs", "Annee", "Resume", "Mots_cles", "Revue_ou_conference", "Langue"]
    df["Completude"] = (df[filled].apply(lambda c: c.str.strip() != "")).sum(axis=1)
    df["Priorite_source"] = df["Source"].map({"Scopus": 0, "WoS": 1})
    df = df.sort_values(["Groupe", "Completude", "Priorite_source", "ID"], ascending=[True, False, True, True])
    keep = df.drop_duplicates("Groupe", keep="first").set_index("Groupe")["ID"]
    df["ID_conserve"] = df["Groupe"].map(keep)
    df["Est_doublon"] = df["ID"] != df["ID_conserve"]

    reason = {}
    for a, b, why in links:
        reason.setdefault(b, why)
        reason.setdefault(a, why)
    sources = df.groupby("Groupe")["Source"].agg(lambda s: " + ".join(sorted(set(s))))
    members = df.groupby("Groupe")["ID"].agg(lambda s: "; ".join(sorted(s)))

    dup = df[df["Est_doublon"]].copy()
    dup["Raison"] = dup["ID"].map(reason)
    dup["Doublon_de"] = dup["ID_conserve"]
    dup[["ID", "Source", "ID_base", "Titre", "DOI", "Annee", "Type_document", "Raison", "Doublon_de"]] \
        .sort_values("ID").to_csv(OUT / "03_log_doublons_supprimes.csv", index=False, encoding="utf-8-sig")

    clean = df[~df["Est_doublon"]].copy()
    clean["Bases"] = clean["Groupe"].map(sources)
    clean["IDs_fusionnes"] = clean["Groupe"].map(members)
    clean = clean.sort_values(["Annee", "Titre"]).reset_index(drop=True)
    clean.insert(0, "ID_unique", [f"U{i + 1:03d}" for i in range(len(clean))])

    # contrôles d'intégrité
    d_left = clean[clean["DOI_norm"] != ""]["DOI_norm"].duplicated().sum()
    t_left = clean[clean["Titre_norm"] != ""]["Titre_norm"].duplicated().sum()

    # 11. rapport PRISMA
    n_raw = len(df)
    by_reason = dup["Raison"].value_counts()
    rep = []
    for s in ("Scopus", "WoS"):
        rep.append({
            "Base": s,
            "Importees": int((df["Source"] == s).sum()),
            "Doublons_supprimes_dans_cette_base": int((dup["Source"] == s).sum()),
            "Notices_conservees_de_cette_base": int((clean["Source"] == s).sum()),
            "Uniques_presentes_dans_cette_base": int(clean["Bases"].str.contains(s).sum()),
            "Uniques_seulement_dans_cette_base": int((clean["Bases"] == s).sum()),
        })
    rep.append({"Base": "Total", "Importees": n_raw, "Doublons_supprimes_dans_cette_base": len(dup),
                "Notices_conservees_de_cette_base": len(clean),
                "Uniques_presentes_dans_cette_base": len(clean),
                "Uniques_seulement_dans_cette_base": int((clean["Bases"] == "Scopus + WoS").sum())})
    pd.DataFrame(rep).to_csv(OUT / "04_rapport_prisma.csv", index=False, encoding="utf-8-sig")

    # 12. dataset final pour le screening
    final_cols = ["ID_unique", "Titre", "Auteurs", "Annee", "DOI", "Type_document", "Revue_ou_conference",
                  "Langue", "Bases", "IDs_fusionnes", "ID"]
    clean[final_cols + ["Resume", "Mots_cles"]].rename(columns={"ID": "ID_notice_conservee"}).to_csv(
        OUT / "05_dataset_final_screening.csv", index=False, encoding="utf-8-sig")
    clean[final_cols].rename(columns={"ID": "ID_notice_conservee"}).to_csv(
        OUT / "05_dataset_final_screening_public.csv", index=False, encoding="utf-8-sig")

    # export RIS (import direct dans Rayyan, Zotero, EndNote)
    ris_type = {"article": "JOUR", "conference": "CONF", "livre": "BOOK"}
    with (OUT / "05_dataset_final_screening.ris").open("w", encoding="utf-8") as f:
        for r in clean.itertuples():
            f.write(f"TY  - {ris_type.get(r.Famille_type, 'GEN')}\n")
            f.write(f"ID  - {r.ID_unique}\n")
            f.write(f"TI  - {r.Titre}\n")
            sep = r" and " if r.Source == "WoS" else ";"
            for au in [x.strip() for x in re.split(sep, r.Auteurs) if x.strip()]:
                f.write(f"AU  - {au}\n")
            for tag, val in (("PY", r.Annee), ("T2", r.Revue_ou_conference), ("VL", r.Volume),
                             ("DO", r.DOI), ("AB", r.Resume), ("DB", r.Bases), ("N1", "Notices fusionnées : " + r.IDs_fusionnes)):
                if str(val).strip():
                    f.write(f"{tag}  - {val}\n")
            for kw in [k.strip() for k in str(r.Mots_cles).split(";") if k.strip()]:
                f.write(f"KW  - {kw}\n")
            f.write("ER  - \n\n")

    # contrôle par rapport à la SLR (si le tableau de tri est présent)
    lines = [f"Notices importées : {n_raw} (Scopus {rep[0]['Importees']}, WoS {rep[1]['Importees']})",
             f"Doublons supprimés : {len(dup)}"]
    lines += [f"  - {k} : {v}" for k, v in by_reason.items()]
    lines += [f"Références uniques : {len(clean)}",
              f"  dans les deux bases : {rep[2]['Uniques_seulement_dans_cette_base']} ; Scopus seul : {rep[0]['Uniques_seulement_dans_cette_base']} ; WoS seul : {rep[1]['Uniques_seulement_dans_cette_base']}",
              f"Doublons internes à une base : Scopus {int((dup['Source'] == 'Scopus').sum() - ((dup['Source'] == 'Scopus') & dup['Doublon_de'].str.startswith('WOS')).sum())}, "
              f"WoS {int((dup['Source'] == 'WoS').sum() - ((dup['Source'] == 'WoS') & dup['Doublon_de'].str.startswith('SCO')).sum())}",
              f"Paires à vérifier manuellement : {len(rows)} (dont sans décision : {len(pending)})",
              f"DOI dupliqués restants : {d_left} ; titres normalisés dupliqués restants : {t_left}"]
    if LEDGER.exists():
        # appariement un-à-un : DOI, puis titre normalisé, puis titre très similaire (>= 0.95)
        led = pd.read_csv(LEDGER, encoding="utf-8-sig", dtype=str).fillna("")
        led["d"], led["t"] = led["doi"].map(normalize_doi), led["title"].map(normalize_title)
        free = set(led.index)
        match = {}
        gdois = df.groupby("Groupe")["DOI_norm"].agg(lambda x: set(x) - {""})
        for crit in ("doi", "titre", "flou"):
            for r in clean.itertuples():
                if r.ID_unique in match:
                    continue
                cand = []
                for j in free:
                    lj = led.loc[j]
                    if crit == "doi" and lj["d"] and lj["d"] in gdois[r.Groupe]:
                        cand.append(j)
                    elif crit == "titre" and r.Titre_norm == lj["t"] and not (r.DOI_norm and lj["d"]):
                        cand.append(j)
                    elif crit == "flou" and SequenceMatcher(None, r.Titre_norm, lj["t"]).ratio() >= 0.95 and not (r.DOI_norm and lj["d"]):
                        cand.append(j)
                if cand:
                    match[r.ID_unique] = (cand[0], crit)
                    free.discard(cand[0])
        miss = clean[~clean["ID_unique"].isin(match)]
        lines += [f"Tableau de tri de la SLR : {len(led)} lignes ; références uniques appariées une à une : {len(match)}/{len(clean)}"
                  f" (DOI {sum(c == 'doi' for _, c in match.values())}, titre {sum(c == 'titre' for _, c in match.values())},"
                  f" titre très similaire {sum(c == 'flou' for _, c in match.values())})"]
        for r in miss.itertuples():
            lines += [f"  Absente du tableau de tri de la SLR : {r.ID_unique} ({r.IDs_fusionnes}, {r.Annee}, {r.Type_document}) {r.Titre[:80]}"]
        if free:
            lines += [f"  Lignes du tableau de tri sans correspondance : {len(free)}"]
    (OUT / "06_controle_vs_SLR.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    if pending:
        print(f"\nATTENTION : {len(pending)} paire(s) sans décision dans manual/manual_decisions.csv")


if __name__ == "__main__":
    main()
