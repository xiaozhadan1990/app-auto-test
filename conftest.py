from __future__ import annotations

import json
import os
from base64 import b64decode
from pathlib import Path
from typing import Any

import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions

from tests.common.mobile_platform import normalize_platform_name
from tests.common.reporting import SessionReportStore
from tests.common.reporting import artifact_dir
from tests.common.reporting import resolve_case_name
from tests.common.reporting import safe_artifact_name
from tests.lysora.data import get_lysora_default_account
from tests.ruijieCloud.data import get_ruijie_cloud_accounts, get_smoke_account

try:
    import allure
except Exception:  # pragma: no cover
    allure = None

PROJECT_ROOT = Path(__file__).parent
REPORTS_ROOT = PROJECT_ROOT / "reports"
SCREENSHOTS_ROOT = REPORTS_ROOT / "screenshots"
VIDEOS_ROOT = REPORTS_ROOT / "videos"


def _load_local_env_file() -> None:
    env_path = PROJECT_ROOT / ".env"
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


def _env_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _results_file() -> Path:
    return Path(os.getenv("TEST_RESULTS_FILE", str(REPORTS_ROOT / "test_results.json")))


def _report_file() -> Path:
    return Path(os.getenv("TEST_REPORT_FILE", str(REPORTS_ROOT / "test_report.html")))


def _android_capabilities() -> dict[str, Any]:
    caps: dict[str, Any] = {
        "platformName": "Android",
        "appium:automationName": os.getenv("APPIUM_AUTOMATION_NAME", "UiAutomator2"),
        "appium:deviceName": os.getenv("APPIUM_DEVICE_NAME", "Android Device"),
        "appium:noReset": _env_bool("APPIUM_NO_RESET", True),
        "appium:newCommandTimeout": _env_int("APPIUM_NEW_COMMAND_TIMEOUT", 240),
    }
    device_id = (os.getenv("APPIUM_DEVICE_ID") or os.getenv("APPIUM_UDID") or "").strip()
    if device_id:
        caps["appium:udid"] = device_id
    return caps


def _ios_capabilities() -> dict[str, Any]:
    caps: dict[str, Any] = {
        "platformName": "iOS",
        "appium:automationName": os.getenv("APPIUM_AUTOMATION_NAME", "XCUITest"),
        "appium:deviceName": os.getenv("APPIUM_DEVICE_NAME", "iPhone"),
        "appium:noReset": _env_bool("APPIUM_NO_RESET", True),
        "appium:newCommandTimeout": _env_int("APPIUM_NEW_COMMAND_TIMEOUT", 240),
    }
    platform_version = (os.getenv("IOS_PLATFORM_VERSION") or "").strip()
    if platform_version:
        caps["appium:platformVersion"] = platform_version
    device_id = (os.getenv("APPIUM_DEVICE_ID") or os.getenv("APPIUM_UDID") or "").strip()
    if device_id:
        caps["appium:udid"] = device_id
    return caps


def _build_appium_options(platform_name: str):
    if platform_name == "ios":
        return XCUITestOptions().load_capabilities(_ios_capabilities())
    return UiAutomator2Options().load_capabilities(_android_capabilities())


def _resolve_app_id(android_env: str, android_default: str | None, ios_env: str, ios_default: str | None, platform_name: str) -> str | None:
    if platform_name == "ios":
        return (os.getenv(ios_env) or ios_default or "").strip() or None
    return (os.getenv(android_env) or android_default or "").strip() or None


_load_local_env_file()
_report_store = SessionReportStore(project_root=PROJECT_ROOT)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "case_name(name): custom display name for reports")
    config.addinivalue_line("markers", "smoke: smoke tests")
    config.addinivalue_line("markers", "full: full regression tests")
    config.addinivalue_line("markers", "lysora: Lysora test cases")
    config.addinivalue_line("markers", "ruijieCloud: RuijieCloud test cases")


