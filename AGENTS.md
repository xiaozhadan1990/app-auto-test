# Codex Agent Guide

## Purpose

This file is for coding agents working in this repository.

Use it to understand:

- what this project is
- which areas are still actively changing
- how new mobile test cases should be added
- which files usually change together
- which stable areas should be avoided unless truly necessary

## Project Summary

This repository is a mobile automation test project with a desktop web runner.

It includes:

- Appium + Pytest test cases under `tests/`
- shared pytest fixtures and report hooks in `conftest.py`
- a Flask backend under `desktop_app/`
- a React frontend under `web-ui/`
- generated runtime outputs under `reports/`

Current reality:

- daily development is now centered on `tests/`
- `desktop_app/`, `web-ui/`, `ui/`, and desktop startup code are mostly stable
- agents should assume non-test directories do not need changes unless the task clearly requires them

## Default Working Assumption

For most requests in this repo, assume the correct change surface is:

1. `tests/`
2. `conftest.py`
3. possibly `pytest.ini`

Only expand beyond that if one of these is true:

- the user explicitly asks for backend or frontend changes
- a test cannot be implemented without new API or runner support
- an existing backend/frontend contract is already broken

Do not proactively refactor stable app code just because it looks improvable.

## First Files To Read

When the task is about writing or updating tests, read these first:

1. `conftest.py`
2. `pytest.ini`
3. the relevant files under `tests/<app_name>/`
4. `tests/templates/README.md`
5. matching files in `tests/templates/` when creating a new case

Only read backend/frontend entry points if the task actually crosses out of the test layer.

## Active Test Structure

Primary working area:

- `tests/common/`
  - shared base page, platform helpers, reporting helpers, common models

- `tests/lysora/`
  - Lysora test cases, flows, pages, test data

- `tests/reyee/`
  - Reyee test cases, flows, pages, test data

- `tests/ruijieCloud/`
  - RuijieCloud test cases, flows, pages, test data

- `tests/templates/`
  - reference templates for adding new cases

Typical per-app structure:

```text
tests/<app>/
  pages/
  flows/
  data.py
  test_*.py
```

Platform split already exists in several apps:

- `pages/android/`
- `pages/ios/`
- top-level page wrappers or factories that hide platform branching

## Recommended Test Layering

Prefer this responsibility split:

- `pages/`
  - locators and direct page interactions

- `flows/`
  - multi-step business actions across one or more pages

- `data.py` or app-specific data modules
  - accounts, seed data, reusable inputs

- `test_*.py`
  - only scenario orchestration, assertions, and markers

Keep test files thin. If a test starts accumulating UI detail, move that detail into a page or flow object.

## Existing Pytest Conventions

Pytest root behavior:

- `pytest.ini` sets `testpaths = tests`
- tests are collected from `tests/`
- default run uses verbose output

Registered markers include:

- `smoke`
- `full`
- `lysora`
- `ruijieCloud`
- `reyee`
- `case_name(name)`
- `case_priority(value)`

Important collection behavior from `conftest.py`:

- tests are sorted by `case_priority`
- missing priorities fall back to a default value
- report snapshots are continuously written during the session
- screenshots and videos are attached through the shared reporting flow

When adding a new case, include an explicit `case_priority` unless there is a good reason not to.

## Fixtures And Shared Capabilities

`conftest.py` is a core part of the test platform. Reuse it before inventing local setup.

Important shared fixtures and helpers include:

- `driver`
- `mobile_platform`
- `appium_server_url`
- `appium_options`
- `lysora_app_id`
- `ruijiecloud_app_id`
- `reyee_app_id`
- account fixtures for supported apps

Prefer:

- shared fixtures from `conftest.py`
- shared helpers from `tests/common/`
- platform-neutral app id fixtures

Avoid:

- hardcoding package names directly inside tests
- duplicating driver setup inside test modules
- implementing one-off reporting logic inside individual tests

## Safe Change Rules

For normal work, change the smallest surface that solves the problem.

Usually this means:

- add or edit a page object
- add or edit a flow
- update test data
- add or edit a `test_*.py`

Before touching stable directories such as `desktop_app/` or `web-ui/`, verify that the request truly needs it.

