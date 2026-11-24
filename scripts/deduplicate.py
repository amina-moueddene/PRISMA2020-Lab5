#!/usr/bin/env python3
"""LAB 5 — Fusion multi-bases et déduplication hiérarchique reproductible (PRISMA 2020).

Étapes implémentées :
  1. Importation des exports bruts (Scopus, Web of Science, OpenAlex, IEEE, ACM).
  2. Harmonisation des schémas (ID, Titre, DOI, Auteurs, Année, Type_Document, Source).
  3. Normalisation non destructive (Titre_Normalise, DOI_Normalise, Premier_Auteur).
  4. Déduplication hiérarchique par priorité :
       - Priorité 1 : DOI normalisé identique (100 % certain)
       - Priorité 2 : Titre normalisé identique + même année (quasi certain)
       - Priorité 3 : Similarité de titre >= 0.80 + mêmes auteurs (cas ambigus -> vérification manuelle)
  5. Exportation :
       - results/dataset_final_screening.csv (corpus propre prêt pour Rayyan / Zotero)
       - results/log_doublons_supprimes.csv   (traçabilité complète de chaque doublon retiré)
       - results/verification_manuelle.csv    (paires ambiguës / conférences vs revues)
       - results/rapport_prisma_dedup.csv     (comptages officiels pour le diagramme PRISMA 2020)

Usage :
  python3 scripts/deduplicate.py
"""
import csv
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
RESULTS_DIR = ROOT / "results"

COLUMN_MAPPINGS = {
    "Scopus": {
        "id": ["EID", "ID"],
        "title": ["Title", "Titre"],
        "doi": ["DOI"],
        "authors": ["Authors", "Auteurs"],
        "year": ["Year", "Année"],
        "doc_type": ["Document Type", "Type"],
    },
    "WoS": {
        "id": ["UT", "ID"],
        "title": ["Article Title", "TI", "Title", "Titre"],
        "doi": ["DI", "DOI"],
        "authors": ["AU", "Authors", "Auteurs"],
        "year": ["PY", "Year", "Année"],
        "doc_type": ["DT", "Document Type"],
    },
    "OpenAlex": {
        "id": ["id", "openalex_id", "ID"],
        "title": ["display_name", "title", "Title"],
        "doi": ["doi", "DOI"],
        "authors": ["authorships", "authors", "Authors"],
        "year": ["publication_year", "year", "Year"],
        "doc_type": ["type", "Document Type"],
    },
    "IEEE": {
        "id": ["Document Identifier", "ID"],
        "title": ["Document Title", "Title"],
        "doi": ["DOI"],
        "authors": ["Authors"],
        "year": ["Publication Year", "Year"],
        "doc_type": ["Document Type"],
    },
    "ACM": {
        "id": ["id", "ID"],
        "title": ["title", "Title"],
        "doi": ["doi", "DOI"],
        "authors": ["author", "Authors"],
        "year": ["year", "Year"],
        "doc_type": ["type", "Document Type"],
    },
}


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def normalize_title(title: str) -> str:
    if not title:
        return ""
    text = strip_accents(str(title).lower())
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_doi(doi: str) -> str:
    if not doi:
        return ""
    text = str(doi).lower().strip()
    text = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", text)
    return text.strip()


def normalize_first_author(authors: str) -> str:
    if not authors:
        return ""
    first = re.split(r"[;,]", str(authors))[0].strip().lower()
    return strip_accents(re.sub(r"[^a-z]", "", first))


def title_similarity(t1: str, t2: str) -> float:
    if not t1 or not t2:
        return 0.0
    return SequenceMatcher(None, t1, t2).ratio()


def pick_column(row: dict, candidates: list[str]) -> str:
    for col in candidates:
        if col in row and row[col] is not None:
            return str(row[col]).strip()
    return ""


