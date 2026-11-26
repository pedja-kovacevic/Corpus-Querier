import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from run_control import (
    ConsecutiveFailureGuard,
    RateLimitWindow,
    RequestRateLimiter,
    RunControl,
)


class RunControlTests(unittest.TestCase):
    def test_failure_guard_triggers_on_tenth_consecutive_failure(self):
        guard = ConsecutiveFailureGuard(limit=10)

        self.assertEqual(
            [guard.record_failure() for _ in range(10)],
            [False] * 9 + [True],
        )
        self.assertEqual(guard.count, 0)

    def test_success_resets_consecutive_failure_count(self):
        guard = ConsecutiveFailureGuard(limit=3)
        self.assertFalse(guard.record_failure())
        self.assertFalse(guard.record_failure())
        guard.record_success()
        self.assertFalse(guard.record_failure())

    def test_paused_worker_waits_until_resume(self):
        stop_event = threading.Event()
        run_event = threading.Event()
        pause_observed = threading.Event()
        control = RunControl(stop_event, run_event, pause_observed.set)
        result = []

        thread = threading.Thread(
            target=lambda: result.append(control.wait_until_running())
        )
        thread.start()
        self.assertTrue(pause_observed.wait(1))
        self.assertTrue(thread.is_alive())

        run_event.set()
        thread.join(1)
        self.assertEqual(result, [True])

    def test_stop_interrupts_a_paused_worker(self):
        stop_event = threading.Event()
        run_event = threading.Event()
        control = RunControl(stop_event, run_event)
        result = []

        thread = threading.Thread(
            target=lambda: result.append(control.wait_until_running())
        )
        thread.start()
        time.sleep(0.05)
        stop_event.set()
        thread.join(1)

        self.assertEqual(result, [False])

    def test_user_can_interrupt_automatic_pause(self):
        stop_event = threading.Event()
        run_event = threading.Event()
        run_event.set()
        control = RunControl(stop_event, run_event)
        result = []

        thread = threading.Thread(
            target=lambda: result.append(control.automatic_pause(60))
        )
        thread.start()
        for _ in range(100):
            if not run_event.is_set():
                break
            time.sleep(0.01)
        self.assertFalse(run_event.is_set())

        run_event.set()
        thread.join(1)
        self.assertEqual(result, ["resumed"])

    def test_automatic_pause_resumes_after_timer(self):
        stop_event = threading.Event()
        run_event = threading.Event()
        run_event.set()
        control = RunControl(stop_event, run_event)

        self.assertEqual(control.automatic_pause(0.01), "elapsed")
        self.assertTrue(run_event.is_set())

    def test_rate_limiter_warns_with_ten_requests_remaining(self):
        limiter = RequestRateLimiter(
            (RateLimitWindow("minute", 60, 100),),
            clock=lambda: 1_000.0,
        )
        for _ in range(90):
            limiter.record_request(999.0)

        snapshot = limiter.inspect(1_000.0)

        self.assertEqual(snapshot.remaining["minute"], 10)
        self.assertEqual(snapshot.warnings, ("minute",))
        self.assertIsNone(snapshot.pause_until)
        self.assertEqual(limiter.inspect(1_000.0).warnings, ())

    def test_rate_limiter_pauses_with_three_requests_remaining(self):
        limiter = RequestRateLimiter(
            (RateLimitWindow("minute", 60, 100),),
            clock=lambda: 1_000.0,
        )
        for _ in range(97):
            limiter.record_request(999.0)

        snapshot = limiter.inspect(1_000.0)

        self.assertEqual(snapshot.remaining["minute"], 3)
        self.assertEqual(snapshot.pause_windows, ("minute",))
        self.assertAlmostEqual(snapshot.pause_until, 1_059.05)

        resumed = limiter.inspect(1_059.1)
        self.assertIsNone(resumed.pause_until)
        self.assertEqual(resumed.remaining["minute"], 100)

    def test_rate_limiter_uses_latest_required_resume_time(self):
        limiter = RequestRateLimiter(
            (
                RateLimitWindow("minute", 60, 20),
                RateLimitWindow("hour", 3_600, 30),
            ),
            clock=lambda: 10_000.0,
        )
        for _ in range(10):
            limiter.record_request(9_000.0)
        for _ in range(17):
            limiter.record_request(9_990.0)

        snapshot = limiter.inspect(10_000.0)

        self.assertEqual(set(snapshot.pause_windows), {"minute", "hour"})
        self.assertAlmostEqual(snapshot.pause_until, 12_600.05)

    def test_rate_limiter_history_survives_restart(self):
        with TemporaryDirectory() as directory:
            history_path = Path(directory) / "rate-limit-history.json"
            windows = (RateLimitWindow("day", 86_400, 100),)
            first = RequestRateLimiter(
                windows,
                history_path=history_path,
                history_key="Sketch Engine",
                clock=lambda: 50_000.0,
            )
            first.record_request(49_999.0)

            second = RequestRateLimiter(
                windows,
                history_path=history_path,
                history_key="Sketch Engine",
                clock=lambda: 50_000.0,
            )

            self.assertEqual(second.inspect().counts["day"], 1)


if __name__ == "__main__":
    unittest.main()
