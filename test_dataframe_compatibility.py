import unittest

import pandas as pd


class DataframeCompatibilityTests(unittest.TestCase):
    def test_generated_query_cells_accept_integer_results(self):
        frame = pd.DataFrame(
            [["INPUT", '[lemma="{LEMMA}"]']],
            dtype=object,
        )
        frame.loc[1] = ["бежать", '[lemma="бежать"]']
        frame.iat[1, 1] = 81155
        self.assertEqual(frame.iat[1, 1], 81155)

    def test_existing_query_cells_accept_error_markers_and_counts(self):
        frame = pd.DataFrame(
            [['[lemma="бежать"]'], ['[lemma="писать"]']],
            dtype=object,
        )
        frame.iat[0, 0] = 81155
        frame.iat[1, 0] = "ERROR"
        self.assertEqual(frame.iloc[:, 0].tolist(), [81155, "ERROR"])


if __name__ == "__main__":
    unittest.main()
