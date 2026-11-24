"""Thread-safe pause, resume, and stop coordination for query workers."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


CONSECUTIVE_FAILURE_LIMIT = 10
AUTOMATIC_PAUSE_SECONDS = 24 * 60 * 60


class ConsecutiveFailureGuard:
    """Count consecutive failures and signal when a safety pause is due."""

    def __init__(self, limit: int = CONSECUTIVE_FAILURE_LIMIT) -> None:
        if limit < 1:
            raise ValueError("Failure limit must be at least one.")
        self.limit = limit
        self.count = 0

    def record_success(self) -> None:
        self.count = 0

    def record_failure(self) -> bool:
        self.count += 1
        if self.count < self.limit:
            return False
        self.count = 0
        return True


class RunControl:
    """Coordinate a worker that may be paused between network requests.

    ``run_event`` is set while work may proceed and cleared while paused.  A
    stop always takes precedence over a pause so a paused worker can still be
    stopped and saved promptly.
    """

    def __init__(
        self,
        stop_event: threading.Event,
        run_event: threading.Event,
        on_paused: Callable[[], None] | None = None,
    ) -> None:
        self.stop_event = stop_event
        self.run_event = run_event
        self.on_paused = on_paused
        self._pause_reported = False

    def wait_until_running(self) -> bool:
        """Wait until resumed; return ``False`` when stopping was requested."""

        if self.stop_event.is_set():
            return False

        if not self.run_event.is_set() and not self._pause_reported:
            self._pause_reported = True
            if self.on_paused is not None:
                self.on_paused()

        while not self.run_event.wait(0.1):
            if self.stop_event.is_set():
                return False

        self._pause_reported = False
        return not self.stop_event.is_set()

    def wait(self, seconds: float) -> bool:
        """Wait interruptibly; return ``False`` when the run should stop.

        Time spent paused also satisfies a configured inter-request delay.  On
        resume, the next request may therefore start immediately, while no
        request can start during the pause itself.
        """

        seconds = max(0.0, float(seconds))
        # Lightweight test doubles generally implement ``wait`` without
        # actually advancing a clock. Preserve their single-wait semantics.
        if not isinstance(self.stop_event, threading.Event):
            if not self.wait_until_running():
                return False
            return not self.stop_event.wait(seconds)

        deadline = time.monotonic() + seconds
        while True:
            if not self.wait_until_running():
                return False
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            if self.stop_event.wait(min(0.1, remaining)):
                return False

    def automatic_pause(self, seconds: float) -> str:
        """Pause until the timer elapses, the user resumes, or the run stops.

        Returns ``"elapsed"``, ``"resumed"``, or ``"stopped"``.  The same
        run event is used by the UI, so the user can interrupt a long automatic
        cooldown with Resume when they deliberately want to continue sooner.
        """

        self.run_event.clear()
        deadline = time.monotonic() + max(0.0, float(seconds))
        while True:
            if self.stop_event.is_set():
                return "stopped"
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self.run_event.set()
                return "elapsed"
            if self.run_event.wait(min(1.0, remaining)):
                return "resumed"
