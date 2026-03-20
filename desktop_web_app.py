"""Flask-based desktop UI launcher for mobile automation testing."""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

from desktop_app.app_factory import create_app
from desktop_app.services_container import DesktopServiceContainer

try:
    import websocket as websocket_client
except Exception:  # pragma: no cover
    websocket_client = None


if getattr(sys, "frozen", False):
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    RUNTIME_ROOT = Path(sys.executable).resolve().parent
else:
    RESOURCE_ROOT = Path(__file__).resolve().parent
    RUNTIME_ROOT = RESOURCE_ROOT

PROJECT_ROOT = RESOURCE_ROOT
REPORTS_ROOT = RUNTIME_ROOT / "reports"
TEST_RESULTS_FILE = REPORTS_ROOT / "test_results.json"
REPORT_HTML_FILE = REPORTS_ROOT / "test_report.html"
RUNTIME_DB_FILE = REPORTS_ROOT / "runtime_state.db"
TASK_LOG_DIR = REPORTS_ROOT / "task-logs"
TASK_REPORT_DIR = REPORTS_ROOT / "task-reports"
REMOTE_WS_LOG_FILE = REPORTS_ROOT / "remote-ws.log"

ADB_BIN = "adb"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 17999


def _load_local_env_file() -> None:
    candidates: list[Path] = [
        RUNTIME_ROOT / ".env",
        RUNTIME_ROOT / "_internal" / ".env",
        RESOURCE_ROOT / ".env",
        RESOURCE_ROOT.parent / ".env",
    ]
    seen: set[Path] = set()
    for env_path in candidates:
        try:
            resolved = env_path.resolve()
        except Exception:
            resolved = env_path
        if resolved in seen:
            continue
        seen.add(resolved)
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)


_load_local_env_file()

APP_CONFIG: dict[str, dict[str, str]] = {
    "lysora": {
        "label": "Lysora",
        "package_name": os.getenv("LYSORA_APP_PACKAGE", "com.lysora.lyapp"),
        "default_test_package": "tests/lysora",
    },
    "ruijieCloud": {
        "label": "RuijieCloud",
        "package_name": os.getenv("RUIJIECLOUD_APP_PACKAGE", "cn.com.ruijie.cloudapp"),
        "default_test_package": "tests/ruijieCloud",
    },
}

_tasks_lock = threading.Lock()
_tasks: dict[str, dict[str, Any]] = {}
_device_running_task: dict[str, str] = {}

services = DesktopServiceContainer(
    resource_root=RESOURCE_ROOT,
    runtime_root=RUNTIME_ROOT,
    project_root=PROJECT_ROOT,
    reports_root=REPORTS_ROOT,
    test_results_file=TEST_RESULTS_FILE,
    report_html_file=REPORT_HTML_FILE,
    runtime_db_file=RUNTIME_DB_FILE,
    task_log_dir=TASK_LOG_DIR,
    task_report_dir=TASK_REPORT_DIR,
    remote_ws_log_file=REMOTE_WS_LOG_FILE,
    app_config=APP_CONFIG,
    adb_bin=ADB_BIN,
    default_host=DEFAULT_HOST,
    default_port=DEFAULT_PORT,
    tasks_lock=_tasks_lock,
    tasks=_tasks,
    device_running_task=_device_running_task,
)

app = create_app(services.build_api_deps())


def _auto_open_browser(url: str) -> None:
    time.sleep(0.8)
    webbrowser.open(url)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--run-pytest":
        import pytest

        exit_code = int(pytest.main(sys.argv[2:]))
        raise SystemExit(exit_code)

    services.init_runtime_db()
    services.start_remote_ws_if_needed(websocket_client)
    host = (os.getenv("DESKTOP_WEB_HOST") or DEFAULT_HOST).strip() or DEFAULT_HOST
    preferred_port = services.env_int("DESKTOP_WEB_PORT", DEFAULT_PORT)
    auto_port_fallback = services.env_bool("DESKTOP_WEB_AUTO_PORT_FALLBACK", False)
    port = services.get_free_port(host, preferred_port) if auto_port_fallback else preferred_port
    url = f"http://{host}:{port}"
    threading.Thread(target=_auto_open_browser, args=(url,), daemon=True).start()
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()

