"""Flask-based desktop UI launcher for mobile automation testing."""
from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_file, send_from_directory


APP_BASE_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT = APP_BASE_DIR
UI_HTML_FILE = PROJECT_ROOT / "ui" / "index.html"
UI_ASSETS_DIR = PROJECT_ROOT / "ui" / "assets"
REPORTS_ROOT = PROJECT_ROOT / "reports"
TEST_RESULTS_FILE = REPORTS_ROOT / "test_results.json"
REPORT_HTML_FILE = REPORTS_ROOT / "test_report.html"

ADB_BIN = "adb"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 17999

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

    cmd = [sys.executable, "-m", "pytest", *test_packages, "-v"]
    if suite in ("smoke", "full"):
        marker_expr = suite
        if app_key in APP_CONFIG:
            marker_expr = f"{app_key} and {suite}"
        cmd.extend(["-m", marker_expr])

    env = os.environ.copy()
    env["APPIUM_UDID"] = device
    pytest_code, pytest_output = _run_command(cmd, timeout=3600, env=env)

    from report_generator import generate_report

    report_ok = generate_report(TEST_RESULTS_FILE, REPORT_HTML_FILE)
    allure_code = 0 if report_ok else 1
    allure_output = (
        f"HTML report generated: {REPORT_HTML_FILE.relative_to(PROJECT_ROOT).as_posix()}"
        if report_ok
        else "HTML report generate failed"
    )

    return {
        "ok": pytest_code == 0 and report_ok,
        "pytest_exit_code": pytest_code,
        "allure_exit_code": allure_code,
        "pytest_output": pytest_output,
        "allure_output": allure_output,
        "error": None if pytest_code == 0 else "pytest 执行失败",
    }


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


@app.post("/api/open_report")
def api_open_report() -> Any:
    return jsonify(_open_report())


@app.get("/api/startup_info")
def api_startup_info() -> Any:
    return jsonify(_startup_info())


@app.get("/api/appium_ready")
def api_appium_ready() -> Any:
    return jsonify(_appium_ready())


def _auto_open_browser(url: str) -> None:
    time.sleep(0.8)
    webbrowser.open(url)


def main() -> None:
    host = (os.getenv("DESKTOP_WEB_HOST") or DEFAULT_HOST).strip() or DEFAULT_HOST
    preferred_port = _env_int("DESKTOP_WEB_PORT", DEFAULT_PORT)
    auto_port_fallback = _env_bool("DESKTOP_WEB_AUTO_PORT_FALLBACK", False)
    port = _get_free_port(host, preferred_port) if auto_port_fallback else preferred_port
    url = f"http://{host}:{port}"
    threading.Thread(target=_auto_open_browser, args=(url,), daemon=True).start()
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
