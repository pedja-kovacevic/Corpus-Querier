import queue
import tempfile
import threading
import unittest
from pathlib import Path

import pandas as pd

from corpus_querier_rnc import JobConfig, QueryWorker


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

    def test_resumed_rnc_workbook_skips_results_and_normalizes_remaining_cql(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "resume.xlsx"
            pd.DataFrame([[81155], ["ERROR"], ['[lemma=“папа”]']]).to_excel(
                source, index=False, header=False
            )
            config = JobConfig(
                mode="existing", token="test", input_file=source,
                output_file=Path(directory) / "out.xlsx", corpus="MAIN",
                columns=[0], start_row=1, end_row=3, words_text="",
                word_source="spreadsheet", word_column=0, templates=[],
                delay=0, timeout=1, attempts=2, save_every=1,
                subcorpus=None, output_mode="Exact total frequency",
                ignore_case=False, minimum_form_frequency=1,
            )
            worker = QueryWorker(config, queue.Queue(), threading.Event())
            try:
                frame, tasks = worker.load_job()
            finally:
                worker.session.close()
            self.assertEqual(tasks, [(2, 0, '[lemma="папа"]')])
            self.assertEqual(frame.iat[0, 0], 81155)
            self.assertEqual(frame.iat[1, 0], "ERROR")

    def test_resumed_generated_workbook_reconstructs_previous_error(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "generated-resume.xlsx"
            pd.DataFrame([
                ["INPUT", '[lemma="{LEMMA}"]'],
                ["папа", "ERROR"],
                ["мама", 120],
            ]).to_excel(source, index=False, header=False)
            config = JobConfig(
                mode="existing", token="test", input_file=source,
                output_file=Path(directory) / "out.xlsx", corpus="MAIN",
                columns=[1], start_row=2, end_row=3, words_text="",
                word_source="spreadsheet", word_column=0, templates=[],
                delay=0, timeout=1, attempts=2, save_every=1,
                subcorpus=None, output_mode="Exact total frequency",
                ignore_case=False, minimum_form_frequency=1,
            )
            worker = QueryWorker(config, queue.Queue(), threading.Event())
            try:
                _, tasks = worker.load_job()
            finally:
                worker.session.close()
            self.assertEqual(tasks, [(1, 1, '[lemma="папа"]')])


if __name__ == "__main__":
    unittest.main()
