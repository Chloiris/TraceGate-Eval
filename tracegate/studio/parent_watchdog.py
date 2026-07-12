from __future__ import annotations

import os
import signal
import threading
import time
from collections.abc import Callable


WATCHDOG_ENV = "TRACEGATE_PARENT_WATCHDOG"
SUPERVISOR_PID_ENV = "TRACEGATE_DESKTOP_PID"


def process_is_alive(parent_pid: int) -> bool:
    if parent_pid <= 1:
        return False
    if os.name == "nt":
        return _windows_process_is_alive(parent_pid)
    try:
        os.kill(parent_pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def parent_process_is_alive(parent_pid: int) -> bool:
    """Return whether the immediate packaged-process parent is still alive."""

    return os.getppid() == parent_pid and process_is_alive(parent_pid)


def _windows_process_is_alive(parent_pid: int) -> bool:
    import ctypes
    from ctypes import wintypes

    synchronize = 0x00100000
    wait_timeout = 0x00000102
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(synchronize, False, parent_pid)
    if not handle:
        return False
    try:
        return kernel32.WaitForSingleObject(handle, 0) == wait_timeout
    finally:
        kernel32.CloseHandle(handle)


def _watch_parent(
    parent_pid: int,
    *,
    supervisor_pid: int | None,
    poll_seconds: float,
    terminate: Callable[[int], object],
) -> None:
    while parent_process_is_alive(parent_pid) and (
        supervisor_pid is None or process_is_alive(supervisor_pid)
    ):
        time.sleep(poll_seconds)
    terminate(0)


def _terminate_current_process(_exit_code: int) -> None:
    os.kill(os.getpid(), signal.SIGTERM)


def start_parent_watchdog() -> threading.Thread | None:
    """Exit a packaged worker when its PyInstaller bootloader parent is killed."""

    if os.environ.get(WATCHDOG_ENV) != "1":
        return None
    parent_pid = os.getppid()
    raw_supervisor_pid = os.environ.get(SUPERVISOR_PID_ENV)
    supervisor_pid = int(raw_supervisor_pid) if raw_supervisor_pid else None
    thread = threading.Thread(
        target=_watch_parent,
        kwargs={
            "parent_pid": parent_pid,
            "supervisor_pid": supervisor_pid,
            "poll_seconds": 0.25,
            "terminate": _terminate_current_process,
        },
        name="tracegate-parent-watchdog",
        daemon=True,
    )
    thread.start()
    return thread
