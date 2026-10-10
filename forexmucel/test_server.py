import unittest

import server


class LocalFormulaTests(unittest.TestCase):
    def test_generates_localized_sum_formulas_without_ai(self):
        spanish = server.local_response("generate", "Suma los valores de A1 a A10", "es")
        english = server.local_response("generate", "Sum values from A1:A10", "en")

        self.assertEqual(spanish["formula"], "=SUMA(A1:A10)")
        self.assertEqual(english["formula"], "=SUM(A1:A10)")
        self.assertEqual(spanish["mode"], "local")

    def test_generates_if_formula_from_explicit_condition(self):
        spanish = server.local_response(
            "generate",
            "Si A1 es mayor que 10, muestra Sí si no No",
            "es",
        )
        english = server.local_response(
            "generate",
            "If A1 is greater than 10 then return Yes otherwise No",
            "en",
        )

        self.assertEqual(spanish["formula"], '=SI(A1>10;"Sí";"No")')
        self.assertEqual(english["formula"], '=IF(A1>10,"Yes","No")')

    def test_generates_if_from_sales_description_and_spanish_thousands(self):
        result = server.local_response(
            "generate",
            "Si las ventas de B2 superan 1.000, muestra “Objetivo”; si no, muestra “Pendiente”",
            "es",
        )

        self.assertEqual(result["formula"], '=SI(B2>1000;"Objetivo";"Pendiente")')

    def test_generates_if_from_exceeds_english_request(self):
        result = server.local_response(
            "generate",
            "If sales in B2 exceed 1,000, show Target; otherwise Pending",
            "en",
        )

        self.assertEqual(result["formula"], '=IF(B2>1000,"Target","Pending")')

    def test_describes_conditional_formatting_instead_of_returning_a_cell_value(self):
        result = server.local_response(
            "generate",
            "a>b entonces el valor de a es amarillo y si no verde",
            "es",
        )

        self.assertEqual(result["formula"], "")
        self.assertIn("=A1>B1", result["explanation"])
        self.assertIn("=A1<=B1", result["explanation"])
        self.assertIn("relleno amarillo", result["explanation"])
        self.assertIn("relleno verde", result["explanation"])

    def test_asks_for_details_when_conditional_format_cells_are_ambiguous(self):
        result = server.local_response(
            "generate",
            "make it yellow if values are different",
            "en",
        )

        self.assertEqual(result["formula"], "")
        self.assertIn("Specify which cells", result["explanation"])

    def test_reports_unsupported_requests_without_failing(self):
        result = server.local_response("generate", "build a complex forecast", "en")

        self.assertEqual(result["formula"], "")
        self.assertEqual(result["mode"], "local")
        self.assertIn("does not recognize", result["explanation"])

    def test_explains_known_formula_locally(self):
        result = server.local_response("explain", "=SUM(A1:A10)", "en")

        self.assertEqual(result["formula"], "=SUM(A1:A10)")
        self.assertIn("Adds all values", result["explanation"])
        self.assertIn("∑", result["notation"])
        self.assertEqual(result["mode"], "local")

    def test_explains_if_formula_in_words_and_readable_notation(self):
        result = server.local_response(
            "explain",
            '=SI(B2>1000;"Objetivo";"Pendiente")',
            "es",
        )

        self.assertIn("B2", result["explanation"])
        self.assertIn("Objetivo", result["explanation"])
        self.assertIn("Pendiente", result["explanation"])
        self.assertIn("si B2 > 1000", result["notation"])

    def test_rejects_malformed_if_formula_instead_of_describing_it_as_valid(self):
        result = server.local_response("explain", "=si(A>b: a=2)", "es")

        self.assertFalse(result["valid"])
        self.assertIn("no parece válida", result["explanation"])


if __name__ == "__main__":
    unittest.main()
