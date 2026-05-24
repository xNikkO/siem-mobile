from __future__ import annotations

import hashlib
import re
import time
from collections import deque
from datetime import datetime, timezone
from typing import Callable, Deque, List, Optional, Tuple, Union


BURST_WINDOW_SEC = 90


def splunk_time_to_local(value: Union[str, int, float, None]) -> str:

    if value is None or value == "":
        return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")

    s = str(value).strip()
    if not s:
        return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")

    if re.match(r"^\d+(\.\d+)?$", s):
        dt = datetime.fromtimestamp(float(s), tz=timezone.utc)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")


    normalized = s.replace("Z", "+00:00")
    if " " in normalized and "T" not in normalized:
        normalized = normalized.replace(" ", "T", 1)

    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    clean = re.sub(r"\.\d+", "", s).replace("T", " ")[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
        try:
            dt = datetime.strptime(clean, fmt)
            return dt.replace(tzinfo=timezone.utc).astimezone().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except ValueError:
            continue

    return clean[:19]


_SYSMON_DATA_RE = re.compile(
    r"<Data\s+Name=['\"]([^'\"]+)['\"]\s*>([^<]*)</Data>",
    re.IGNORECASE,
)


def _parse_sysmon_data(raw: str) -> dict:

    if not isinstance(raw, str) or "<Data" not in raw:
        return {}
    out: dict = {}
    for match in _SYSMON_DATA_RE.finditer(raw):
        key = match.group(1).strip()
        val = match.group(2).strip()
        if key and val and key not in out:
            out[key] = val
    return out


def _extract_time_from_result(result: dict) -> Union[str, int, float, None]:

    for key in ("_time", "time", "TimeGenerated", "TimeCreated"):
        val = result.get(key)
        if val is not None and val != "":
            return val
    raw = result.get("_raw", "")
    if isinstance(raw, str):
        m = re.search(
            r"(?i)SystemTime=['\"]([^'\"]+)['\"]|"
            r"TimeCreated=['\"]([^'\"]+)['\"]|"
            r"UtcTime=['\"]([^'\"]+)['\"]",
            raw,
        )
        if m:
            return next(g for g in m.groups() if g)
    return None


_PROCESS_EVENT_CODES = frozenset({"1"})
_SECURITY_EVENT_CODES = frozenset({"1", "1102"})


_ENCODED_PS_RE = re.compile(
    r"(?:"
    r"(?:powershell|pwsh)(?:\d*\.exe)?[^\r\n]{0,240}?(?:"
    r"-(?:enc(?:odedcommand)?|e)\b\s+[a-z0-9+/=]{8,}|"
    r"-(?:enc(?:odedcommand)?|e)\b"
    r")"
    r"|(?:tobase64string|frombase64string|"
    r"\[convert\]::tobase64string|encoding\]::unicode\.getbytes|"
    r"getbytes\(\$)"
    r")",
    re.I,
)

_IEX_RE = re.compile(
    r"(?:downloadstring|downloadfile|invoke-webrequest|iwr\s|"
    r"\biex\b|invoke-expression|i\s*ex\s*\(|start-bitstransfer|"
    r"new-object\s+net\.webclient)",
    re.I,
)

_CRED_DUMP_RE = re.compile(
    r"mimikatz|sekurlsa|lsadump|procdump.*lsass|"
    r"comsvcs\.dll.*minidump|\blsass\b.*dump",
    re.I,
)

_SUSPICIOUS_PS_RE = re.compile(
    r"(?:powershell|pwsh)(?:\d*\.exe)?[^\r\n]{0,240}(?:"
    r"-(?:nop|noprofile|w\s+hidden|windowstyle\s+hidden|"
    r"ep\s+bypass|executionpolicy\s+bypass|"
    r"enc(?:odedcommand)?|e)\b\s+[a-z0-9+/=]{8,}|"
    r"-(?:nop|noprofile|w\s+hidden|windowstyle\s+hidden|"
    r"ep\s+bypass|executionpolicy\s+bypass)"
    r")",
    re.I,
)


_DETECTION_RULES: Tuple[Tuple[str, str, re.Pattern], ...] = (
    (
        "Event Log Cleared",
        "CRITICAL",
        re.compile(
            r"eventcode[\"'=:\s]+1102|event\s+log.*cleared|audit\s+log\s+was\s+cleared",
            re.I,
        ),
    ),
    (
        "Encoded PowerShell",
        "CRITICAL",
        _ENCODED_PS_RE,
    ),
    (
        "PowerShell Download / IEX",
        "CRITICAL",
        _IEX_RE,
    ),
    (
        "Credential Dumping Attempt",
        "CRITICAL",
        _CRED_DUMP_RE,
    ),
    (
        "Shadow Copy Deletion",
        "CRITICAL",
        re.compile(
            r"vssadmin(?:\d*\.exe)?[^\r\n]{0,80}delete\s+shadows|"
            r"wmic[^\r\n]{0,80}shadowcopy\s+delete|"
            r"bcdedit[^\r\n]{0,80}recoveryenabled\s+no",
            re.I,
        ),
    ),
    (
        "Rundll32 LOLBin",
        "CRITICAL",
        re.compile(
            r"rundll32(?:\d*\.exe)?[^\r\n]{0,120}(?:javascript:|vbscript:)",
            re.I,
        ),
    ),
    (
        "Regsvr32 Squiblydoo",
        "WARNING",
        re.compile(
            r"regsvr32(?:\d*\.exe)?[^\r\n]{0,80}(?:/s|/i:|scrobj)",
            re.I,
        ),
    ),
    (
        "Certutil Decode",
        "WARNING",
        re.compile(
            r"certutil(?:\d*\.exe)?[^\r\n]{0,80}(?:-decode|-urlcache|-split)",
            re.I,
        ),
    ),
    (
        "BITS Transfer",
        "WARNING",
        re.compile(
            r"bitsadmin(?:\d*\.exe)?|start-bitstransfer",
            re.I,
        ),
    ),
    (
        "WMIC Remote Execution",
        "WARNING",
        re.compile(
            r"wmic(?:\d*\.exe)?[^\r\n]{0,80}process\s+call\s+create",
            re.I,
        ),
    ),
    (
        "Scheduled Task Created",
        "WARNING",
        re.compile(
            r"schtasks(?:\d*\.exe)?[^\r\n]{0,80}/create",
            re.I,
        ),
    ),
    (
        "Local Account Created",
        "WARNING",
        re.compile(
            r"net(?:1)?\.exe[^\r\n]{0,80}\buser\b[^\r\n]{0,40}/add",
            re.I,
        ),
    ),
    (
        "CMD /c Execution",
        "WARNING",
        re.compile(
            r"cmd(?:\d*|\.\d*)?\.exe[^\r\n]{0,80}(?:/c|/k)\s",
            re.I,
        ),
    ),
    (
        "Suspicious PowerShell",
        "WARNING",
        _SUSPICIOUS_PS_RE,
    ),
)


_BENIGN_HINTS = re.compile(
    r"\\windows\\system32\\svchost\.exe|"
    r"\\windows\\system32\\runtimebroker\.exe|"
    r"\\windows\\system32\\searchindexer\.exe|"
    r"\\program files\\.*\\update\.exe",
    re.I,
)


class Alert:
    SEVERITY_CRITICAL = "CRITICAL"
    SEVERITY_WARNING = "WARNING"
    SEVERITY_INFO = "INFO"

    _CTX_FIELDS = (
        "CommandLine",
        "commandline",
        "ParentCommandLine",
        "parentcommandline",
        "Image",
        "image",
        "ParentImage",
        "parentimage",
        "ProcessCommandLine",
        "ScriptBlockText",
        "scriptblocktext",
        "_raw",
    )

    def __init__(self, result: dict) -> None:
        self.raw: dict = result

        time_val = _extract_time_from_result(result)
        self.time_raw = time_val
        self.time_display = splunk_time_to_local(time_val)
        self.host: str = (
            result.get("Computer")
            or result.get("ComputerName")
            or result.get("host")
            or "unknown"
        )
        self.user: str = (
            result.get("User")
            or result.get("user")
            or "unknown"
        )
        self.image: str = (
            result.get("Image")
            or result.get("process")
            or ""
        )
        self.command_line: str = (
            result.get("CommandLine")
            or result.get("commandline")
            or ""
        )
        self.parent_command_line: str = (
            result.get("ParentCommandLine")
            or result.get("parentcommandline")
            or ""
        )

        ev_code = (
            result.get("EventCode")
            or result.get("EventID")
            or result.get("event_id")
        )
        self.event_code: str = str(ev_code) if ev_code else ""

        _raw = result.get("_raw", "")
        sysmon_data: dict = {}
        if isinstance(_raw, str) and _raw:
            sysmon_data = _parse_sysmon_data(_raw)

            if not self.event_code:
                ev = sysmon_data.get("EventID") or sysmon_data.get("EventCode")
                if not ev:
                    m = re.search(
                        r"<EventID[^>]*>(\d+)</EventID>|"
                        r"EventCode[=>: ]+(\d+)|"
                        r"EventID[=>: ]+(\d+)",
                        _raw,
                        re.IGNORECASE,
                    )
                    if m:
                        ev = next(g for g in m.groups() if g)
                if ev:
                    self.event_code = str(ev)

            if not self.command_line:
                self.command_line = sysmon_data.get("CommandLine", "")
                if not self.command_line:
                    m = re.search(r"(?i)CommandLine[:=]\s*([^\r\n]+)", _raw)
                    if m:
                        self.command_line = m.group(1).strip()

            if not self.parent_command_line:
                self.parent_command_line = sysmon_data.get(
                    "ParentCommandLine", ""
                )
                if not self.parent_command_line:
                    m = re.search(
                        r"(?i)ParentCommandLine[:=]\s*([^\r\n]+)", _raw
                    )
                    if m:
                        self.parent_command_line = m.group(1).strip()

            if not self.image:
                self.image = sysmon_data.get("Image", "")
                if not self.image:
                    m = re.search(r"(?i)Image[:=]\s*([^\r\n]+)", _raw)
                    if m:
                        self.image = m.group(1).strip()

            if self.user == "unknown":
                user_val = sysmon_data.get("User")
                if user_val:
                    self.user = user_val
                else:
                    m = re.search(r"(?i)User[:=]\s*([^\r\n]+)", _raw)
                    if m:
                        self.user = m.group(1).strip()

            if self.host == "unknown":
                m = re.search(
                    r"<Computer[^>]*>([^<]+)</Computer>",
                    _raw,
                    re.IGNORECASE,
                )
                if m:
                    self.host = m.group(1).strip()

        self.sysmon_data: dict = sysmon_data
        self.target_object: str = sysmon_data.get("TargetObject", "")
        self.details: str = sysmon_data.get("Details", "")
        self.event_type: str = sysmon_data.get("EventType", "")

        self.context_lower: str = self._build_context_lower(result)
        self.detection_context: str = self._build_detection_context(result)
        self._rule_match = self._match_rules()
        self.name: str = self._derive_name()
        self.severity: str = self._derive_severity()
        self.fingerprint: str = self._fingerprint()

    def _build_detection_context(self, result: dict) -> str:
        chunks: List[str] = []
        for key in (
            "CommandLine",
            "commandline",
            "ParentCommandLine",
            "parentcommandline",
            "ScriptBlockText",
            "scriptblocktext",
            "ProcessCommandLine",
        ):
            val = result.get(key)
            if val and isinstance(val, str):
                chunks.append(val)
        if self.command_line:
            chunks.append(self.command_line)
        if self.parent_command_line:
            chunks.append(self.parent_command_line)
        script = self.sysmon_data.get("ScriptBlockText", "")
        if script:
            chunks.append(script)
        return " ".join(chunks).lower()

    def is_actionable(self) -> bool:
        if self._rule_match:
            return True
        if self.event_code in _SECURITY_EVENT_CODES:
            return True
        if self.event_code or self.sysmon_data:
            return True
        return False

    def _build_context_lower(self, result: dict) -> str:
        chunks: List[str] = []
        for key in self._CTX_FIELDS:
            val = result.get(key)
            if val and isinstance(val, str):
                chunks.append(val)
        if self.command_line and self.command_line not in chunks:
            chunks.append(self.command_line)
        if self.parent_command_line:
            chunks.append(self.parent_command_line)
        if self.image:
            chunks.append(self.image)
        if self.event_code:
            chunks.append(f"EventCode={self.event_code}")
        return " ".join(chunks).lower()

    def _match_rules(self) -> Optional[Tuple[str, str]]:

        if self.event_code == "1102":
            return ("Event Log Cleared", Alert.SEVERITY_CRITICAL)

        ctx = self.detection_context.strip()
        if not ctx and self.event_code not in _PROCESS_EVENT_CODES:
            return None

        best: Optional[Tuple[str, str, int]] = None
        severity_rank = {
            Alert.SEVERITY_CRITICAL: 3,
            Alert.SEVERITY_WARNING: 2,
            Alert.SEVERITY_INFO: 1,
        }

        for name, severity, pattern in _DETECTION_RULES:
            if name == "Suspicious PowerShell" and self.event_code not in _PROCESS_EVENT_CODES:
                continue
            if not pattern.search(ctx):
                continue
            rank = severity_rank.get(severity, 0)
            if best is None or rank > best[2]:
                best = (name, severity, rank)

        if best:
            return (best[0], best[1])
        return None

    def _derive_name(self) -> str:
        if self._rule_match:
            return self._rule_match[0]

        if self.event_code == "1":
            return "Process Create"
        return f"Event ID: {self.event_code or 'Unknown'}"

    def _derive_severity(self) -> str:
        if self._rule_match:
            return self._rule_match[1]

        ctx = self.detection_context

        if self.event_code == "1102":
            return Alert.SEVERITY_CRITICAL

        if _ENCODED_PS_RE.search(ctx):
            return Alert.SEVERITY_CRITICAL

        if _IEX_RE.search(ctx) or _CRED_DUMP_RE.search(ctx):
            return Alert.SEVERITY_CRITICAL

        if re.search(
            r"cmd(?:\d*|\.\d*)?\.exe.*/[ck]\s|rundll32|regsvr32|"
            r"certutil|bitsadmin|wmic|schtasks|net\d*\.exe.*user",
            ctx,
            re.I,
        ):
            return Alert.SEVERITY_WARNING

        if self.event_code == "1":
            if _BENIGN_HINTS.search(ctx):
                return Alert.SEVERITY_INFO
            if _SUSPICIOUS_PS_RE.search(ctx):
                return Alert.SEVERITY_WARNING

        return Alert.SEVERITY_INFO

    def _dedupe_key(self) -> str:

        cmd = (self.command_line or self.parent_command_line or "").lower()
        cmd = re.sub(r"\s+", " ", cmd).strip()

        cmd = re.sub(
            r"-enc(?:odedcommand)?\s+[a-z0-9+/=]{16,}",
            "-enc <payload>",
            cmd,
            flags=re.I,
        )
        return (
            f"{self.host}|{self.name}|{self.severity}|"
            f"{self.event_code}|{cmd[:280]}"
        )

    def _fingerprint(self) -> str:
        return hashlib.md5(
            self._dedupe_key().encode("utf-8", errors="ignore")
        ).hexdigest()

    def short_command(self, length: int = 80) -> str:
        cmd = self.display_command(short=True)
        if len(cmd) <= length:
            return cmd
        return cmd[: length - 1] + "\u2026"

    def display_command(self, short: bool = False) -> str:

        cmd = (self.command_line or self.parent_command_line or "").strip()
        if cmd:
            return cmd

        sd = self.sysmon_data
        if sd:
            ev = self.event_code or sd.get("EventID") or "?"
            if ev == "13" or self.target_object or self.details:
                parts = []
                if self.event_type:
                    parts.append(self.event_type)
                if self.target_object:
                    parts.append(f"key={self.target_object}")
                if self.details and not short:
                    parts.append(f"value={self.details}")
                if parts:
                    return "Registry " + "  ".join(parts)
            if ev == "11":
                tgt = sd.get("TargetFilename", "")
                if tgt:
                    return f"File create  {tgt}"
            if ev == "3":
                src = sd.get("SourceIp", "")
                dst = sd.get("DestinationIp", "")
                port = sd.get("DestinationPort", "")
                if src or dst:
                    return f"Net connect  {src} \u2192 {dst}:{port}"
            if ev == "1102":
                return "Windows Security log cleared"
            if self.image:
                return self.image
        return "(no command line / non-process event)"

    def pretty_time(self) -> str:
        return self.time_display


class AlertManager:


    MAX_ALERTS = 500

    def __init__(self) -> None:
        self.alerts: Deque[Alert] = deque(maxlen=self.MAX_ALERTS)
        self._fingerprints: set = set()
        self._burst_seen: dict[str, float] = {}
        self._listeners: List[Callable[[], None]] = []
        self.last_poll_message: str = ""
        self.last_poll_ok: Optional[bool] = None

    def subscribe(self, callback: Callable[[], None]) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def _notify(self) -> None:
        for cb in list(self._listeners):
            try:
                cb()
            except Exception as exc:
                print(f"[alert_manager] listener raised {exc}")

    def set_poll_status(self, ok: bool, message: str) -> None:
        self.last_poll_ok = ok
        self.last_poll_message = message
        self._notify()

    def _is_burst_duplicate(self, alert: Alert) -> bool:

        burst_key = f"{alert.host}|{alert.name}|{alert.severity}"
        now = time.monotonic()
        last = self._burst_seen.get(burst_key)
        if last is not None and (now - last) < BURST_WINDOW_SEC:
            return True
        self._burst_seen[burst_key] = now
        if len(self._burst_seen) > self.MAX_ALERTS * 2:
            cutoff = now - BURST_WINDOW_SEC * 2
            self._burst_seen = {
                k: v for k, v in self._burst_seen.items() if v >= cutoff
            }
        return False

    def add(self, result: dict):
        alert = Alert(result)
        if not alert.is_actionable():
            return None
        if alert.fingerprint in self._fingerprints:
            return None
        if self._is_burst_duplicate(alert):
            return None
        self._fingerprints.add(alert.fingerprint)
        self.alerts.appendleft(alert)
        if len(self._fingerprints) > self.MAX_ALERTS * 4:
            self._fingerprints = {a.fingerprint for a in self.alerts}
        self._notify()
        return alert

    def clear(self) -> None:
        self.alerts.clear()
        self._fingerprints.clear()
        self._burst_seen.clear()
        self._notify()

    def critical_count(self) -> int:
        return sum(
            1 for a in self.alerts if a.severity == Alert.SEVERITY_CRITICAL
        )

    def warning_count(self) -> int:
        return sum(
            1 for a in self.alerts if a.severity == Alert.SEVERITY_WARNING
        )

    def info_count(self) -> int:
        return sum(1 for a in self.alerts if a.severity == Alert.SEVERITY_INFO)

    def total(self) -> int:
        return len(self.alerts)

    def latest(self) -> Optional[Alert]:
        return self.alerts[0] if self.alerts else None
