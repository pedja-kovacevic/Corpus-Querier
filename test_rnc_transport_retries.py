import queue
import unittest
from pathlib import Path

import requests

from corpus_querier_rnc import JobConfig, QueryError, QueryWorker


class FakeStopEvent:
    def __init__(self):
        self.waits = []

    def is_set(self):
        return False

    def wait(self, seconds):
        self.waits.append(seconds)
        return False


class FakeResponse:
    status_code = 200
    headers = {}

    def __init__(self, count):
        self.count = count

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "queryStats": {"wordUsageCount": self.count, "textCount": 2},
            "groups": [],
            "pagination": {"totalPageCount": 1, "maxAvailablePage": 0},
        }


class FakeSession:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def post(self, *args, **kwargs):
        self.calls += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        return None


def make_worker(results, attempts=2):
    config = JobConfig(
        mode="existing",
        token="test-token",
        input_file=None,
        output_file=Path("unused.xlsx"),
        corpus="MAIN",
        columns=[0],
        start_row=1,
        end_row=1,
        words_text="",
        word_source="direct",
        word_column=0,
        templates=[],
        delay=0,
        timeout=1,
        attempts=attempts,
        save_every=1,
        subcorpus=None,
        output_mode="Exact total frequency",
        ignore_case=False,
        minimum_form_frequency=1,
    )
    stop_event = FakeStopEvent()
    worker = QueryWorker(config, queue.Queue(), stop_event)
    worker.session.close()
    worker.session = FakeSession(results)
    # Keep the fake sequence when the production code discards a reset socket.
    worker._renew_session = lambda: None
    return worker, stop_event


class RNCTransportRetryTests(unittest.TestCase):
    query = '{"lexGramm": {}, "corpus": {"type": "MAIN"}}'

    def test_connection_reset_does_not_consume_required_attempt(self):
        worker, stop_event = make_worker([
            requests.ConnectionError("reset"),
            FakeResponse(5),
            FakeResponse(7),
        ])
        result, successful, _ = worker.fetch_result(self.query)
        self.assertEqual(result.total_occurrences, 7)
        self.assertEqual(successful, 2)
        self.assertEqual(worker.session.calls, 3)
        self.assertEqual(stop_event.waits, [2.0, 1])

    def test_one_attempt_per_query_is_supported(self):
        worker, stop_event = make_worker([FakeResponse(5)], attempts=1)

        result, successful, _ = worker.fetch_result(self.query)

        self.assertEqual(result.total_occurrences, 5)
        self.assertEqual(successful, 1)
        self.assertEqual(worker.session.calls, 1)
        self.assertEqual(stop_event.waits, [])

    def test_persistent_resets_pause_without_writing_a_false_error(self):
        worker, stop_event = make_worker([
            *[requests.ConnectionError("reset") for _ in range(9)],
            FakeResponse(5),
            FakeResponse(7),
        ])
        result, successful, _ = worker.fetch_result(self.query)
        self.assertEqual(result.total_occurrences, 7)
        self.assertEqual(successful, 2)
        self.assertEqual(worker.session.calls, 11)
        self.assertEqual(
            stop_event.waits,
            [2.0, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0, 300.0, 300.0, 1],
        )


if __name__ == "__main__":
    unittest.main()
