from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


os.environ.setdefault("KIVY_NO_ARGS", "1")

ROOT = Path(__file__).resolve().parent
_LAUNCHER_FLAGS = frozenset({"--demo", "--setup-only"})


def _venv_python() -> Path | None:
    if sys.platform == "win32":
        candidate = ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = ROOT / ".venv" / "bin" / "python"
    return candidate if candidate.is_file() else None


def _pip_install() -> None:
    req = ROOT / "requirements.txt"
    print("[run] Installing dependencies from requirements.txt ...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        cwd=str(ROOT),
    )
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", str(req)],
        cwd=str(ROOT),
    )


def _ensure_dependencies() -> None:
    try:
        import kivy
        import requests
    except ImportError:
        _pip_install()


def _maybe_create_venv() -> None:
    if _venv_python() is not None:
        return
    print("[run] Creating virtual environment (.venv) ...")
    subprocess.check_call([sys.executable, "-m", "venv", str(ROOT / ".venv")], cwd=str(ROOT))
    vp = _venv_python()
    if vp is None:
        return
    subprocess.check_call([str(vp), "-m", "pip", "install", "--upgrade", "pip"], cwd=str(ROOT))
    subprocess.check_call(
        [str(vp), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")],
        cwd=str(ROOT),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch SIEM-Mobile SOC dashboard",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Offline demo with synthetic Sysmon events (no Splunk)",
    )
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Install dependencies and exit",
    )
    args = parser.parse_args()

    sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if a not in _LAUNCHER_FLAGS]

    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))

    _maybe_create_venv()
    _ensure_dependencies()

    if args.setup_only:
        print("[run] Setup complete.")
        return 0

    if args.demo:
        os.environ["SIEM_DEMO_MODE"] = "1"
        print("[run] DEMO mode - Splunk not required. Auto-monitor will start.")

    from main import SiemApp

    SiemApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
