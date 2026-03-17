import json
import os
import re
from base64 import b64decode
from datetime import datetime
from pathlib import Path

import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options
try:
    import allure
except Exception:  # pragma: no cover - allure is optional at runtime
    allure = None

_PROJECT_ROOT = Path(__file__).parent


def _load_local_env_file() -> None:
    env_path = _PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


_load_local_env_file()


def _build_android_options() -> UiAutomator2Options:
    caps = {
        "platformName": "Android",
        "appium:automationName": os.getenv("APPIUM_AUTOMATION_NAME", "UiAutomator2"),
        "appium:deviceName": os.getenv("APPIUM_DEVICE_NAME", "Android Device"),
        "appium:noReset": os.getenv("APPIUM_NO_RESET", "true").lower() == "true",
        "appium:newCommandTimeout": int(os.getenv("APPIUM_NEW_COMMAND_TIMEOUT", "240")),
    }
    udid = os.getenv("APPIUM_UDID")
    if udid:
        caps["appium:udid"] = udid
    return UiAutomator2Options().load_capabilities(caps)


def _safe_test_name(nodeid: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", nodeid).replace("::", "__")


def _resolve_app_group(node) -> str:
    nodeid = getattr(node, "nodeid", "").lower()
    if "tests/lysora/" in nodeid or "tests\\lysora\\" in nodeid:
        return "lysora"
    if "tests/ruijiecloud/" in nodeid or "tests\\ruijiecloud\\" in nodeid:
        return "ruijieCloud"
    if hasattr(node, "get_closest_marker"):
        if node.get_closest_marker("lysora"):
            return "lysora"
        if node.get_closest_marker("ruijieCloud"):
            return "ruijieCloud"
    return "common"


def _artifact_dir(base: str, node) -> Path:
    target = _PROJECT_ROOT / "reports" / base / _resolve_app_group(node)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _rel(path: Path) -> str:
    """Return path relative to project root with forward slashes."""
    try:
        return str(path.relative_to(_PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


# ---------- Session-level result collection ----------
_session_start: str = datetime.now().isoformat()
_test_results: list[dict] = []        # populated by pytest_runtest_logreport
_test_artifacts: dict[str, dict] = {}  # nodeid -> {screenshot, video}


@pytest.fixture(scope="session", autouse=True)
def ensure_report_dirs() -> None:
    (_PROJECT_ROOT / "reports").mkdir(parents=True, exist_ok=True)
    (_PROJECT_ROOT / "reports" / "screenshots").mkdir(parents=True, exist_ok=True)
    (_PROJECT_ROOT / "reports" / "videos").mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def driver():
    server_url = os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723")
    options = _build_android_options()
    mobile_driver = webdriver.Remote(server_url, options=options)
    mobile_driver.implicitly_wait(2)
    yield mobile_driver
    mobile_driver.quit()


@pytest.fixture(autouse=True)
def record_test_video(driver, request):
    started = False
    try:
        driver.start_recording_screen()
        started = True
    except Exception:
        pass

    yield

    if not started:
        return

    try:
        video_base64 = driver.stop_recording_screen()
    except Exception:
        return

    if not video_base64:
        return

    video_name = f"{_safe_test_name(request.node.nodeid)}.mp4"
    video_path = _artifact_dir("videos", request.node) / video_name
    try:
        video_path.write_bytes(b64decode(video_base64))
        nodeid = request.node.nodeid
        _test_artifacts.setdefault(nodeid, {})["video"] = _rel(video_path)
        if allure is not None:
            allure.attach.file(
                str(video_path),
                name=f"{request.node.name}-video",
                attachment_type=allure.attachment_type.MP4,
            )
    except Exception:
        pass


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        driver = item.funcargs.get("driver")
        if driver:
            file_name = f"{item.name}_{report.outcome}.png"
            file_path = _artifact_dir("screenshots", item) / file_name
            try:
                driver.save_screenshot(str(file_path))
                _test_artifacts.setdefault(item.nodeid, {})["screenshot"] = _rel(file_path)
                if allure is not None:
                    allure.attach.file(
                        str(file_path),
                        name=f"{item.name}-screenshot-{report.outcome}",
                        attachment_type=allure.attachment_type.PNG,
                    )
            except Exception:
                pass


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Collect pass/fail/duration for every test's call phase."""
    if report.when != "call":
        return
    nodeid = report.nodeid
    app = "lysora" if "lysora" in nodeid.lower() else (
        "ruijieCloud" if "ruijiecloud" in nodeid.lower() else "common"
    )
    status = "passed" if report.passed else ("failed" if report.failed else "skipped")
    _test_results.append({
        "nodeid": nodeid,
        "name": nodeid.split("::")[-1] if "::" in nodeid else nodeid,
        "status": status,
        "duration": round(getattr(report, "duration", 0), 2),
        "app": app,
        "error_message": str(report.longrepr) if report.failed else None,
    })


def pytest_sessionfinish(session, exitstatus) -> None:
    """Write JSON results and generate HTML report after all tests complete."""
    tests = []
    for r in _test_results:
        artifacts = _test_artifacts.get(r["nodeid"], {})
        tests.append({
            "name": r["name"],
            "node_id": r["nodeid"],
            "status": r["status"],
            "duration": r["duration"],
            "app": r["app"],
            "screenshot": artifacts.get("screenshot"),
            "video": artifacts.get("video"),
            "error_message": r["error_message"],
        })

    passed = sum(1 for t in tests if t["status"] == "passed")
    failed = sum(1 for t in tests if t["status"] == "failed")
    skipped = sum(1 for t in tests if t["status"] == "skipped")

    data = {
        "session_start": _session_start,
        "session_end": datetime.now().isoformat(),
        "total": len(tests),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "tests": tests,
    }

    results_file = Path(os.getenv("TEST_RESULTS_FILE", str(_PROJECT_ROOT / "reports" / "test_results.json")))
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Also generate HTML report
    try:
        from report_generator import generate_report
        report_file = Path(os.getenv("TEST_REPORT_FILE", str(_PROJECT_ROOT / "reports" / "test_report.html")))
        report_file.parent.mkdir(parents=True, exist_ok=True)
        generate_report(results_file, report_file)
    except Exception:
        pass
