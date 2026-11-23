import unittest

try:
    from corpus_querier_noske import QueryWorker, column_letter_to_index, generate_cql
except ModuleNotFoundError:
    QueryWorker = column_letter_to_index = generate_cql = None


@unittest.skipIf(QueryWorker is None, "integrated NoSketch module is not staged locally")
class NoSketchRegressionTests(unittest.TestCase):
    def test_excel_columns_beyond_z(self):
        self.assertEqual(column_letter_to_index("AA"), 26)

    def test_template_generation(self):
        self.assertEqual(
            generate_cql('[lemma="{LEMMA}"]', "čitati"),
            '[lemma="čitati"]',
        )

    def test_bonito_form_response(self):
        forms = QueryWorker.parse_forms_response({
            "Blocks": [{
                "Items": [
                    {"Word": [{"n": "čita"}], "frq": 12},
                    {"Word": [{"n": "Čita"}], "freq": 3},
                ]
            }]
        })
        self.assertEqual(forms, {"čita": 12, "Čita": 3})

    def test_missing_blocks_is_rejected(self):
        with self.assertRaisesRegex(Exception, "Blocks"):
            QueryWorker.parse_forms_response({})


if __name__ == "__main__":
    unittest.main()
