"""Thread-safe pause, resume, and stop coordination for query workers."""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


CONSECUTIVE_FAILURE_LIMIT = 10
AUTOMATIC_PAUSE_SECONDS = 24 * 60 * 60
RATE_LIMIT_WARNING_MARGIN = 10
RATE_LIMIT_PAUSE_MARGIN = 3


@dataclass(frozen=True)
class RateLimitWindow:
    """One rolling request quota enforced by a corpus provider."""

    name: str
    seconds: int
    limit: int


@dataclass(frozen=True)
class RateLimitSnapshot:
    """The limiter state immediately before a network request."""

    counts: dict[str, int]
    remaining: dict[str, int]
    warnings: tuple[str, ...]
    pause_until: float | None
    pause_windows: tuple[str, ...]


class RequestRateLimiter:
    """Track outbound requests in rolling minute, hour, and day windows.

    The ledger can be persisted so closing and reopening Corpus Querier does
    not reset the daily counter. Only requests made by Corpus Querier can be
    observed; activity from a provider's web interface or another API client
    remains outside this counter.
    """

    def __init__(
        self,
        windows: tuple[RateLimitWindow, ...],
        *,
        warning_margin: int = RATE_LIMIT_WARNING_MARGIN,
        pause_margin: int = RATE_LIMIT_PAUSE_MARGIN,
        history_path: Path | None = None,
        history_key: str = "default",
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not windows:
            raise ValueError("At least one rate-limit window is required.")
        if warning_margin <= pause_margin:
            raise ValueError("The warning margin must exceed the pause margin.")
        if pause_margin < 1:
            raise ValueError("The pause margin must be at least one.")
        for window in windows:
            if window.seconds <= 0:
                raise ValueError("Rate-limit window durations must be positive.")
            if window.limit <= warning_margin:
                raise ValueError(
                    f"The {window.name} request limit must exceed "
                    f"the warning margin ({warning_margin})."
                )

        self.windows = windows
        self.warning_margin = warning_margin
        self.pause_margin = pause_margin
        self.history_path = history_path
        self.history_key = history_key
        self.clock = clock
        self.timestamps: deque[float] = deque()
        self._warned_windows: set[str] = set()
        self._load()

    @property
    def longest_window(self) -> int:
        return max(window.seconds for window in self.windows)

    def _prune(self, now: float) -> None:
        cutoff = now - self.longest_window
        while self.timestamps and self.timestamps[0] <= cutoff:
            self.timestamps.popleft()

    def _load(self) -> None:
        if self.history_path is None:
            return
        try:
            payload = json.loads(self.history_path.read_text(encoding="utf-8"))
            values = payload.get(self.history_key, []) if isinstance(payload, dict) else []
            now = self.clock()
            valid = sorted(
                float(value)
                for value in values
                if 0 <= now - float(value) < self.longest_window
            )
            self.timestamps.extend(valid)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            # A missing or damaged optional ledger must never prevent a run.
            self.timestamps.clear()

    def _save(self) -> None:
        if self.history_path is None:
            return
        payload: dict[str, list[float]] = {}
        try:
            if self.history_path.exists():
                existing = json.loads(
                    self.history_path.read_text(encoding="utf-8")
                )
                if isinstance(existing, dict):
                    payload = existing
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            payload = {}

        payload[self.history_key] = list(self.timestamps)
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.history_path.with_suffix(
                self.history_path.suffix + ".tmp"
            )
            temporary.write_text(
                json.dumps(payload, separators=(",", ":")),
                encoding="utf-8",
            )
            temporary.replace(self.history_path)
        except OSError:
            # Rate limiting still works for the active run if persistence fails.
            pass

    def inspect(self, now: float | None = None) -> RateLimitSnapshot:
        """Return warning and pause information before the next request."""

        now = self.clock() if now is None else float(now)
        self._prune(now)
        counts: dict[str, int] = {}
        remaining: dict[str, int] = {}
        warnings: list[str] = []
        pause_windows: list[str] = []
        resume_times: list[float] = []

        timestamps = list(self.timestamps)
        for window in self.windows:
            cutoff = now - window.seconds
            active = [timestamp for timestamp in timestamps if timestamp > cutoff]
            count = len(active)
            available = max(0, window.limit - count)
            counts[window.name] = count
            remaining[window.name] = available

            if available > self.warning_margin:
                self._warned_windows.discard(window.name)
            elif window.name not in self._warned_windows:
                self._warned_windows.add(window.name)
                warnings.append(window.name)

            if available <= self.pause_margin:
                pause_windows.append(window.name)
                # Wait until enough of the oldest requests have expired to
                # preserve more than ``pause_margin`` unused requests.
                expirations_needed = (
                    count - (window.limit - self.pause_margin) + 1
                )
                index = max(0, expirations_needed - 1)
                resume_times.append(active[index] + window.seconds + 0.05)

        return RateLimitSnapshot(
            counts=counts,
            remaining=remaining,
            warnings=tuple(warnings),
            pause_until=max(resume_times) if resume_times else None,
            pause_windows=tuple(pause_windows),
        )

    def record_request(self, timestamp: float | None = None) -> None:
        """Record one actual outbound HTTP request and persist the ledger."""

        now = self.clock() if timestamp is None else float(timestamp)
        self._prune(now)
        self.timestamps.append(now)
        self._save()


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
