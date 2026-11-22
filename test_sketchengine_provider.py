import queue
import threading
import unittest
from pathlib import Path

from corpus_querier_clarin import JobConfig, QueryWorker
from corpus_querier_sketchengine import (
    CorpusQuerierSketchEngineApp,
    SKETCH_ENGINE_ROOT,
)


class FakeResponse:
    status_code = 200
    headers = {}

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, endpoint, *, params, timeout):
        self.calls.append((endpoint, params, timeout))
        return FakeResponse(self.payload)


def sketch_config(output_mode="total"):
    return JobConfig(
        mode="generated",
        input_file=None,
        output_file=Path("result.xlsx"),
        corpus="preloaded/bnc2",
        columns=[],
        start_row=1,
        end_row=None,
        words_text="run",
        word_source="typed",
        word_column=0,
        templates=['[lemma="{LEMMA}"]'],
        delay=1,
        timeout=30,
        attempts=2,
        save_every=25,
        min_form_frequency=1,
        case_sensitive=True,
        output_mode=output_mode,
        provider_name="Sketch Engine",
        api_key="secret-test-key",
        view_url=f"{SKETCH_ENGINE_ROOT}/view",
        freqs_url=f"{SKETCH_ENGINE_ROOT}/freqs",
        synchronous=True,
    )


class SketchEngineProviderTests(unittest.TestCase):
    def test_provider_uses_official_api_and_bnc_default(self):
        self.assertEqual(
            CorpusQuerierSketchEngineApp.default_corpus,
            "preloaded/bnc2",
        )
        self.assertTrue(CorpusQuerierSketchEngineApp.requires_api_key)
        self.assertEqual(
            CorpusQuerierSketchEngineApp.view_url,
            "https://api.sketchengine.eu/bonito/run.cgi/view",
        )

    def test_bearer_key_is_kept_in_the_http_header(self):
        worker = QueryWorker(sketch_config(), queue.Queue(), threading.Event())
        self.assertEqual(
            worker.session.headers["Authorization"],
            "Bearer secret-test-key",
        )

    def test_official_concsize_response_is_accepted(self):
        worker = QueryWorker(sketch_config(), queue.Queue(), threading.Event())
        worker.session = FakeSession({"concsize": 42})

        result = worker.fetch_result('[lemma="run"]')

        self.assertEqual(result.total_hits, 42)
        self.assertEqual(result.successful_attempts, 2)
        self.assertEqual(len(worker.session.calls), 2)
        endpoint, params, timeout = worker.session.calls[0]
        self.assertEqual(endpoint, f"{SKETCH_ENGINE_ROOT}/view")
        self.assertEqual(params["q"], 'q[lemma="run"]')
        self.assertEqual(params["asyn"], 0)
        self.assertEqual(timeout, 30)

    def test_forms_response_uses_the_authenticated_freqs_endpoint(self):
        payload = {
            "concsize": 12,
            "Blocks": [
                {
                    "Items": [
                        {"Word": [{"n": "runs"}], "freq": 7},
                        {"Word": [{"n": "run"}], "freq": 5},
                    ]
                }
            ],
        }
        worker = QueryWorker(
            sketch_config("forms_frequencies"),
            queue.Queue(),
            threading.Event(),
        )
        worker.session = FakeSession(payload)

        result = worker.fetch_result('[lemma="run"]')

        self.assertEqual(result.total_hits, 12)
        self.assertEqual(result.forms, [("runs", 7), ("run", 5)])
        self.assertEqual(
            worker.session.calls[0][0],
            f"{SKETCH_ENGINE_ROOT}/freqs",
        )


if __name__ == "__main__":
    unittest.main()
