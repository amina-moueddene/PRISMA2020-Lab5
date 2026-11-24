"""Outils communs aux tests : charge le script et fabrique de petits exports fictifs."""
import csv
import importlib.util
import io
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_module():
    spec = importlib.util.spec_from_file_location("deduplicate", ROOT / "scripts" / "deduplicate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rows(path):
    return list(csv.DictReader(io.StringIO(Path(path).read_text(encoding="utf-8-sig"))))


SCOPUS_COLS = ["Authors", "Title", "Year", "Source title", "Volume", "Page start", "Page end", "DOI", "Abstract",
               "Author Keywords", "Index Keywords", "ISBN", "Language of Original Document", "Document Type", "EID"]


def scopus_row(title, doi, authors, year, dtype="Article", volume="", isbn="", eid="2-s2.0-1"):
    return {"Authors": authors, "Title": title, "Year": year, "Source title": "Revue test", "Volume": volume,
            "Page start": "", "Page end": "", "DOI": doi, "Abstract": "Résumé.", "Author Keywords": "kw",
            "Index Keywords": "", "ISBN": isbn, "Language of Original Document": "English",
            "Document Type": dtype, "EID": eid}


def wos_entry(key, title, doi, authors, year, kind="article"):
    doi_line = f"DOI = {{{doi}}},\n" if doi else ""
    return (f"@{kind}{{ WOS:{key},\nAuthor = {{{authors}}},\nTitle = {{{title}}},\nJournal = {{REVUE TEST}},\n"
            f"Year = {{{year}}},\nAbstract = {{Résumé {{imbriqué}} sur\n   deux lignes.}},\n{doi_line}Unique-ID = {{WOS:{key}}},\n}}\n")


class Workspace:
    """Dossier temporaire avec raw/, manual/, output/ et redirection des chemins du script."""

    def __init__(self, mod, scopus_rows, wos_entries, decisions=None):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        (t / "raw").mkdir()
        (t / "manual").mkdir()
        with (t / "raw" / "scopus.csv").open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=SCOPUS_COLS)
            w.writeheader()
            for i, r in enumerate(scopus_rows):
                r = dict(r)
                r["EID"] = f"2-s2.0-{i + 1}"
                w.writerow(r)
        (t / "raw" / "wos.bib").write_text("﻿\n" + "\n".join(wos_entries), encoding="utf-8")
        with (t / "manual" / "decisions.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ID_A", "ID_B", "Decision", "Justification"])
            for d in decisions or []:
                w.writerow(d)
        mod.SCOPUS, mod.WOS = t / "raw" / "scopus.csv", t / "raw" / "wos.bib"
        mod.OUT, mod.MANUAL, mod.LEDGER = t / "output", t / "manual" / "decisions.csv", t / "absent.csv"
        self.path = t

    def out(self, name):
        return rows(self.path / "output" / name)

    def close(self):
        self.tmp.cleanup()
