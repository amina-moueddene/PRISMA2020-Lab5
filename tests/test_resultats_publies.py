"""Cohérence des résultats publiés dans output/ (étapes 10 à 12). Ne demande pas les exports bruts."""
import unittest
from collections import Counter

from tests.helpers import ROOT, rows

OUT = ROOT / "output"


class TestResultatsPublies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.all = rows(OUT / "01_references_fusionnees_harmonisees.csv")
        cls.log = rows(OUT / "03_log_doublons_supprimes.csv")
        cls.final = rows(OUT / "05_dataset_final_screening_public.csv")
        cls.rep = {r["Base"]: r for r in rows(OUT / "04_rapport_prisma.csv")}
        cls.man = rows(OUT / "02_verification_manuelle.csv")
        cls.dec = rows(ROOT / "manual" / "manual_decisions.csv")

    def test_chiffres_prisma(self):
        self.assertEqual(len(self.all), 215)
        self.assertEqual(Counter(r["Source"] for r in self.all), Counter({"Scopus": 118, "WoS": 97}))
        self.assertEqual(len(self.log), 71)
        self.assertEqual(len(self.final), 144)
        self.assertEqual(len(self.all) - len(self.log), len(self.final))
        self.assertEqual(self.rep["Total"]["Notices_conservees_de_cette_base"], "144")

    def test_chaque_notice_est_conservee_ou_journalisee(self):
        kept = {i for r in self.final for i in r["IDs_fusionnes"].split("; ")}
        self.assertEqual(kept, {r["ID"] for r in self.all})
        self.assertTrue({r["ID"] for r in self.log}.isdisjoint({r["ID_notice_conservee"] for r in self.final}))

    def test_raisons_des_suppressions(self):
        self.assertEqual(Counter(r["Raison"] for r in self.log), Counter({"P1 DOI identique": 70, "P4 Vérification manuelle": 1}))

    def test_aucun_doi_duplique_dans_le_dataset_final(self):
        dois = [r["DOI"].lower() for r in self.final if r["DOI"]]
        self.assertEqual(len(dois), len(set(dois)))

    def test_provenance(self):
        self.assertTrue(all(r["Bases"] in {"Scopus", "WoS", "Scopus + WoS"} for r in self.final))
        self.assertEqual(Counter(r["Bases"] for r in self.final), Counter({"Scopus + WoS": 71, "Scopus": 47, "WoS": 26}))

    def test_toutes_les_paires_ambigues_ont_une_decision_justifiee(self):
        dec = {frozenset((d["ID_A"], d["ID_B"])): d for d in self.dec}
        for r in self.man:
            d = dec.get(frozenset((r["ID_A"], r["ID_B"])))
            self.assertIsNotNone(d, (r["ID_A"], r["ID_B"]))
            self.assertIn(d["Decision"], {"Doublon", "Distinct"})
            self.assertGreater(len(d["Justification"]), 20)

    def test_titres_restants_en_double_sont_des_publications_distinctes_justifiees(self):
        norm = {r["ID"]: r["Titre_norm"] for r in self.all}
        c = Counter(norm[r["ID_notice_conservee"]] for r in self.final)
        distinct_ids = {i for d in self.dec if d["Decision"] == "Distinct" for i in (d["ID_A"], d["ID_B"])}
        for t, n in c.items():
            if n > 1:
                ids = [r["ID_notice_conservee"] for r in self.final if norm[r["ID_notice_conservee"]] == t]
                self.assertTrue(set(ids) <= distinct_ids, ids)


if __name__ == "__main__":
    unittest.main()
