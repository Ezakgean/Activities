import unittest
from pathlib import Path

from app.analise import extract_record, _round_record_values
from app.coletor_lote_rmd import create_payload
from app.scraper_rmd import extract_composition, extract_indicators, merge_indicators


FIXTURES = Path(__file__).parent / "fixtures"


class ColetaTests(unittest.TestCase):
    def test_missing_value_serializes_as_null(self):
        self.assertIsNone(_round_record_values({"valor": float("nan")})["valor"])

    def test_modern_report_to_dashboard(self):
        text = (FIXTURES / "2025_12.txt").read_text()
        indicators = extract_indicators(text, "Dezembro")
        payload = create_payload(2025, 12, "pagina", "pdf")
        merge_indicators(payload, indicators)
        record = extract_record(payload, Path("rmd.json"))
        self.assertEqual(record["prefixada_pct"], 22.05)
        self.assertEqual(record["taxa_flutuante_pct"], 48.25)
        self.assertIsNone(record["selic_pct"])
        self.assertEqual(record["emissoes_nominais_brl_milhoes"], 65813.65)
        self.assertEqual(record["resgates_nominais_brl_milhoes"], 5886.51)
        self.assertIsNone(record["impacto_liquidez_nominal_brl_milhoes"])

    def test_2015_layout(self):
        indicators = extract_indicators((FIXTURES / "2015_12.txt").read_text(), "Dezembro")
        self.assertEqual(indicators["composicao_percentual"]["prefixada"], 39.43)
        self.assertEqual(indicators["fluxos_dpf"]["resgates_brl_milhoes"], 7902.75)

    def test_legacy_month_and_missing_month(self):
        text = (FIXTURES / "2000_11.txt").read_text()
        self.assertEqual(extract_composition(text, "Novembro")["selic"], 52.15)
        self.assertEqual(extract_composition(text, "Outubro")["prefixada"], 15.7)
        self.assertEqual(extract_composition(text, "Janeiro"), {})

    def test_reject_invalid_percentage_total(self):
        text = (FIXTURES / "2025_12.txt").read_text().replace("48,25%", "88,25%")
        self.assertEqual(extract_composition(text, "Dezembro"), {})

    def test_side_by_side_narrative_and_table(self):
        values = extract_composition((FIXTURES / "2010_12.txt").read_text(), "Dezembro", 2010)
        self.assertEqual(values["prefixada"], 36.63)
        self.assertEqual(values["selic"], 30.8)
        plural = (FIXTURES / "2010_12.txt").read_text().replace("Prefixado", "Prefixados")
        self.assertEqual(extract_composition(plural, "Dezembro", 2010)["prefixada"], 36.63)

    def test_year_suffix_does_not_select_previous_december(self):
        text = (FIXTURES / "2004_12.txt").read_text()
        self.assertEqual(extract_composition(text, "Dezembro", 2004)["prefixada"], 20.09)
        self.assertEqual(extract_composition(text, "Dezembro", 2003)["prefixada"], 12.51)
        self.assertEqual(extract_composition(text, "Dezembro", 2005), {})

    def test_missing_values_do_not_erase_existing_data_and_zero_is_kept(self):
        payload = create_payload(2024, 2, "pagina", "pdf")
        merge_indicators(payload, {"composicao_percentual": {"prefixada": 12}})
        merge_indicators(payload, {"composicao_percentual": {"prefixada": None, "cambio": 0}})
        self.assertEqual(payload["resumo_fevereiro_2024"]["composicao_percentual"], {"prefixada": 12, "cambio": 0})
        self.assertEqual(payload["periodo_referencia"]["fim"], "2024-02-29")


if __name__ == "__main__":
    unittest.main()
