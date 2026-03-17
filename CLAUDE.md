# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Android mobile automation testing framework using Appium + UiAutomator2 + pytest. Supports two apps (Lysora, RuijieCloud) with CLI and desktop Web UI (Flask) execution modes. Tests run on a physical Android device connected via ADB.

## Commands

### Running Tests (CLI via PowerShell)
```powershell
# Run smoke tests
.\run_tests_and_allure.ps1 -Suite smoke

# Run full regression for specific app
.\run_tests_and_allure.ps1 -Suite full -Component lysora -OpenReport

# Run with direct pytest (requires Appium server running)
pytest tests/ -m smoke
pytest tests/ -m "lysora and smoke"
pytest tests/ -m ruijieCloud
pytest tests/lysora/test_lysora_home_logo.py -v   # single test file
```

### Run a Single Test
```bash
pytest tests/lysora/test_lysora_login_my_tab.py::test_lysora_login_and_verify_account_in_my_tab -v
```

### Launch Desktop Web UI
```powershell
.\run_desktop_ui.ps1
```

### Package as Standalone Executable
```powershell
.\package_desktop_ui.ps1
```

## Architecture

### Test Infrastructure (`conftest.py`)
Session-scoped Appium `driver` fixture shared across all tests. Key behaviors:
- Reads device config from `.env` (copy from `.env.example`)
- `record_test_video` auto-fixture records screen video for every test; video saved to `reports/videos/` on completion
- `pytest_runtest_makereport` hook captures screenshots to `reports/screenshots/{app}/` on failure and attaches both screenshots and videos to Allure

### Desktop Web UI (`desktop_web_app.py`)
Flask-based desktop web app. Backend exposes HTTP APIs consumed by `ui/desktop_app.html` in the browser:
- Auto-opens browser when app starts
- Does not manage Appium lifecycle inside UI (Appium should be started/stopped externally)
- Enumerates ADB devices and installed app versions
- Dynamically sets `APPIUM_UDID` env var before spawning pytest subprocess
- Generates and opens Allure HTML reports after test runs

### Test Suites
- `tests/lysora/` — Lysora app tests (home logo pixel analysis, login/account verification)
- `tests/ruijieCloud/` — RuijieCloud app tests (parametrized login/logout cycle across 7 regional accounts)

### Pytest Markers
| Marker | Purpose |
|--------|---------|
| `smoke` | Quick critical-path tests |
| `full` | Full regression |
| `lysora` | Lysora-specific tests |
| `ruijieCloud` | RuijieCloud-specific tests |

### Reporting
Allure results written to `reports/allure-results/`, HTML generated to `reports/allure-html/`. The PowerShell scripts handle `allure generate` + `allure open` automatically.

## Environment Setup

Copy `.env.example` to `.env` and configure:
- `APPIUM_SERVER_URL` — default `http://127.0.0.1:4723`
- `APPIUM_UDID` — ADB device serial (leave blank to auto-detect first device)
- App package names for each supported app

Bundled tools in `build-assets/tools/`: ADB (`tools/adb/`) and Appium + Node.js (`tools/appium/`). The desktop app uses these bundled paths; CLI mode requires system-installed ADB and Appium.

## Test Patterns

Tests use two XPath helper utilities defined in each test file:
- `_first_clickable(driver, selectors, timeout)` — waits for any of a list of selectors to be clickable
- `_first_visible(driver, selectors, timeout)` — waits for any selector to be visible

Selectors are tried in order (accessibility ID preferred, then XPath fallbacks) to handle UI variations across app versions.
