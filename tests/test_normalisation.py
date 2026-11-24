"""Étape 4 : normalisation des titres, des DOI et des auteurs ; lecture du BibTeX WoS (étape 2)."""
import tempfile
import unittest
from pathlib import Path

from tests.helpers import load_module, wos_entry

dd = load_module()


class TestNormalisation(unittest.TestCase):
    def test_titre_casse_ponctuation_accents(self):
        self.assertEqual(dd.normalize_title("Spatio-Temporal Assessment: Olive Groves!"),
                         dd.normalize_title("spatio temporal assessment olive groves"))
        self.assertEqual(dd.normalize_title("Castrignanò"), "castrignano")

    def test_titre_espace_insecable_et_tiret_long(self):
        self.assertEqual(dd.normalize_title("Using the Cloud-Edge Continuum"), dd.normalize_title("Using the Cloud-Edge Continuum"))
        self.assertEqual(dd.normalize_title("TEBAKA – A platform"), dd.normalize_title("TEBAKA - A platform"))

    def test_titre_vide(self):
        self.assertEqual(dd.normalize_title(""), "")

    def test_doi_prefixes(self):
        for raw in ("https://doi.org/10.3390/RS70505584", "http://dx.doi.org/10.3390/rs70505584",
                    "doi: 10.3390/rs70505584", " 10.3390/rs70505584. "):
            self.assertEqual(dd.normalize_doi(raw), "10.3390/rs70505584", raw)

    def test_noms_auteurs_selon_la_base(self):
        self.assertEqual(dd.surnames("Calderón R.; Lucena C.; Zarco-Tejada P.J.", "Scopus"), ["calderon", "lucena", "zarcotejada"])
        self.assertEqual(dd.surnames("Calderon, Rocio and Lucena, Carlos", "WoS"), ["calderon", "lucena"])
        self.assertEqual(dd.surnames("", "Scopus"), [])

    def test_lecture_bibtex_wos(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "w.bib"
            p.write_text("﻿\n" + wos_entry("1", "Un titre {avec} accolades", "10.1/A", "Doe, Ann and Roe, Bob", "2023")
                         + wos_entry("2", "Actes", "", "X, Y", "2024", kind="inproceedings"), encoding="utf-8")
            df = dd.read_wos(p)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.loc[0, "Titre"], "Un titre avec accolades")
        self.assertEqual(df.loc[0, "Resume"], "Résumé imbriqué sur deux lignes.")
        self.assertEqual(df.loc[1, "Type_document"], "Proceedings Paper")
        self.assertEqual(df.loc[1, "DOI"], "")

    def test_groupes_union_find(self):
        g = dd.Groups(["a", "b", "c", "d"])
        g.union("a", "b")
        g.union("b", "c")
        self.assertEqual(g.find("c"), g.find("a"))
        self.assertNotEqual(g.find("d"), g.find("a"))


if __name__ == "__main__":
    unittest.main()
