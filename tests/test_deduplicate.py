"""Tests unitaires pour le pipeline de fusion et déduplication (LAB 5)."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("deduplicate", ROOT / "scripts" / "deduplicate.py")
dd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dd)


class TestNormalisationLab5(unittest.TestCase):
    def test_normalize_doi_prefixes(self):
        self.assertEqual(dd.normalize_doi("https://doi.org/10.123/ABC"), "10.123/abc")
        self.assertEqual(dd.normalize_doi("http://dx.doi.org/10.123/ABC"), "10.123/abc")
        self.assertEqual(dd.normalize_doi("doi: 10.123/ABC "), "10.123/abc")
        self.assertEqual(dd.normalize_doi(""), "")

    def test_normalize_title_punctuation_and_accents(self):
        t1 = dd.normalize_title("Deep Learning: A Survey on Olea europaea!")
        t2 = dd.normalize_title("  deep   learning a survey on olea europaea ")
        self.assertEqual(t1, t2)


class TestDeduplicationHierarchy(unittest.TestCase):
    def test_defi1_android_benchmark(self):
        """Vérifie le cas d'école du Défi 1 (R1 à R4)."""
        raw = [
            {"ID": "R1", "Titre": "Deep Learning for Android", "DOI": "10.123/abc", "Auteurs": "Smith, J.", "Année": "2023", "Type_Document": "Article", "Source": "Scopus"},
            {"ID": "R2", "Titre": "Deep Learning for Android", "DOI": "10.123/abc", "Auteurs": "Smith, John", "Année": "2023", "Type_Document": "Article", "Source": "WoS"},
            {"ID": "R3", "Titre": "Deep Learning for Android Security", "DOI": "10.456/def", "Auteurs": "Smith, J.", "Année": "2023", "Type_Document": "Article", "Source": "IEEE"},
            {"ID": "R4", "Titre": "Deep Learning for Android", "DOI": "10.789/ghi", "Auteurs": "Doe, A.", "Année": "2022", "Type_Document": "Article", "Source": "ACM"},
        ]
        records = []
        for r in raw:
            rec = dict(r)
            rec["Sources_Fusionnees"] = r["Source"]
            rec["Titre_Normalise"] = dd.normalize_title(r["Titre"])
            rec["DOI_Normalise"] = dd.normalize_doi(r["DOI"])
            rec["Premier_Auteur"] = dd.normalize_first_author(r["Auteurs"])
            rec["Est_Doublon"] = False
            rec["Raison_Doublon"] = ""
            rec["Doublon_De"] = ""
            records.append(rec)

        uniques, dups, ambiguous = dd.deduplicate_records(records)
        self.assertEqual(len(uniques), 3)
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0]["ID"], "R2")
        self.assertIn("WoS", uniques[0]["Sources_Fusionnees"])
        self.assertEqual(len(ambiguous), 1)
        self.assertEqual((ambiguous[0]["ID_1"], ambiguous[0]["ID_2"]), ("R1", "R3"))

    def test_end_to_end_slr_pipeline(self):
        dd.main()
        screening_file = ROOT / "results" / "dataset_final_screening.csv"
        self.assertTrue(screening_file.exists())


if __name__ == "__main__":
    unittest.main()
