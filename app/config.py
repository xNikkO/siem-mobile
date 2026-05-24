from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


DEFAULT_SPL = (
    'search index=* "Microsoft-Windows-Sysmon" '
    '("<EventID>1</EventID>" OR "<EventID>1102</EventID>") '
    '| head 200'
)


CONFIG_DIR = Path.home() / ".siem_mobile"
CONFIG_FILE = CONFIG_DIR / "config.json"


DEFAULTS: Dict[str, Any] = {
    "splunk_url": "https://192.168.1.100:8089",
    "username": "",
    "password": "",
    "poll_interval": 30,
    "spl_query": DEFAULT_SPL,
    "auto_monitor": False,
    "earliest_time": "-15m",
    "latest_time": "now",
    "notify_critical": True,
    "notify_warning": True,
    "demo_mode": False,
}


class Config:


    def __init__(self) -> None:
        self.data: Dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
                    user_data = json.load(fh)
                if isinstance(user_data, dict):
                    self.data.update(user_data)
            except (OSError, json.JSONDecodeError) as exc:
                print(f"[config] Failed to load {CONFIG_FILE}: {exc}")

    def save(self) -> None:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2)
            try:
                os.chmod(CONFIG_FILE, 0o600)
            except OSError:
                pass
        except OSError as exc:
            print(f"[config] Failed to save {CONFIG_FILE}: {exc}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def update(self, **kwargs: Any) -> None:
        self.data.update(kwargs)
