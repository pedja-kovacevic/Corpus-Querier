import threading
import time
import unittest

from run_control import ConsecutiveFailureGuard, RunControl


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


if __name__ == "__main__":
    unittest.main()
