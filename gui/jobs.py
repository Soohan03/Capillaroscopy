"""Background jobs, so long work never freezes the window.

The old GUI ran stabilization and optical flow one frame per tick of its main
loop, inside the UI. Here a job is a function run on a worker thread: it gets
its `Job` to report progress to (reporting is also where cancellation is
noticed) and its result or error comes back on the Tk thread through the
callbacks given to `JobManager.submit`. Jobs in the same lane run one after
another; lanes run side by side, so a measurement need not wait for a long
optical-flow computation.

Nothing here touches Tk except through the `after` method of the widget the
manager is given; the worker threads never call Tk.
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
import time
import traceback
from typing import Callable, Optional

from capillary.measure import Cancelled

log = logging.getLogger(__name__)

__all__ = ['Cancelled', 'Job', 'JobManager', 'LatestOnlyWorker']


class Job:
    def __init__(self, title: str, fn: Callable, lane: str, on_done=None, on_error=None, on_cancel=None, key=None):
        self.title = title
        self.fn = fn
        self.lane = lane
        self.on_done = on_done
        self.on_error = on_error
        self.on_cancel = on_cancel
        self.key = key
        self.state = 'queued'          # queued, running, done, failed, cancelled
        self.progress: Optional[float] = None
        self.message = ''
        self.error: Optional[BaseException] = None
        self.started_at: Optional[float] = None
        self._cancel = threading.Event()

    # called from the worker thread ------------------------------------------------
    def report(self, progress: Optional[float] = None, message: Optional[str] = None) -> None:
        """Update progress (0..1) and/or the status message; raises `Cancelled` if cancelled."""
        if progress is not None:
            self.progress = max(0.0, min(1.0, float(progress)))
        if message is not None:
            self.message = message
        if self._cancel.is_set():
            raise Cancelled()

    def cancelled(self) -> bool:
        return self._cancel.is_set()

    # called from the Tk thread ----------------------------------------------------
    def cancel(self) -> None:
        self._cancel.set()

    @property
    def finished(self) -> bool:
        return self.state in ('done', 'failed', 'cancelled')

    @property
    def eta_s(self) -> Optional[float]:
        """Rough time left, from the progress made so far."""
        if self.state != 'running' or not self.progress or self.started_at is None:
            return None
        elapsed = time.monotonic() - self.started_at
        if elapsed < 3 or self.progress < 0.02:
            return None
        return elapsed * (1 - self.progress) / self.progress


class JobManager:
    def __init__(self, widget, poll_ms: int = 100):
        self._widget = widget
        self._poll_ms = poll_ms
        self._events: queue.Queue = queue.Queue()
        self._lanes: dict[str, queue.Queue] = {}
        self.jobs: list[Job] = []
        self._listeners: list[Callable[[], None]] = []
        self._threads: list[threading.Thread] = []
        self._closed = False
        self._widget.after(self._poll_ms, self._poll)

    def add_listener(self, callback: Callable[[], None]) -> None:
        """`callback()` runs on the Tk thread whenever jobs change or progress."""
        self._listeners.append(callback)

    def submit(self, title, fn, *, lane='analysis', on_done=None, on_error=None, on_cancel=None, key=None):
        """Queue `fn(job)`; returns the `Job`, or None if a job with the same `key` is pending."""
        if key is not None and any(job.key == key and not job.finished for job in self.jobs):
            return None
        job = Job(title, fn, lane, on_done, on_error, on_cancel, key)
        self.jobs.append(job)
        if lane not in self._lanes:
            self._lanes[lane] = queue.Queue()
            thread = threading.Thread(target=self._work, args=(self._lanes[lane],), name=f'jobs-{lane}', daemon=True)
            thread.start()
            self._threads.append(thread)
        self._lanes[lane].put(job)
        self._notify()
        return job

    def active(self) -> list[Job]:
        return [job for job in self.jobs if not job.finished]

    def running(self) -> list[Job]:
        return [job for job in self.jobs if job.state == 'running']

    def find(self, key) -> Optional[Job]:
        for job in self.jobs:
            if job.key == key and not job.finished:
                return job
        return None

    def cancel_all(self) -> None:
        for job in self.active():
            job.cancel()

    def close(self, timeout: float = 10.0) -> bool:
        """Cancel every job and wait up to `timeout` s for the workers to stop; True if they did.

        Waiting matters: a worker still inside OpenCV when Python exits takes
        the process down with a C++ abort instead of a clean exit.
        """
        self.cancel_all()
        self._closed = True
        for lane in self._lanes.values():
            lane.put(None)
        return _join(self._threads, timeout)

    # worker threads -----------------------------------------------------------------
    def _work(self, lane: queue.Queue) -> None:
        while True:
            job = lane.get()
            if job is None:
                return
            if job.cancelled():
                self._events.put(('cancelled', job, None))
                continue
            job.started_at = time.monotonic()
            self._events.put(('running', job, None))
            try:
                result = job.fn(job)
            except Cancelled:
                self._events.put(('cancelled', job, None))
            except BaseException as exc:  # noqa: BLE001 - reported to the user, never lost
                log.error('Job failed: %s\n%s', job.title, traceback.format_exc())
                self._events.put(('failed', job, exc))
            else:
                self._events.put(('done', job, result))

    # Tk thread ----------------------------------------------------------------------
    def _poll(self) -> None:
        if self._closed:
            return
        changed = False
        while True:
            try:
                event, job, payload = self._events.get_nowait()
            except queue.Empty:
                break
            changed = True
            if event == 'running':
                if job.state == 'queued':
                    job.state = 'running'
                continue
            job.state = event
            callback = {'done': job.on_done, 'failed': job.on_error, 'cancelled': job.on_cancel}[event]
            if event == 'failed':
                job.error = payload
            if callback is not None:
                try:
                    callback(payload) if event != 'cancelled' else callback()
                except Exception:
                    log.exception('Error in the completion handler of %s', job.title)
                    self._widget._root().report_callback_exception(*sys.exc_info())
        # keep the list short: forget finished jobs except the last few
        finished = [job for job in self.jobs if job.finished]
        if len(finished) > 20:
            for job in finished[:-20]:
                self.jobs.remove(job)
        if changed or self.running():
            self._notify()
        self._widget.after(self._poll_ms, self._poll)

    def _notify(self) -> None:
        for listener in list(self._listeners):
            try:
                listener()
            except Exception:
                log.exception('Job listener failed')


class LatestOnlyWorker:
    """Runs `fn` on a thread for the most recent request only.

    For previews: while one runs, newer requests replace each other, and only
    the newest is computed next. Results arrive on the Tk thread via
    `on_result(token, result_or_exception)`.
    """

    def __init__(self, widget, fn: Callable, on_result: Callable, poll_ms: int = 40):
        self._widget = widget
        self._fn = fn
        self._on_result = on_result
        self._poll_ms = poll_ms
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._request = None
        self._results: queue.Queue = queue.Queue()
        self._busy = 0
        self._polling = False
        self._stopped = False
        self._thread = threading.Thread(target=self._run, name='preview', daemon=True)
        self._thread.start()

    def request(self, token, *args, **kwargs) -> None:
        with self._lock:
            if self._request is None:
                self._busy += 1
            self._request = (token, args, kwargs)
        self._wake.set()
        if not self._polling:
            self._polling = True
            self._widget.after(self._poll_ms, self._poll)

    def stop(self, timeout: float = 5.0) -> bool:
        """Stop after the request being computed; True if the thread ended within `timeout` s."""
        self._stopped = True
        self._wake.set()
        return _join([self._thread], timeout)

    def _run(self) -> None:
        while not self._stopped:
            self._wake.wait()
            with self._lock:
                request, self._request = self._request, None
                self._wake.clear()
            if request is None or self._stopped:
                continue
            token, args, kwargs = request
            try:
                result = self._fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - handed to on_result
                log.debug('Preview failed', exc_info=True)
                result = exc
            self._results.put((token, result))

    def _poll(self) -> None:
        latest = None
        while True:
            try:
                latest = self._results.get_nowait()
                with self._lock:
                    self._busy -= 1
            except queue.Empty:
                break
        if latest is not None and not self._stopped:
            try:
                self._on_result(*latest)
            except Exception:
                self._widget._root().report_callback_exception(*sys.exc_info())
        with self._lock:
            pending = self._busy > 0
        if pending and not self._stopped:
            self._widget.after(self._poll_ms, self._poll)
        else:
            self._polling = False


def _join(threads, timeout: float) -> bool:
    """Join `threads` within `timeout` seconds overall; True if all of them ended."""
    deadline = time.monotonic() + timeout
    for thread in threads:
        if thread is not threading.current_thread():
            thread.join(max(0.0, deadline - time.monotonic()))
    return not any(thread.is_alive() for thread in threads)