## File Coupling Rules

If you change a test file:

- inspect the related `flows/`
- inspect the related `pages/`
- inspect the relevant `data.py`

If you change a page object:

- inspect the matching flow files
- inspect tests that import that page
- preserve platform abstraction if Android/iOS split already exists

If you change `conftest.py`:

- inspect `pytest.ini`
- inspect `tests/common/reporting.py`
- inspect representative tests from affected apps
- be extra careful, because this file impacts the whole suite

If you change markers, suite behavior, or collection rules:

- inspect `pytest.ini`
- inspect `conftest.py`
- inspect backend code only if the desktop runner depends on that marker behavior

If you think you need to change backend/frontend code:

- inspect `desktop_app/api.py`
- inspect `desktop_app/task_service.py`
- inspect `desktop_app/services_container.py`
- inspect `web-ui/src/App.tsx`

But treat that as an exception path, not the default path.

## Stable Areas

These areas are important, but usually not the place to start:

- `desktop_web_app.py`
- `desktop_app/`
- `web-ui/`
- `ui/`
- build/packaging scripts

Assume they are stable unless the user explicitly asks for changes there.

Do not make opportunistic cleanup changes in these directories while working on test cases.

## Run Commands

Run the whole suite:

```powershell
uv run pytest tests/
```

Run by marker:

```powershell
uv run pytest tests/ -m smoke
uv run pytest tests/ -m "lysora and smoke"
uv run pytest tests/ -m reyee
uv run pytest tests/ -m ruijieCloud
```

Run with helper script:

```powershell
.\run_tests_and_allure.ps1 -Suite smoke
.\run_tests_and_allure.ps1 -Suite full -Component lysora -OpenReport
```

Start backend manually when needed:

```powershell
uv run python .\desktop_web_app.py
```

Start frontend dev server only if the task really needs UI work:

```powershell
cd .\web-ui
yarn dev
```

## Environment Assumptions

Expected local dependencies:

- Python and `uv`
- Node.js and yarn
- Appium server
- `adb`
- Android device or emulator

Common environment variables:

- `APPIUM_SERVER_URL`
- `APPIUM_PLATFORM_NAME`
- `APPIUM_UDID`
- `LYSORA_APP_PACKAGE`
- `RUIJIECLOUD_APP_PACKAGE`
- `REEYEE_APP_PACKAGE`
- `LYSORA_IOS_BUNDLE_ID`
- `RUIJIECLOUD_IOS_BUNDLE_ID`
- `REEYEE_IOS_BUNDLE_ID`

If platform behavior is involved, prefer using fixtures and helpers rather than reading env vars directly inside each test.

## Runtime Outputs

Common output locations:

- `reports/runtime_state.db`
- `reports/task-logs/`
- `reports/task-reports/<task_id>/`
- `reports/test_results.json`
- `reports/test_report.html`
- `reports/allure-results/`
- `reports/allure-html/`

Do not commit generated runtime artifacts unless the user explicitly asks for that.

## Test Authoring Guidance

When adding a new test case, prefer this sequence:

1. find the closest existing case in the same app
2. reuse or extend an existing page object if possible
3. add a flow when the scenario spans multiple steps
4. keep data in `data.py` or a nearby app data module
5. keep the final test file concise
6. add `case_name` and `case_priority`
7. run the narrowest possible pytest command

For new scenarios, the templates under `tests/templates/` are the safest starting point.

## What Not To Do

- do not assume backend or frontend changes are needed for ordinary test work
- do not hardcode Android package names inside tests when fixtures already exist
- do not duplicate driver setup in test modules
- do not put heavy UI interaction details directly in `test_*.py`
- do not refactor stable app code while only trying to add a test
- do not change global fixtures casually

## Default Agent Working Style For This Repo

- start from `tests/`, not from app code
- prefer small and local edits
- reuse `conftest.py` fixtures and `tests/common/` helpers
- follow the existing page/flow/data/test layering
- treat `desktop_app/` and `web-ui/` as stable unless proven otherwise
- verify the narrowest useful slice after making changes
- clearly call out risks when a change touches shared fixtures or cross-layer behavior
