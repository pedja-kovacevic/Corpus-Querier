import queue
import threading
import unittest
from pathlib import Path

from corpus_querier_noske import JobConfig, QueryWorker
from corpus_querier_sketchengine import (
    CorpusQuerierSketchEngineApp,
    SKETCH_ENGINE_ROOT,
)
from run_control import RateLimitWindow, RequestRateLimiter


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


class MutableClock:
    def __init__(self, value):
        self.value = float(value)

    def __call__(self):
        return self.value


class AdvancingControl:
    def __init__(self, clock):
        self.clock = clock
        self.pauses = []

    def wait_until_running(self):
        return True

    def automatic_pause(self, seconds):
        self.pauses.append(seconds)
        self.clock.value += seconds
        return "elapsed"


def sketch_config(output_mode="total", attempts=2):
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
        attempts=attempts,
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
        self.assertEqual(
            worker.rate_limiter.inspect().counts["minute"],
            2,
        )
        endpoint, params, timeout = worker.session.calls[0]
        self.assertEqual(endpoint, f"{SKETCH_ENGINE_ROOT}/view")
        self.assertEqual(params["q"], 'q[lemma="run"]')
        self.assertEqual(params["asyn"], 0)
        self.assertEqual(timeout, 30)

    def test_one_attempt_per_query_is_supported(self):
        worker = QueryWorker(
            sketch_config(attempts=1), queue.Queue(), threading.Event()
        )
        worker.session = FakeSession({"concsize": 42})

        result = worker.fetch_result('[lemma="run"]')

        self.assertEqual(result.successful_attempts, 1)
        self.assertEqual(len(worker.session.calls), 1)
        self.assertEqual(
            worker.rate_limiter.inspect().counts["minute"],
            1,
        )

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

    def test_worker_pauses_until_the_rolling_window_is_safe(self):
        events = queue.Queue()
        worker = QueryWorker(
            sketch_config(attempts=1), events, threading.Event()
        )
        clock = MutableClock(1_800_000_000.0)
        worker.rate_limiter = RequestRateLimiter(
            (RateLimitWindow("minute", 60, 20),),
            clock=clock,
        )
        for _ in range(17):
            worker.rate_limiter.record_request(1_799_999_990.0)
        control = AdvancingControl(clock)
        worker.control = control

        worker._wait_for_rate_capacity()

        self.assertEqual(len(control.pauses), 1)
        self.assertAlmostEqual(control.pauses[0], 50.05)
        event_names = []
        while not events.empty():
            event_names.append(events.get_nowait()[0])
        self.assertIn("rate_warning", event_names)
        self.assertIn("rate_paused", event_names)
        self.assertIn("rate_resumed", event_names)


if __name__ == "__main__":
    unittest.main()
