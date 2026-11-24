"""Étapes 5 à 12 sur de petits jeux fictifs, dont le défi 1 du lab (R1 à R4)."""
import io
import unittest
from contextlib import redirect_stdout

from tests.helpers import Workspace, load_module, scopus_row, wos_entry


def run(ws, mod):
    with redirect_stdout(io.StringIO()):
        mod.main()


class TestDefi1(unittest.TestCase):
    """R1 (Scopus) et R2 (WoS) : même DOI ; R3 : titre proche, autre DOI ; R4 : même titre, autre DOI, autre auteur."""

    def setUp(self):
        self.mod = load_module()
        sco = [scopus_row("Deep Learning for Android", "10.123/abc", "Smith J.", "2023"),
               scopus_row("Deep Learning for Android Security", "10.456/def", "Smith J.", "2023")]
        wos = [wos_entry("R2", "Deep Learning for Android", "10.123/abc", "Smith, John", "2023"),
               wos_entry("R4", "Deep Learning for Android", "10.789/ghi", "Doe, A.", "2022")]
        decisions = [("SCO-001", "WOS-002", "Distinct", "DOI, auteur et année différents"),
                     ("SCO-001", "SCO-002", "Distinct", "Titre et DOI différents")]
        self.ws = Workspace(self.mod, sco, wos, decisions)
        run(self.ws, self.mod)

    def tearDown(self):
        self.ws.close()

    def test_R1_R2_doublon_par_DOI(self):
        log = self.ws.out("03_log_doublons_supprimes.csv")
        self.assertEqual([(r["ID"], r["Doublon_de"], r["Raison"]) for r in log], [("WOS-001", "SCO-001", "P1 DOI identique")])

    def test_R1_R4_meme_titre_mais_DOI_differents_va_en_verification(self):
        man = self.ws.out("02_verification_manuelle.csv")
        motifs = {frozenset((r["ID_A"], r["ID_B"])): r["Motif"] for r in man}
        self.assertIn("DOI différents", motifs[frozenset(("SCO-001", "WOS-002"))])

    def test_R1_R3_titre_similaire_meme_auteur_va_en_verification(self):
        man = self.ws.out("02_verification_manuelle.csv")
        pair = [r for r in man if {r["ID_A"], r["ID_B"]} == {"SCO-001", "SCO-002"}]
        self.assertEqual(len(pair), 1)
        self.assertGreaterEqual(float(pair[0]["Similarite_titre"]), 0.80)
        self.assertIn("même premier auteur", pair[0]["Motif"])

    def test_resultat_final_trois_references(self):
        final = self.ws.out("05_dataset_final_screening_public.csv")
        self.assertEqual(len(final), 3)
        merged = [r for r in final if r["Bases"] == "Scopus + WoS"]
        self.assertEqual([r["IDs_fusionnes"] for r in merged], ["SCO-001; WOS-001"])

    def test_rapport_prisma(self):
        rep = {r["Base"]: r for r in self.ws.out("04_rapport_prisma.csv")}
        self.assertEqual((rep["Total"]["Importees"], rep["Total"]["Doublons_supprimes_dans_cette_base"],
                          rep["Total"]["Notices_conservees_de_cette_base"]), ("4", "1", "3"))


class TestPiegesEtape9(unittest.TestCase):
    """Cas réels de la SLR : conférence et revue de même titre ; deux volumes d'actes de même titre."""

    def setUp(self):
        self.mod = load_module()
        sco = [scopus_row("Analysis and sensing of verticillium wilt", "", "Kostas B.", "2020", "Conference paper", "2844"),
               scopus_row("Analysis and sensing of verticillium wilt", "10.3390/jsan1", "Blekos K.", "2021", "Article", "10"),
               scopus_row("4th Conference OL2A 2024", "", "", "2024", "Conference review", "2281 CCIS", "978-1"),
               scopus_row("4th Conference OL2A 2024", "", "", "2024", "Conference review", "2280 CCIS", "978-2")]
        wos = [wos_entry("J", "Analysis and Sensing of Verticillium Wilt", "10.3390/JSAN1", "Blekos, Kostas", "2021")]
        self.ws = Workspace(self.mod, sco, wos)  # aucune décision : rien ne doit être fusionné hors DOI
        run(self.ws, self.mod)

    def tearDown(self):
        self.ws.close()

    def test_titre_identique_jamais_fusionne_automatiquement_si_contradiction(self):
        log = self.ws.out("03_log_doublons_supprimes.csv")
        self.assertEqual([r["Raison"] for r in log], ["P1 DOI identique"])  # seule la notice WoS de l'article
        motifs = " | ".join(r["Motif"] for r in self.ws.out("02_verification_manuelle.csv"))
        self.assertIn("types différents", motifs)
        self.assertIn("volumes différents", motifs)
        self.assertEqual(len(self.ws.out("05_dataset_final_screening_public.csv")), 4)

    def test_doublon_confirme_manuellement(self):
        self.ws.close()
        self.mod = load_module()
        sco = [scopus_row("Remote sensing Atacama", "10.64697/x-p1951-cd", "Pino-Vargas E.", "2025", "Conference paper")]
        wos = [wos_entry("A", "Remote sensing Atacama", "10.64697/x-p1951", "Pino-Vargas, Edwin", "2025", kind="inproceedings")]
        self.ws = Workspace(self.mod, sco, wos, [("SCO-001", "WOS-001", "Doublon", "Variante -cd du même DOI")])
        run(self.ws, self.mod)
        log = self.ws.out("03_log_doublons_supprimes.csv")
        self.assertEqual([(r["ID"], r["Raison"]) for r in log], [("WOS-001", "P4 Vérification manuelle")])


if __name__ == "__main__":
    unittest.main()
