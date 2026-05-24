from __future__ import annotations

import json
import threading
import time
from typing import Callable, Optional

import requests
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


EventCallback = Callable[[dict], None]
StatusCallback = Callable[[bool, str], None]


def _short_exc(exc: Exception, limit: int = 120) -> str:


    msg = str(exc)
    if "(Caused by " in msg:
        inner = msg.split("(Caused by ", 1)[1].rstrip(")").strip()

        if "(" in inner and inner.endswith(")"):
            cls, _, rest = inner.partition("(")
            rest = rest.rstrip(")").strip("'\"")
            msg = f"{cls.strip()}: {rest}" if rest else cls.strip()
        else:
            msg = inner

    msg = msg.replace("\r", " ").replace("\n", " ").strip()
    if len(msg) > limit:
        msg = msg[: limit - 1] + "\u2026"
    return msg or "unknown error"


class SplunkClient:


    CONNECT_TIMEOUT = 10
    READ_TIMEOUT = 25
    STREAM_MAX_SECONDS = 30

    def __init__(self, config) -> None:
        self.config = config
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_poll_at: float = 0.0
        self._poll_in_progress = False


    def _build_url(self, path: str) -> str:
        base = (self.config.get("splunk_url") or "").rstrip("/")
        if not base:
            raise ValueError("splunk_url is empty - configure it in Settings")
        return f"{base}{path}"

    def _auth(self):
        user = (self.config.get("username") or "").strip()
        password = self.config.get("password") or ""
        if not user and not password:
            return None
        if user.lower() == "admin" and not password:
            return None
        return (user, password)


    def _index_event_summary(self, limit: int = 4) -> str:
        try:
            url = self._build_url("/services/data/indexes?output_mode=json&count=0")
            resp = requests.get(
                url,
                auth=self._auth(),
                verify=False,
                timeout=(self.CONNECT_TIMEOUT, self.READ_TIMEOUT),
            )
            if resp.status_code != 200:
                return ""
            data = resp.json()
            rows: list[tuple[str, int]] = []
            for entry in data.get("entry", []):
                name = entry.get("name") or ""
                if not name or name.startswith("_"):
                    continue
                content = entry.get("content") or {}
                try:
                    total = int(content.get("totalEventCount") or 0)
                except (TypeError, ValueError):
                    total = 0
                if total > 0:
                    rows.append((name, total))
            if not rows:
                return "indexes: (no events yet)"
            rows.sort(key=lambda item: item[1], reverse=True)
            parts = [f"{name}={count}" for name, count in rows[:limit]]
            return "indexes: " + ", ".join(parts)
        except Exception:
            return ""

    def test_connection(self, on_status: StatusCallback) -> None:


        try:
            url = self._build_url("/services/server/info?output_mode=json")
        except ValueError as exc:
            on_status(False, str(exc))
            return

        try:
            resp = requests.get(
                url,
                auth=self._auth(),
                verify=False,
                timeout=(self.CONNECT_TIMEOUT, self.READ_TIMEOUT),
            )
        except requests.exceptions.SSLError as exc:
            on_status(False, f"SSL error: {_short_exc(exc)}")
            return
        except requests.exceptions.ConnectionError as exc:
            on_status(False, f"Cannot reach Splunk: {_short_exc(exc)}")
            return
        except requests.exceptions.Timeout:
            on_status(False, "Timeout - is Splunk reachable on 8089?")
            return
        except Exception as exc:
            on_status(False, f"{type(exc).__name__}: {_short_exc(exc)}")
            return

        if resp.status_code == 401:
            on_status(False, "401 Unauthorized - wrong username/password")
            return
        if resp.status_code != 200:
            on_status(False, f"HTTP {resp.status_code}: {resp.text[:200]}")
            return


        version = "?"
        try:
            data = resp.json()
            version = data["entry"][0]["content"].get("version", "?")
        except Exception:
            pass

        idx = self._index_event_summary()
        msg = f"Connected (Splunk {version})"
        if idx:
            msg = f"{msg} | {idx}"
        on_status(True, msg)

    def query_once(
        self,
        on_event: EventCallback,
        on_status: StatusCallback,
    ) -> None:


        self._poll_in_progress = True
        try:
            try:
                url = self._build_url("/services/search/jobs/export")
            except ValueError as exc:
                on_status(False, str(exc))
                return

            requested_earliest = (self.config.get("earliest_time") or "").strip() or "-15m"
            effective_earliest = requested_earliest
            if requested_earliest in (
                "-1m", "-30s", "-15s", "-10s", "-5s", "-2m", "-5m", "now", "rt"
            ):
                effective_earliest = "-1h"

            requested_latest = (self.config.get("latest_time") or "").strip() or "now"
            effective_latest = requested_latest
            if requested_latest in ("now", "", "+0s"):
                effective_latest = "+15m"

            payload = {
                "search": self.config.get("spl_query"),
                "earliest_time": effective_earliest,
                "latest_time": effective_latest,
                "output_mode": "json",
            }

            try:
                resp = requests.post(
                    url,
                    data=payload,
                    auth=self._auth(),
                    verify=False,
                    stream=True,
                    timeout=(self.CONNECT_TIMEOUT, self.READ_TIMEOUT),
                )
            except requests.exceptions.SSLError as exc:
                on_status(False, f"SSL error: {_short_exc(exc)}")
                return
            except requests.exceptions.ConnectionError as exc:
                on_status(False, f"Cannot reach Splunk: {_short_exc(exc)}")
                return
            except requests.exceptions.Timeout:
                on_status(False, "Timeout")
                return
            except Exception as exc:
                on_status(False, f"{type(exc).__name__}: {_short_exc(exc)}")
                return

            with resp:
                if resp.status_code == 401:
                    on_status(False, "401 Unauthorized - check credentials")
                    return
                if resp.status_code != 200:
                    snippet = resp.text[:200] if resp.text else ""
                    on_status(False, f"HTTP {resp.status_code}: {snippet}")
                    return

                event_count = 0
                splunk_msgs: list[str] = []
                deadline = time.monotonic() + self.STREAM_MAX_SECONDS
                try:
                    for raw_line in resp.iter_lines(decode_unicode=True):
                        if time.monotonic() > deadline:
                            on_status(False, "Splunk stream timeout - retrying")
                            break
                        if self._stop_event.is_set():
                            break
                        if not raw_line:
                            continue
                        if raw_line.startswith("\ufeff"):
                            raw_line = raw_line.lstrip("\ufeff")
                        try:
                            obj = json.loads(raw_line)
                        except json.JSONDecodeError:
                            continue

                        for msg in obj.get("messages") or []:
                            text = (msg.get("text") or "").strip()
                            if not text:
                                continue
                            level = (msg.get("type") or "").upper()
                            if level in ("FATAL", "ERROR", "WARN"):
                                splunk_msgs.append(text[:120])

                        result = obj.get("result")
                        if not result:
                            continue

                        on_event(result)
                        event_count += 1
                except requests.exceptions.ChunkedEncodingError as exc:
                    on_status(False, f"Stream broken: {exc}")
                    return
                except Exception as exc:
                    on_status(False, f"Parse error: {type(exc).__name__}: {exc}")
                    return

                window_note = ""
                widened_bits = []
                if effective_earliest != requested_earliest:
                    widened_bits.append(f"earliest {requested_earliest}->{effective_earliest}")
                if effective_latest != requested_latest:
                    widened_bits.append(f"latest {requested_latest}->{effective_latest}")
                if widened_bits:
                    window_note = " [auto: " + ", ".join(widened_bits) + "]"
                if event_count:
                    on_status(True, f"OK ({event_count} from Splunk){window_note}")
                elif splunk_msgs:
                    on_status(False, splunk_msgs[0])
                else:
                    spl = (self.config.get("spl_query") or "")
                    hint = ""
                    if "index=main" in spl.replace(" ", ""):
                        hint = " - SPL uses index=main; try index=endpoint"
                    on_status(
                        True,
                        f"OK (0 from Splunk){window_note}{hint}",
                    )
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
                    try:
                        on_status(False, f"Poll error: {_short_exc(exc)}")
                    except Exception:
                        pass
                    self._poll_in_progress = False
                    self._last_poll_at = time.monotonic()
                interval = max(5, int(self.config.get("poll_interval") or 30))
                for _ in range(interval):
                    if self._stop_event.is_set():
                        return
                    time.sleep(1)

        self._thread = threading.Thread(
            target=worker,
            name="SplunkPoller",
            daemon=True,
        )
        self._thread.start()

    def stop_polling(self) -> None:
        self._stop_event.set()
        t = self._thread
        if t is not None and t.is_alive():
            t.join(timeout=3.0)
        self._thread = None


        self._poll_in_progress = False
        self._last_poll_at = 0.0

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
