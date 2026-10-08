"""The guard that refuses a stabilization the computer has no memory for (`gui.tasks`)."""

from types import SimpleNamespace

import pytest

from gui import tasks


def test_the_memory_is_known_on_this_platform():
    # without it the guard is silently off (it was on macOS until 2026-10-08)
    available = tasks.available_memory_bytes()
    assert available is not None and available > 0


def test_a_full_recording_is_refused_on_an_8_gb_computer(monkeypatch):
    # FP01_Qföre_22-Oct-2019_08-16-35: 5729 frames of 640 x 480, about 28 GB to stabilize
    monkeypatch.setattr(tasks, 'probe_video', lambda path: SimpleNamespace(frame_count=5729, width=640, height=480))
    monkeypatch.setattr(tasks, 'available_memory_bytes', lambda: 8 * 1024 ** 3)
    with pytest.raises(MemoryError, match='28.2 GB'):
        tasks.check_stabilization_memory('recording.avi')