@pytest.fixture(scope="session", autouse=True)
def ensure_report_dirs() -> None:
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_ROOT.mkdir(parents=True, exist_ok=True)
    VIDEOS_ROOT.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def mobile_platform() -> str:
    return normalize_platform_name(os.getenv("APPIUM_PLATFORM_NAME"))


@pytest.fixture(scope="session")
def appium_server_url() -> str:
    return os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723")


@pytest.fixture(scope="session")
def appium_options(mobile_platform: str):
    return _build_appium_options(mobile_platform)


@pytest.fixture(scope="session")
def driver(appium_server_url: str, appium_options):
    mobile_driver = webdriver.Remote(appium_server_url, options=appium_options)
    mobile_driver.implicitly_wait(2)
    yield mobile_driver
    mobile_driver.quit()


@pytest.fixture(scope="session")
def lysora_app_id(mobile_platform: str) -> str:
    app_id = _resolve_app_id(
        android_env="LYSORA_APP_PACKAGE",
        android_default="com.lysora.lyapp",
        ios_env="LYSORA_IOS_BUNDLE_ID",
        ios_default=None,
        platform_name=mobile_platform,
    )
    if not app_id:
        raise RuntimeError(f"Lysora app id is not configured for platform: {mobile_platform}")
    return app_id


@pytest.fixture(scope="session")
def ruijiecloud_app_id(mobile_platform: str) -> str | None:
    return _resolve_app_id(
        android_env="RUIJIECLOUD_APP_PACKAGE",
        android_default=os.getenv("REEYEE_APP_PACKAGE"),
        ios_env="RUIJIECLOUD_IOS_BUNDLE_ID",
        ios_default=os.getenv("REEYEE_IOS_BUNDLE_ID"),
        platform_name=mobile_platform,
    )


@pytest.fixture(scope="session")
def lysora_package(lysora_app_id: str) -> str:
    return lysora_app_id


@pytest.fixture(scope="session")
def ruijiecloud_package(ruijiecloud_app_id: str | None) -> str | None:
    return ruijiecloud_app_id


@pytest.fixture(scope="session")
def lysora_account():
    return get_lysora_default_account()


@pytest.fixture(scope="session")
def ruijiecloud_accounts():
    return get_ruijie_cloud_accounts()


@pytest.fixture(scope="session")
def ruijiecloud_smoke_account():
    return get_smoke_account()


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

    video_name = f"{safe_artifact_name(request.node.nodeid)}.mp4"
    video_path = artifact_dir(VIDEOS_ROOT, request.node) / video_name
    try:
        video_bytes = b64decode(video_base64)
        video_path.write_bytes(video_bytes)
        _report_store.attach_artifact(request.node.nodeid, "video", video_path)
        if allure is not None:
            allure.attach(
                video_bytes,
                name=f"{request.node.name}-video",
                attachment_type=allure.attachment_type.MP4,
            )
    except Exception:
        pass


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when != "call":
        return

    setattr(report, "case_name", resolve_case_name(item, item.nodeid))
    setattr(report, "platform", item.funcargs.get("mobile_platform", "android"))
    current_driver = item.funcargs.get("driver")
    if not current_driver:
        return

    file_name = f"{item.name}_{report.outcome}.png"
    file_path = artifact_dir(SCREENSHOTS_ROOT, item) / file_name
    try:
        current_driver.save_screenshot(str(file_path))
        _report_store.attach_artifact(item.nodeid, "screenshot", file_path)
        if allure is not None:
            allure.attach(
                file_path.read_bytes(),
                name=f"{item.name}-screenshot-{report.outcome}",
                attachment_type=allure.attachment_type.PNG,
            )
    except Exception:
        pass


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.when != "call":
        return
    _report_store.add_result(report)


def pytest_sessionfinish(session, exitstatus) -> None:
    payload = _report_store.build_payload()
    results_file = _results_file()
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        from report_generator import generate_report

        report_file = _report_file()
        report_file.parent.mkdir(parents=True, exist_ok=True)
        generate_report(results_file, report_file)
    except Exception:
        pass
