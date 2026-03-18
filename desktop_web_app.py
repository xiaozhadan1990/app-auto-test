"""Flask-based desktop UI launcher for mobile automation testing."""
from __future__ import annotations

import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
import json
import platform
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import Flask, jsonify, request, send_file, send_from_directory

try:
    import websocket as websocket_client
except Exception:  # pragma: no cover
    websocket_client = None


if getattr(sys, "frozen", False):
    # PyInstaller one-dir resources are under _internal (sys._MEIPASS).
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    RUNTIME_ROOT = Path(sys.executable).resolve().parent
else:
    RESOURCE_ROOT = Path(__file__).resolve().parent
    RUNTIME_ROOT = RESOURCE_ROOT

PROJECT_ROOT = RESOURCE_ROOT
UI_HTML_FILE = RESOURCE_ROOT / "ui" / "index.html"
UI_ASSETS_DIR = RESOURCE_ROOT / "ui" / "assets"
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


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _safe_display_path(path: Path) -> str:
    p = path.resolve()
    for base in (RUNTIME_ROOT, RESOURCE_ROOT, PROJECT_ROOT):
        try:
            return p.relative_to(base.resolve()).as_posix()
        except Exception:
            continue
    return str(path)


def _db_conn() -> sqlite3.Connection:
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(RUNTIME_DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _init_runtime_db() -> None:
    conn = _db_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS device_runtime_status (
                device_serial TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                task_id TEXT,
                message TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_run_history (
                task_id TEXT PRIMARY KEY,
                device_serial TEXT NOT NULL,
                app_key TEXT,
                suite TEXT,
                test_packages TEXT,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                pytest_exit_code INTEGER,
                allure_exit_code INTEGER,
                error TEXT,
                log_path TEXT,
                allure_output TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_report_summary (
                task_id TEXT PRIMARY KEY,
                session_start TEXT,
                session_end TEXT,
                total INTEGER NOT NULL,
                passed INTEGER NOT NULL,
                failed INTEGER NOT NULL,
                skipped INTEGER NOT NULL,
                total_duration REAL NOT NULL,
                pass_rate REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_report_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                case_index INTEGER NOT NULL,
                node_id TEXT,
                name TEXT,
                status TEXT,
                duration REAL,
                app TEXT,
                screenshot TEXT,
                video TEXT,
                error_message TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_report_cases_task_id ON task_report_cases(task_id)")
        conn.commit()
    finally:
        conn.close()


def _set_device_status(device_serial: str, status: str, task_id: str | None = None, message: str = "") -> None:
    conn = _db_conn()
    try:
        conn.execute(
            """
            INSERT INTO device_runtime_status(device_serial, status, task_id, message, updated_at)
            VALUES(?, ?, ?, ?, datetime('now', 'localtime'))
            ON CONFLICT(device_serial) DO UPDATE SET
              status=excluded.status,
              task_id=excluded.task_id,
              message=excluded.message,
              updated_at=excluded.updated_at
            """,
            (device_serial, status, task_id, message),
        )
        conn.commit()
    finally:
        conn.close()


def _get_device_status(device_serial: str) -> dict[str, Any]:
    conn = _db_conn()
    try:
        row = conn.execute(
            "SELECT device_serial, status, task_id, message, updated_at FROM device_runtime_status WHERE device_serial=?",
            (device_serial,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return {
            "device_serial": device_serial,
            "status": "idle",
            "task_id": None,
            "message": "",
            "updated_at": None,
        }
    return dict(row)


def _ensure_task_log_dir() -> None:
    TASK_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _task_report_paths(task_id: str) -> tuple[Path, Path]:
    base = TASK_REPORT_DIR / task_id
    return base / "test_results.json", base / "test_report.html"


def _task_report_url(task_id: str) -> str:
    return f"/api/task_report/{task_id}"


def _report_asset_url(rel_path: str | None) -> str | None:
    value = (rel_path or "").strip()
    if not value:
        return None
    return f"/api/report_asset?path={urllib.parse.quote(value)}"


def _task_has_report(task_id: str) -> bool:
    _, report_file = _task_report_paths(task_id)
    return report_file.exists()


def _task_has_report_data(task_id: str) -> bool:
    conn = _db_conn()
    try:
        row = conn.execute("SELECT task_id FROM task_report_summary WHERE task_id=?", (task_id,)).fetchone()
    finally:
        conn.close()
    return row is not None


def _save_task_report_to_db(task_id: str, results_file: Path) -> bool:
    if not results_file.exists():
        return False
    try:
        data = json.loads(results_file.read_text(encoding="utf-8"))
    except Exception:
        return False

    tests = data.get("tests", [])
    if not isinstance(tests, list):
        tests = []
    total = int(data.get("total", len(tests)) or 0)
    passed = int(data.get("passed", 0) or 0)
    failed = int(data.get("failed", 0) or 0)
    skipped = int(data.get("skipped", 0) or 0)
    total_duration = float(sum((t.get("duration", 0) or 0) for t in tests))
    pass_rate = (passed / total * 100.0) if total > 0 else 0.0

    conn = _db_conn()
    try:
        conn.execute("DELETE FROM task_report_cases WHERE task_id=?", (task_id,))
        conn.execute("DELETE FROM task_report_summary WHERE task_id=?", (task_id,))
        conn.execute(
            """
            INSERT INTO task_report_summary(
                task_id, session_start, session_end, total, passed, failed, skipped, total_duration, pass_rate, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """,
            (
                task_id,
                str(data.get("session_start") or ""),
                str(data.get("session_end") or ""),
                total,
                passed,
                failed,
                skipped,
                total_duration,
                pass_rate,
            ),
        )
        for idx, case in enumerate(tests, start=1):
            conn.execute(
                """
                INSERT INTO task_report_cases(
                    task_id, case_index, node_id, name, status, duration, app, screenshot, video, error_message
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    idx,
                    str(case.get("node_id") or ""),
                    str(case.get("name") or ""),
                    str(case.get("status") or ""),
                    float(case.get("duration", 0) or 0),
                    str(case.get("app") or ""),
                    str(case.get("screenshot") or ""),
                    str(case.get("video") or ""),
                    str(case.get("error_message") or ""),
                ),
            )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def _get_task_report_data(task_id: str) -> dict[str, Any] | None:
    conn = _db_conn()
    try:
        summary_row = conn.execute("SELECT * FROM task_report_summary WHERE task_id=?", (task_id,)).fetchone()
        if not summary_row:
            return None
        case_rows = conn.execute(
            "SELECT * FROM task_report_cases WHERE task_id=? ORDER BY case_index ASC",
            (task_id,),
        ).fetchall()
    finally:
        conn.close()

    summary = dict(summary_row)
    cases = [dict(r) for r in case_rows]
    for case in cases:
        case["screenshot_url"] = _report_asset_url(str(case.get("screenshot") or ""))
        case["video_url"] = _report_asset_url(str(case.get("video") or ""))
    return {"summary": summary, "tests": cases}


def _insert_task_history(
    task_id: str,
    device: str,
    app_key: str,
    suite: str,
    test_packages: list[str],
    log_path: str,
) -> None:
    conn = _db_conn()
    try:
        conn.execute(
            """
            INSERT INTO task_run_history(
              task_id, device_serial, app_key, suite, test_packages, status, start_time, log_path
            ) VALUES(?, ?, ?, ?, ?, 'running', datetime('now', 'localtime'), ?)
            """,
            (task_id, device, app_key, suite, json.dumps(test_packages, ensure_ascii=False), log_path),
        )
        conn.commit()
    finally:
        conn.close()


def _update_task_history(
    task_id: str,
    status: str,
    pytest_exit_code: int | None = None,
    allure_exit_code: int | None = None,
    error: str | None = None,
    allure_output: str | None = None,
) -> None:
    conn = _db_conn()
    try:
        conn.execute(
            """
            UPDATE task_run_history
            SET status=?,
                end_time=datetime('now', 'localtime'),
                pytest_exit_code=?,
                allure_exit_code=?,
                error=?,
                allure_output=?
            WHERE task_id=?
            """,
            (status, pytest_exit_code, allure_exit_code, error, allure_output, task_id),
        )
        conn.commit()
    finally:
        conn.close()


def _get_task_history(limit: int = 20, device: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    conn = _db_conn()
    try:
        if device and status:
            rows = conn.execute(
                """
                SELECT * FROM task_run_history
                WHERE device_serial=? AND status=?
                ORDER BY start_time DESC
                LIMIT ?
                """,
                (device, status, limit),
            ).fetchall()
        elif device:
            rows = conn.execute(
                """
                SELECT * FROM task_run_history
                WHERE device_serial=?
                ORDER BY start_time DESC
                LIMIT ?
                """,
                (device, limit),
            ).fetchall()
        elif status:
            rows = conn.execute(
                """
                SELECT * FROM task_run_history
                WHERE status=?
                ORDER BY start_time DESC
                LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM task_run_history
                ORDER BY start_time DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    items = [dict(r) for r in rows]
    for item in items:
        task_id = str(item.get("task_id") or "")
        has_report = _task_has_report(task_id) if task_id else False
        item["has_report"] = has_report
        item["report_url"] = _task_report_url(task_id) if has_report else None
        item["has_report_data"] = _task_has_report_data(task_id) if task_id else False
    return items


def _get_task_record(task_id: str) -> dict[str, Any] | None:
    conn = _db_conn()
    try:
        row = conn.execute("SELECT * FROM task_run_history WHERE task_id=?", (task_id,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


_remote_ws_lock = threading.Lock()
_remote_ws_send_lock = threading.Lock()
_remote_ws_log_lock = threading.Lock()
_remote_ws_stop_event = threading.Event()
_remote_ws_thread: threading.Thread | None = None
_remote_ws_app: Any = None
_remote_ws_status_state: dict[str, Any] = {
    "enabled": False,
    "url": "",
    "connected": False,
    "client_id": "",
    "last_error": "",
    "last_connect_ts": 0,
    "last_message_ts": 0,
    "last_heartbeat_ts": 0,
}


def _remote_ws_enabled() -> bool:
    raw = (os.getenv("REMOTE_WS_ENABLED") or "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    return bool((os.getenv("REMOTE_WS_URL") or "").strip())


def _remote_ws_client_id() -> str:
    raw = (os.getenv("REMOTE_WS_CLIENT_ID") or "").strip()
    if raw:
        return raw
    host = platform.node().strip() or socket.gethostname().strip() or "desktop-client"
    return f"{host}-{os.getpid()}"


def _remote_ws_set_status(**kwargs: Any) -> None:
    with _remote_ws_lock:
        _remote_ws_status_state.update(kwargs)


def _remote_ws_status() -> dict[str, Any]:
    with _remote_ws_lock:
        return dict(_remote_ws_status_state)


def _remote_ws_log(event: str, **fields: Any) -> None:
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    payload = {"event": event, **fields}
    safe_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    line = f"[{ts}] {safe_payload}\n"
    try:
        with _remote_ws_log_lock:
            with REMOTE_WS_LOG_FILE.open("a", encoding="utf-8") as f:
                f.write(line)
    except Exception:
        # Never let logging failures affect websocket behavior.
        pass


def _read_remote_ws_log_lines(max_lines: int = 200) -> list[str]:
    if max_lines <= 0:
        max_lines = 1
    max_lines = min(max_lines, 2000)
    if not REMOTE_WS_LOG_FILE.exists():
        return []
    try:
        lines = REMOTE_WS_LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []
    if len(lines) <= max_lines:
        return lines
    return lines[-max_lines:]


def _remote_ws_send_json(payload: dict[str, Any]) -> bool:
    global _remote_ws_app
    app = _remote_ws_app
    if app is None:
        return False
    try:
        with _remote_ws_send_lock:
            app.send(json.dumps(payload, ensure_ascii=False))
        return True
    except Exception as exc:
        _remote_ws_set_status(last_error=str(exc), connected=False)
        _remote_ws_log("send_failed", error=str(exc), payload_type=str(payload.get("type") or "unknown"))
        return False


def _remote_ws_heartbeat_payload() -> dict[str, Any]:
    with _tasks_lock:
        running_task_ids = list(_device_running_task.values())
    bind_host = (os.getenv("DESKTOP_WEB_HOST") or DEFAULT_HOST).strip() or DEFAULT_HOST
    bind_port = _env_int("DESKTOP_WEB_PORT", DEFAULT_PORT)
    desktop_base_url = (os.getenv("REMOTE_WS_PUBLIC_BASE_URL") or "").strip() or f"http://{bind_host}:{bind_port}"
    return {
        "type": "heartbeat",
        "client_id": _remote_ws_client_id(),
        "data": {
            "status": "running" if running_task_ids else "idle",
            "running_task_count": len(running_task_ids),
            "running_task_ids": running_task_ids,
            "desktop_base_url": desktop_base_url,
            "ts": int(time.time()),
        },
    }


def _remote_ws_exec_command(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    if action == "list_devices":
        return _list_devices()
    if action == "list_test_packages":
        return {"ok": True, "packages": _list_test_packages(str(payload.get("app_key") or "lysora"))}
    if action == "run_tests":
        return _run_tests(payload)
    if action == "stop_task":
        return _stop_task(payload)
    if action == "task_status":
        task_id = str(payload.get("task_id") or "").strip()
        if not task_id:
            return {"ok": False, "error": "task_id 不能为空"}
        return _task_status(task_id)
    if action == "task_report_data":
        task_id = str(payload.get("task_id") or "").strip()
        if not task_id:
            return {"ok": False, "error": "task_id 不能为空"}
        data = _get_task_report_data(task_id)
        if not data:
            return {"ok": False, "error": f"任务报告数据不存在: {task_id}"}
        return {"ok": True, "task_id": task_id, **data}
    if action == "task_history":
        limit_raw = payload.get("limit", 20)
        try:
            limit = max(1, min(int(limit_raw), 200))
        except Exception:
            limit = 20
        device = str(payload.get("device") or "").strip() or None
        status = str(payload.get("status") or "").strip().lower() or None
        if status and status not in {"running", "success", "failed", "stopped"}:
            status = None
        return {"ok": True, "tasks": _get_task_history(limit=limit, device=device, status=status)}
    if action == "device_status":
        device = str(payload.get("device_serial") or "").strip()
        if not device:
            return {"ok": False, "error": "device_serial 不能为空"}
        return {"ok": True, "device_status": _get_device_status(device)}
    if action == "startup_info":
        return _startup_info()
    if action == "appium_ready":
        return _appium_ready()
    return {"ok": False, "error": f"unsupported action: {action}"}


def _remote_ws_handle_message(raw: str) -> None:
    _remote_ws_set_status(last_message_ts=int(time.time()))
    try:
        msg = json.loads(raw)
    except Exception:
        _remote_ws_log("message_parse_failed", raw_preview=raw[:200])
        return
    msg_type = str(msg.get("type") or "").strip().lower()
    _remote_ws_log("message_received", message_type=msg_type or "unknown")
    if msg_type == "command":
        action = str(msg.get("action") or "").strip()
        request_id = str(msg.get("request_id") or "").strip()
        payload = msg.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        try:
            result = _remote_ws_exec_command(action, payload)
            ok = bool(result.get("ok", True)) if isinstance(result, dict) else True
            resp = {
                "type": "response",
                "client_id": _remote_ws_client_id(),
                "request_id": request_id,
                "action": action,
                "data": result,
                "ok": ok,
            }
        except Exception as exc:
            resp = {
                "type": "response",
                "client_id": _remote_ws_client_id(),
                "request_id": request_id,
                "action": action,
                "ok": False,
                "error": str(exc),
            }
        _remote_ws_send_json(resp)
    elif msg_type in {"register_ack", "heartbeat_ack"}:
        _remote_ws_set_status(last_heartbeat_ts=int(time.time()))
        _remote_ws_log("message_ack", message_type=msg_type)


def _remote_ws_heartbeat_loop(app: Any, interval_sec: int) -> None:
    while not _remote_ws_stop_event.is_set():
        if _remote_ws_app is not app:
            return
        _remote_ws_send_json(_remote_ws_heartbeat_payload())
        _remote_ws_set_status(last_heartbeat_ts=int(time.time()))
        _remote_ws_stop_event.wait(max(1, interval_sec))


def _remote_ws_runner() -> None:
    global _remote_ws_app
    if websocket_client is None:
        _remote_ws_set_status(last_error="websocket-client 未安装", enabled=False)
        _remote_ws_log("disabled", reason="websocket-client missing")
        return
    ws_url = (os.getenv("REMOTE_WS_URL") or "").strip()
    if not ws_url:
        _remote_ws_set_status(enabled=False, url="", connected=False)
        _remote_ws_log("disabled", reason="REMOTE_WS_URL empty")
        return
    _remote_ws_set_status(enabled=True, url=ws_url, client_id=_remote_ws_client_id())
    _remote_ws_log("runner_started", ws_url=ws_url, client_id=_remote_ws_client_id())
    heartbeat_sec = max(5, _env_int("REMOTE_WS_HEARTBEAT_SEC", 15))
    reconnect_sec = max(2, _env_int("REMOTE_WS_RECONNECT_SEC", 5))
    ping_interval = max(10, _env_int("REMOTE_WS_PING_INTERVAL_SEC", 20))
    ping_timeout = max(5, _env_int("REMOTE_WS_PING_TIMEOUT_SEC", 10))

    while not _remote_ws_stop_event.is_set():
        def _on_open(app: Any) -> None:
            _remote_ws_set_status(connected=True, last_connect_ts=int(time.time()), last_error="")
            _remote_ws_log("connected", ws_url=ws_url, client_id=_remote_ws_client_id())
            bind_host = (os.getenv("DESKTOP_WEB_HOST") or DEFAULT_HOST).strip() or DEFAULT_HOST
            bind_port = _env_int("DESKTOP_WEB_PORT", DEFAULT_PORT)
            desktop_base_url = (os.getenv("REMOTE_WS_PUBLIC_BASE_URL") or "").strip() or f"http://{bind_host}:{bind_port}"
            _remote_ws_send_json(
                {
                    "type": "register",
                    "client_id": _remote_ws_client_id(),
                    "data": {
                        "hostname": platform.node(),
                        "pid": os.getpid(),
                        "status": "online",
                        "version": "desktop-web-app",
                        "desktop_base_url": desktop_base_url,
                    },
                }
            )
            threading.Thread(
                target=_remote_ws_heartbeat_loop,
                args=(app, heartbeat_sec),
                daemon=True,
            ).start()

        def _on_message(_: Any, message: str) -> None:
            _remote_ws_handle_message(message)

        def _on_error(_: Any, err: Any) -> None:
            _remote_ws_set_status(last_error=str(err), connected=False)
            _remote_ws_log("error", error=str(err))

        def _on_close(_: Any, __: Any, ___: Any) -> None:
            _remote_ws_set_status(connected=False)
            _remote_ws_log("closed")

        app = websocket_client.WebSocketApp(
            ws_url,
            on_open=_on_open,
            on_message=_on_message,
            on_error=_on_error,
            on_close=_on_close,
        )
        _remote_ws_app = app
        try:
            app.run_forever(ping_interval=ping_interval, ping_timeout=ping_timeout)
        except Exception as exc:
            _remote_ws_set_status(last_error=str(exc), connected=False)
            _remote_ws_log("run_forever_exception", error=str(exc))
        if _remote_ws_stop_event.wait(reconnect_sec):
            _remote_ws_log("runner_stopped")
            break
        _remote_ws_log("reconnecting", wait_sec=reconnect_sec)


def _start_remote_ws_if_needed() -> None:
    global _remote_ws_thread
    if not _remote_ws_enabled():
        _remote_ws_set_status(enabled=False)
        _remote_ws_log("startup_skipped", reason="REMOTE_WS disabled")
        return
    if _remote_ws_thread and _remote_ws_thread.is_alive():
        _remote_ws_log("startup_skipped", reason="thread already running")
        return
    _remote_ws_stop_event.clear()
    _remote_ws_thread = threading.Thread(target=_remote_ws_runner, daemon=True, name="remote-ws-client")
    _remote_ws_thread.start()
    _remote_ws_log("startup_triggered")


def _run_command(args: list[str], timeout: int = 120, env: dict[str, str] | None = None) -> tuple[int, str]:
    try:
        result = subprocess.run(
            args,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout,
            env=env,
        )
    except FileNotFoundError as exc:
        return 127, f"Command not found: {args[0]}\n{exc}"
    except subprocess.TimeoutExpired:
        return 124, f"Command timed out after {timeout}s"
    combined = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    return result.returncode, combined.strip()


def _adb(serial: str, shell_args: list[str], timeout: int = 30) -> tuple[int, str]:
    return _run_command([ADB_BIN, "-s", serial, "shell", *shell_args], timeout=timeout)


def _get_prop(serial: str, prop: str) -> str:
    code, out = _adb(serial, ["getprop", prop])
    return out.strip() or "-" if code == 0 else "-"


def _get_app_version(serial: str, package_name: str) -> str:
    code, out = _adb(serial, ["dumpsys", "package", package_name], timeout=40)
    if code != 0:
        return "未安装"
    m = re.search(r"versionName=([^\s]+)", out)
    return m.group(1) if m else "未安装"


def _list_devices() -> dict[str, Any]:
    code, out = _run_command([ADB_BIN, "devices"], timeout=20)
    if code != 0:
        return {"ok": False, "devices": [], "error": out or "无法执行 adb devices"}

    devices: list[dict[str, Any]] = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices") or "\t" not in line:
            continue
        serial, status = line.split("\t", 1)
        serial, status = serial.strip(), status.strip()
        if status != "device":
            devices.append(
                {
                    "serial": serial,
                    "status": status,
                    "brand": "-",
                    "model": "-",
                    "os_version": "-",
                    "app_versions": {},
                }
            )
            continue
        app_versions = {k: _get_app_version(serial, v["package_name"]) for k, v in APP_CONFIG.items()}
        devices.append(
            {
                "serial": serial,
                "status": status,
                "brand": _get_prop(serial, "ro.product.brand"),
                "model": _get_prop(serial, "ro.product.model"),
                "os_version": _get_prop(serial, "ro.build.version.release"),
                "app_versions": app_versions,
            }
        )
    return {"ok": True, "devices": devices}


def _list_test_packages(app_key: str) -> list[str]:
    default_pkg = APP_CONFIG.get(app_key, {}).get("default_test_package", "tests")
    package_path = (PROJECT_ROOT / default_pkg).resolve()
    packages = [default_pkg]
    if package_path.exists():
        for f in sorted(package_path.glob("test_*.py")):
            packages.append(f.relative_to(PROJECT_ROOT).as_posix())
    return packages


def _startup_info() -> dict[str, Any]:
    missing: list[str] = []
    if shutil.which("adb") is None:
        missing.append("adb")
    return {"ok": True, "missing_dependencies": missing}


def _appium_ready() -> dict[str, Any]:
    server_url = (os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723") or "").strip().rstrip("/")
    if not server_url:
        return {"ok": True, "running": False, "server_url": "", "error": "APPIUM_SERVER_URL 为空"}

    status_url = f"{server_url}/status"
    try:
        with urllib.request.urlopen(status_url, timeout=1.5) as resp:
            running = resp.status == 200
            return {
                "ok": True,
                "running": running,
                "server_url": server_url,
                "error": None if running else f"HTTP {resp.status}",
            }
    except Exception as exc:
        return {"ok": True, "running": False, "server_url": server_url, "error": str(exc)}


def _run_tests(payload: dict[str, Any]) -> dict[str, Any]:
    device = (payload.get("device") or "").strip()
    app_key = (payload.get("app_key") or "").strip()
    raw_packages = payload.get("test_packages")
    if isinstance(raw_packages, list):
        test_packages = [str(p).strip() for p in raw_packages if str(p).strip()]
    else:
        test_packages = []
    if not test_packages:
        single_package = (payload.get("test_package") or "").strip()
        if single_package:
            test_packages = [single_package]
    suite = (payload.get("suite") or "all").strip()

    if not test_packages:
        return {"ok": False, "error": "test_packages 不能为空"}
    if not device:
        return {"ok": False, "error": "device 不能为空"}

    appium_state = _appium_ready()
    if not appium_state.get("running"):
        server_url = appium_state.get("server_url") or "http://127.0.0.1:4723"
        detail = appium_state.get("error") or "unknown error"
        return {"ok": False, "error": f"Appium 未启动，请先启动后再执行测试。地址: {server_url}，详情: {detail}"}

    pytest_args = [*test_packages, "-v"]
    if suite in ("smoke", "full"):
        marker_expr = suite
        if app_key in APP_CONFIG:
            marker_expr = f"{app_key} and {suite}"
        pytest_args.extend(["-m", marker_expr])

    if _is_frozen():
        # In PyInstaller app, sys.executable is the UI exe (not python.exe).
        cmd = [sys.executable, "--run-pytest", *pytest_args]
    else:
        cmd = [sys.executable, "-m", "pytest", *pytest_args]

    with _tasks_lock:
        if device in _device_running_task:
            task_id = _device_running_task[device]
            return {"ok": False, "error": f"该设备已有任务在运行中: {task_id}", "task_id": task_id}

    _ensure_task_log_dir()
    task_id = uuid4().hex[:12]
    log_path = TASK_LOG_DIR / f"{task_id}.log"
    task_results_file, task_report_file = _task_report_paths(task_id)
    task_results_file.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["APPIUM_UDID"] = device
    # Prevent external user-site pytest plugins (e.g. xonsh) from breaking runs.
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    # Reduce noisy deprecation warning from bundled importer/pkg_resources.
    env["PYTHONWARNINGS"] = "ignore:pkg_resources is deprecated as an API:UserWarning"
    # Isolate per-task result artifacts so history can open any past run.
    env["TEST_RESULTS_FILE"] = str(task_results_file)
    env["TEST_REPORT_FILE"] = str(task_report_file)

    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            env=env,
        )
    except Exception as exc:
        return {"ok": False, "error": f"启动 pytest 失败: {exc}"}

    task_info = {
        "task_id": task_id,
        "device": device,
        "status": "running",
        "cmd": cmd,
        "process": process,
        "log_path": str(log_path),
        "start_time": time.time(),
        "pytest_exit_code": None,
        "allure_exit_code": None,
        "allure_output": "",
        "error": None,
    }

    with _tasks_lock:
        _tasks[task_id] = task_info
        _device_running_task[device] = task_id

    _insert_task_history(task_id, device, app_key, suite, test_packages, str(log_path))
    _set_device_status(device, "running", task_id=task_id, message="任务执行中")

    def _watch_task() -> None:
        exit_code: int | None = None
        try:
            with log_path.open("w", encoding="utf-8") as fp:
                if process.stdout is not None:
                    for line in process.stdout:
                        fp.write(line)
                        fp.flush()
                exit_code = process.wait()
        except Exception as exc:
            with _tasks_lock:
                info = _tasks.get(task_id)
                if info is not None:
                    info["status"] = "failed"
                    info["error"] = str(exc)
                _device_running_task.pop(device, None)
            _update_task_history(task_id=task_id, status="failed", error=str(exc))
            _set_device_status(device, "failed", task_id=task_id, message=str(exc))
            return

        report_ok = False
        post_errors: list[str] = []
        try:
            report_ok = task_report_file.exists()
            if not report_ok:
                from report_generator import generate_report

                report_ok = generate_report(task_results_file, task_report_file)
            allure_output = (
                f"HTML report generated: {_safe_display_path(task_report_file)}"
                if report_ok
                else "HTML report generate failed"
            )
            if report_ok:
                try:
                    shutil.copyfile(task_report_file, REPORT_HTML_FILE)
                    if task_results_file.exists():
                        shutil.copyfile(task_results_file, TEST_RESULTS_FILE)
                except Exception as exc:
                    post_errors.append(f"copy latest report failed: {exc}")
            report_data_ok = _save_task_report_to_db(task_id, task_results_file)
            if not report_data_ok:
                post_errors.append("report data save failed")
        except Exception as exc:
            allure_output = "report post-process failed"
            post_errors.append(str(exc))

        allure_code = 0 if report_ok else 1
        if post_errors:
            allure_output = f"{allure_output}; {'; '.join(post_errors)}"

        with _tasks_lock:
            info = _tasks.get(task_id)
            was_stopped = bool(info is not None and info.get("status") == "stopped")
            if info is not None:
                info["pytest_exit_code"] = exit_code
                info["allure_exit_code"] = allure_code
                info["allure_output"] = allure_output
                if not was_stopped:
                    # pytest 成功时，后处理异常仅记告警，不再影响任务成功状态。
                    info["status"] = "success" if exit_code == 0 else "failed"
            _device_running_task.pop(device, None)

        final_task_status = "stopped" if was_stopped else ("success" if exit_code == 0 else "failed")
        final_status = "idle" if final_task_status in {"success", "stopped"} else "failed"
        if final_task_status == "stopped":
            final_msg = "任务已停止"
        elif final_status == "idle":
            final_msg = "任务完成"
        else:
            final_msg = "任务失败，请查看日志"
        update_error = "任务被手动停止" if final_task_status == "stopped" else None
        _update_task_history(
            task_id=task_id,
            status=final_task_status,
            pytest_exit_code=exit_code,
            allure_exit_code=allure_code,
            error=update_error,
            allure_output=allure_output,
        )
        _set_device_status(device, final_status, task_id=task_id, message=final_msg)
        return

    threading.Thread(target=_watch_task, daemon=True).start()
    return {"ok": True, "task_id": task_id, "status": "running"}


def _task_status(task_id: str) -> dict[str, Any]:
    with _tasks_lock:
        info = _tasks.get(task_id)
        if info:
            payload = {
                "ok": True,
                "task_id": task_id,
                "device": info.get("device"),
                "status": info.get("status"),
                "pytest_exit_code": info.get("pytest_exit_code"),
                "allure_exit_code": info.get("allure_exit_code"),
                "allure_output": info.get("allure_output"),
                "error": info.get("error"),
                "has_report": _task_has_report(task_id),
                "report_url": _task_report_url(task_id) if _task_has_report(task_id) else None,
                "has_report_data": _task_has_report_data(task_id),
            }
            log_path = Path(str(info.get("log_path") or ""))
        else:
            record = _get_task_record(task_id)
            if not record:
                return {"ok": False, "error": f"任务不存在: {task_id}"}
            payload = {
                "ok": True,
                "task_id": task_id,
                "device": record.get("device_serial"),
                "status": record.get("status"),
                "pytest_exit_code": record.get("pytest_exit_code"),
                "allure_exit_code": record.get("allure_exit_code"),
                "allure_output": record.get("allure_output") or "",
                "error": record.get("error"),
                "has_report": _task_has_report(task_id),
                "report_url": _task_report_url(task_id) if _task_has_report(task_id) else None,
                "has_report_data": _task_has_report_data(task_id),
            }
            log_path = Path(str(record.get("log_path") or ""))
    if log_path.exists():
        try:
            payload["pytest_output"] = log_path.read_text(encoding="utf-8", errors="ignore")[-120000:]
        except Exception:
            payload["pytest_output"] = ""
    else:
        payload["pytest_output"] = ""
    return payload


def _stop_task(payload: dict[str, Any]) -> dict[str, Any]:
    task_id = str(payload.get("task_id") or "").strip()
    device = str(payload.get("device") or "").strip()

    with _tasks_lock:
        if not task_id and device:
            task_id = _device_running_task.get(device) or ""
        if not task_id:
            return {"ok": False, "error": "task_id 或 device 至少提供一个"}
        info = _tasks.get(task_id)
        if not info:
            return {"ok": False, "error": f"任务不存在: {task_id}"}
        process: subprocess.Popen[str] | None = info.get("process")
        dev = str(info.get("device") or "")

    if process is None:
        return {"ok": False, "error": "任务进程不存在"}
    if process.poll() is not None:
        _set_device_status(dev, "idle", task_id=task_id, message="任务已结束")
        return {"ok": True, "task_id": task_id, "status": "finished"}

    try:
        process.terminate()
        try:
            process.wait(timeout=5)
        except Exception:
            process.kill()
    except Exception as exc:
        return {"ok": False, "error": f"停止任务失败: {exc}"}

    with _tasks_lock:
        info = _tasks.get(task_id)
        if info:
            info["status"] = "stopped"
            info["error"] = "任务被手动停止"
        _device_running_task.pop(dev, None)
    _update_task_history(task_id=task_id, status="stopped", error="任务被手动停止")
    _set_device_status(dev, "idle", task_id=task_id, message="任务已停止")
    return {"ok": True, "task_id": task_id, "status": "stopped"}


def _open_report() -> dict[str, Any]:
    if not REPORT_HTML_FILE.exists():
        from report_generator import generate_report

        if not generate_report(TEST_RESULTS_FILE, REPORT_HTML_FILE):
            return {"ok": False, "error": "暂无报告，且生成失败"}
    try:
        os.startfile(str(REPORT_HTML_FILE))  # type: ignore[attr-defined]
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _get_free_port(host: str, preferred_port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        if sock.connect_ex((host, preferred_port)) != 0:
            return preferred_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock2:
        sock2.bind((host, 0))
        return int(sock2.getsockname()[1])


app = Flask(__name__)


@app.get("/")
def index() -> Any:
    return send_file(UI_HTML_FILE)


@app.get("/assets/<path:filename>")
def ui_assets(filename: str) -> Any:
    return send_from_directory(UI_ASSETS_DIR, filename)


@app.post("/api/list_devices")
def api_list_devices() -> Any:
    return jsonify(_list_devices())


@app.get("/api/get_app_options")
def api_get_app_options() -> Any:
    apps = [{"key": k, "label": v["label"]} for k, v in APP_CONFIG.items()]
    return jsonify(apps)


@app.post("/api/list_test_packages")
def api_list_test_packages() -> Any:
    payload = request.get_json(silent=True) or {}
    app_key = payload.get("app_key") or "lysora"
    return jsonify({"ok": True, "packages": _list_test_packages(app_key)})


@app.post("/api/run_tests")
def api_run_tests() -> Any:
    payload = request.get_json(silent=True) or {}
    return jsonify(_run_tests(payload))


@app.get("/api/task_status/<task_id>")
def api_task_status(task_id: str) -> Any:
    return jsonify(_task_status(task_id))


@app.get("/api/task_history")
def api_task_history() -> Any:
    limit_raw = request.args.get("limit", "20")
    device = (request.args.get("device") or "").strip() or None
    status = (request.args.get("status") or "").strip().lower() or None
    if status and status not in {"running", "success", "failed", "stopped"}:
        status = None
    try:
        limit = max(1, min(int(limit_raw), 200))
    except ValueError:
        limit = 20
    return jsonify({"ok": True, "tasks": _get_task_history(limit=limit, device=device, status=status)})


@app.get("/api/task_log/<task_id>")
def api_task_log(task_id: str) -> Any:
    record = _get_task_record(task_id)
    if not record:
        return jsonify({"ok": False, "error": f"任务不存在: {task_id}"}), 404
    log_path = Path(str(record.get("log_path") or ""))
    if not log_path.exists():
        return jsonify({"ok": False, "error": f"日志不存在: {log_path}"}), 404
    return send_file(log_path, as_attachment=True, download_name=f"{task_id}.log", mimetype="text/plain")


@app.get("/api/task_report/<task_id>")
def api_task_report(task_id: str) -> Any:
    _, report_file = _task_report_paths(task_id)
    if not report_file.exists():
        return jsonify({"ok": False, "error": f"任务报告不存在: {task_id}"}), 404
    return send_file(report_file, mimetype="text/html")


@app.get("/api/task_report_data/<task_id>")
def api_task_report_data(task_id: str) -> Any:
    data = _get_task_report_data(task_id)
    if not data:
        return jsonify({"ok": False, "error": f"任务报告数据不存在: {task_id}"}), 404
    return jsonify({"ok": True, "task_id": task_id, **data})


@app.get("/api/report_asset")
def api_report_asset() -> Any:
    rel_path = (request.args.get("path") or "").strip()
    if not rel_path:
        return jsonify({"ok": False, "error": "path 不能为空"}), 400
    # Support both runtime reports folder and PyInstaller resource reports folder.
    # In packaged mode, screenshots/videos can be generated under _internal/reports.
    allowed_roots = [REPORTS_ROOT.resolve(), (RESOURCE_ROOT / "reports").resolve()]
    candidate_roots = [RUNTIME_ROOT.resolve(), RESOURCE_ROOT.resolve()]

    target: Path | None = None
    for root in candidate_roots:
        candidate = (root / rel_path).resolve()
        try:
            if any(candidate.is_relative_to(base) for base in allowed_roots):
                if candidate.exists():
                    target = candidate
                    break
        except Exception:
            continue

    if target is None:
        return jsonify({"ok": False, "error": f"文件不存在或路径非法: {rel_path}"}), 404
    return send_file(target)


@app.post("/api/stop_task")
def api_stop_task() -> Any:
    payload = request.get_json(silent=True) or {}
    return jsonify(_stop_task(payload))


@app.get("/api/device_status/<device_serial>")
def api_device_status(device_serial: str) -> Any:
    return jsonify({"ok": True, "device_status": _get_device_status(device_serial)})


@app.post("/api/open_report")
def api_open_report() -> Any:
    return jsonify(_open_report())


@app.get("/api/startup_info")
def api_startup_info() -> Any:
    return jsonify(_startup_info())


@app.get("/api/appium_ready")
def api_appium_ready() -> Any:
    return jsonify(_appium_ready())


@app.get("/api/remote_ws_status")
def api_remote_ws_status() -> Any:
    return jsonify({"ok": True, "status": _remote_ws_status()})


@app.get("/api/remote_ws_log")
def api_remote_ws_log() -> Any:
    try:
        lines = max(1, min(int(request.args.get("lines", "200")), 2000))
    except Exception:
        lines = 200
    return jsonify({"ok": True, "file": str(REMOTE_WS_LOG_FILE), "lines": _read_remote_ws_log_lines(lines)})


def _auto_open_browser(url: str) -> None:
    time.sleep(0.8)
    webbrowser.open(url)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--run-pytest":
        import pytest

        exit_code = int(pytest.main(sys.argv[2:]))
        raise SystemExit(exit_code)

    _init_runtime_db()
    _start_remote_ws_if_needed()
    host = (os.getenv("DESKTOP_WEB_HOST") or DEFAULT_HOST).strip() or DEFAULT_HOST
    preferred_port = _env_int("DESKTOP_WEB_PORT", DEFAULT_PORT)
    auto_port_fallback = _env_bool("DESKTOP_WEB_AUTO_PORT_FALLBACK", False)
    port = _get_free_port(host, preferred_port) if auto_port_fallback else preferred_port
    url = f"http://{host}:{port}"
    threading.Thread(target=_auto_open_browser, args=(url,), daemon=True).start()
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
