import queue
import threading
import unittest
from pathlib import Path

try:
    from corpus_querier_noske import (
        JobConfig,
        QueryWorker,
        column_letter_to_index,
        generate_cql,
    )
    from run_control import RateLimitWindow, RequestRateLimiter
except ModuleNotFoundError:
    QueryWorker = column_letter_to_index = generate_cql = None


class MutableClock:
    def __init__(self, value):
        self.value = float(value)

    def __call__(self):
        return self.value


class ManualResumeControl:
    def __init__(self):
        self.pauses = []

    def wait_until_running(self):
        return True

    def automatic_pause(self, seconds):
        self.pauses.append(seconds)
        return "resumed"


def noske_config():
    return JobConfig(
        mode="generated",
        input_file=None,
        output_file=Path("result.xlsx"),
        corpus="srwac",
        columns=[],
        start_row=1,
        end_row=None,
        words_text="čitati",
        word_source="typed",
        word_column=0,
        templates=['[lemma="{LEMMA}"]'],
        delay=1,
        timeout=30,
        attempts=1,
        save_every=25,
        min_form_frequency=1,
        case_sensitive=True,
        output_mode="total",
        allow_rate_limit_override=True,
    )


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

    def test_manual_resume_overrides_noske_rate_pause(self):
        events = queue.Queue()
        worker = QueryWorker(
            noske_config(), events, threading.Event()
        )
        clock = MutableClock(1_800_000_000.0)
        worker.rate_limiter = RequestRateLimiter(
            (RateLimitWindow("minute", 60, 20),),
            clock=clock,
        )
        for _ in range(17):
            worker.rate_limiter.record_request(1_799_999_990.0)
        control = ManualResumeControl()
        worker.control = control

        worker._wait_for_rate_capacity()

        self.assertEqual(len(control.pauses), 1)
        self.assertEqual(
            worker.rate_limiter.inspect().counts["minute"], 0
        )
        events_seen = []
        while not events.empty():
            events_seen.append(events.get_nowait())
        self.assertTrue(
            any(
                kind == "rate_resumed" and payload.get("overridden")
                for kind, payload in events_seen
            )
        )


if __name__ == "__main__":
    unittest.main()