def load_and_harmonize(filepath: Path, source_name: str) -> list[dict]:
    mapping = COLUMN_MAPPINGS.get(source_name, COLUMN_MAPPINGS["Scopus"])
    records = []
    with filepath.open("r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            raw_id = pick_column(row, mapping["id"]) or f"{source_name.upper()}-{idx:04d}"
            title = pick_column(row, mapping["title"])
            doi = pick_column(row, mapping["doi"])
            authors = pick_column(row, mapping["authors"])
            year = pick_column(row, mapping["year"])
            doc_type = pick_column(row, mapping["doc_type"]) or "Unknown"
            records.append({
                "ID": f"{source_name}:{raw_id}",
                "Titre": title,
                "DOI": doi,
                "Auteurs": authors,
                "Année": year,
                "Type_Document": doc_type,
                "Source": source_name,
                "Sources_Fusionnees": source_name,
                "Titre_Normalise": normalize_title(title),
                "DOI_Normalise": normalize_doi(doi),
                "Premier_Auteur": normalize_first_author(authors),
                "Est_Doublon": False,
                "Raison_Doublon": "",
                "Doublon_De": "",
            })
    return records


def deduplicate_records(records: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Applique la déduplication hiérarchique et renvoie (uniques, doublons_log, cas_ambigus)."""
    seen_doi: dict[str, dict] = {}
    seen_title_year: dict[tuple[str, str], dict] = {}
    unique_records: list[dict] = []
    duplicates_log: list[dict] = []
    ambiguous_cases: list[dict] = []

    for rec in records:
        doi_n = rec["DOI_Normalise"]
        title_n = rec["Titre_Normalise"]
        year = rec["Année"]

        if doi_n and doi_n in seen_doi:
            master = seen_doi[doi_n]
            rec["Est_Doublon"] = True
            rec["Raison_Doublon"] = "Priorité 1 : DOI identique"
            rec["Doublon_De"] = master["ID"]
            if rec["Source"] not in master["Sources_Fusionnees"].split("; "):
                master["Sources_Fusionnees"] += f"; {rec['Source']}"
            duplicates_log.append(rec)
            continue

        if title_n and (title_n, year) in seen_title_year:
            master = seen_title_year[(title_n, year)]
            if doi_n and master["DOI_Normalise"] and doi_n != master["DOI_Normalise"]:
                ambiguous_cases.append({
                    "ID_1": master["ID"],
                    "Titre_1": master["Titre"],
                    "DOI_1": master["DOI"],
                    "Annee_1": master["Année"],
                    "Type_1": master["Type_Document"],
                    "Source_1": master["Source"],
                    "ID_2": rec["ID"],
                    "Titre_2": rec["Titre"],
                    "DOI_2": rec["DOI"],
                    "Annee_2": rec["Année"],
                    "Type_2": rec["Type_Document"],
                    "Source_2": rec["Source"],
                    "Similarite": "1.000",
                    "Motif": "Même titre/année mais DOI distincts",
                    "Decision": "À vérifier manuellement",
                })
            else:
                rec["Est_Doublon"] = True
                rec["Raison_Doublon"] = "Priorité 2 : Titre normalisé + Année identiques"
                rec["Doublon_De"] = master["ID"]
                if rec["Source"] not in master["Sources_Fusionnees"].split("; "):
                    master["Sources_Fusionnees"] += f"; {rec['Source']}"
                duplicates_log.append(rec)
                continue

        if doi_n:
            seen_doi[doi_n] = rec
        if title_n:
            seen_title_year[(title_n, year)] = rec
        unique_records.append(rec)

    for i in range(len(unique_records)):
        for j in range(i + 1, len(unique_records)):
            r1, r2 = unique_records[i], unique_records[j]
            if r1["Premier_Auteur"] and r1["Premier_Auteur"] == r2["Premier_Auteur"]:
                sim = title_similarity(r1["Titre_Normalise"], r2["Titre_Normalise"])
                if sim >= 0.80:
                    ambiguous_cases.append({
                        "ID_1": r1["ID"],
                        "Titre_1": r1["Titre"],
                        "DOI_1": r1["DOI"],
                        "Annee_1": r1["Année"],
                        "Type_1": r1["Type_Document"],
                        "Source_1": r1["Source"],
                        "ID_2": r2["ID"],
                        "Titre_2": r2["Titre"],
                        "DOI_2": r2["DOI"],
                        "Annee_2": r2["Année"],
                        "Type_2": r2["Type_Document"],
                        "Source_2": r2["Source"],
                        "Similarite": f"{sim:.3f}",
                        "Motif": "Titre similaire + même premier auteur (conférence vs revue ?)",
                        "Decision": "Publications distinctes probables (DOI différents)" if (r1["DOI_Normalise"] and r2["DOI_Normalise"] and r1["DOI_Normalise"] != r2["DOI_Normalise"]) else "À vérifier manuellement",
                    })

    return unique_records, duplicates_log, ambiguous_cases


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    sources = [
        ("Scopus", RAW_DIR / "scopus_results.csv"),
        ("WoS", RAW_DIR / "wos_results.csv"),
        ("OpenAlex", RAW_DIR / "openalex_results.csv"),
    ]

    all_records = []
    counts_by_source = {}
    for src_name, path in sources:
        if path.exists():
            recs = load_and_harmonize(path, src_name)
            counts_by_source[src_name] = len(recs)
            all_records.extend(recs)

    unique_records, duplicates_log, ambiguous_cases = deduplicate_records(all_records)

    final_cols = ["ID", "Titre", "DOI", "Auteurs", "Année", "Type_Document", "Sources_Fusionnees"]
    with (RESULTS_DIR / "dataset_final_screening.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=final_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(unique_records)

    dup_cols = ["ID", "Titre", "DOI", "Année", "Source", "Raison_Doublon", "Doublon_De"]
    with (RESULTS_DIR / "log_doublons_supprimes.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=dup_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(duplicates_log)

    amb_cols = [
        "ID_1", "Titre_1", "DOI_1", "Annee_1", "Type_1", "Source_1",
        "ID_2", "Titre_2", "DOI_2", "Annee_2", "Type_2", "Source_2",
        "Similarite", "Motif", "Decision"
    ]
    with (RESULTS_DIR / "verification_manuelle.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=amb_cols)
        w.writeheader()
        w.writerows(ambiguous_cases)

    with (RESULTS_DIR / "rapport_prisma_dedup.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Source", "Importes", "Doublons_supprimes", "Uniques_conserves"])
        for src_name, n_imp in counts_by_source.items():
            n_dup = sum(1 for d in duplicates_log if d["Source"] == src_name)
            w.writerow([src_name, n_imp, n_dup, n_imp - n_dup])
        w.writerow(["Total", len(all_records), len(duplicates_log), len(unique_records)])

    print(f"Total brut importé      : {len(all_records)}")
    print(f"Doublons supprimés      : {len(duplicates_log)}")
    print(f"Références uniques      : {len(unique_records)}")
    print(f"Cas ambigus à vérifier  : {len(ambiguous_cases)}")


if __name__ == "__main__":
    main()
