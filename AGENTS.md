# Codex Agent Guide

## Purpose

This file is for coding agents working in this repository.

Use it to understand:

- what this project does
- where the real entry points are
- how to run and verify changes
- what files usually need to change together
- what constraints must not be broken

## Project Summary

This repository is an Android mobile automation test runner with a desktop web UI.

Main capabilities:

- run Appium + Pytest test suites
- manage devices from a Flask backend
- show execution status and task history
- generate HTML test reports
- optionally expose remote control through WebSocket

This is not just a test folder and not just a frontend app. It is a combined system:

- Python backend
- React frontend
- pytest/Appium execution pipeline
- report storage and rendering

## First Files To Read

When starting work, read these files first:

1. `desktop_web_app.py`
2. `desktop_app/services_container.py`
3. `desktop_app/api.py`
4. `desktop_app/task_service.py`
5. `web-ui/src/App.tsx`

That reading order usually reveals the real control flow quickly.

## Key Entry Points

### Backend entry

- `desktop_web_app.py`

Responsibilities:

- load local `.env`
- compute runtime/resource paths
- create the service container
- create the Flask app
- initialize runtime DB
- optionally start remote WebSocket client
- launch the desktop web server

### Backend composition root

- `desktop_app/services_container.py`

Responsibilities:

- wire all backend services together
- expose unified methods to API routes
- centralize path resolution and runtime dependencies

Avoid putting real business logic into `desktop_web_app.py` when extending features.

### API layer

- `desktop_app/api.py`

Responsibilities:

- define Flask routes
- parse request payloads and query params
- call service container methods
- return JSON or files

Keep route handlers thin.

### Frontend entry

- `web-ui/src/App.tsx`

Current reality:

- a large amount of UI logic lives in this file
- device management, task execution, history, and report UI are all connected here

Before changing frontend behavior, inspect the existing API call shape in this file.

## Major Backend Modules

- `desktop_app/task_service.py`
  - starts pytest subprocesses
  - tracks in-memory task state
  - prevents concurrent runs on the same device
  - watches task output
  - updates DB status and report state

- `desktop_app/report_service.py`
  - resolves report paths
  - saves task report data into DB
  - reads report summaries and case details
  - resolves report asset paths

- `desktop_app/db_service.py`
  - owns SQLite access
  - stores device runtime status
  - stores task history
  - stores report summary and case rows

- `desktop_app/device_service.py`
  - queries devices through `adb`
  - fetches device metadata and app versions

- `desktop_app/package_service.py`
  - lists test packages for each app
  - builds display labels for frontend selection

- `desktop_app/remote_ws_service.py`
  - optional remote command channel
  - status, logs, command dispatch, heartbeat

## Frontend Stack

- React 18
- TypeScript
- Vite
- Ant Design

Frontend source:

- `web-ui/`

Built frontend output served by Flask:

- `ui/`

When frontend assets change, keep in mind the runtime app serves static files from the built `ui/` directory, not from `web-ui/src/`.

## Common Commands

### Start backend

```powershell
uv run python .\desktop_web_app.py
```

### Start frontend dev server

```powershell
cd .\web-ui
yarn dev
```

### Start both

```powershell
.\start_dev_all.ps1
```

### Run tests directly

```powershell
uv run pytest tests/
uv run pytest tests/ -m smoke
uv run pytest tests/ -m "lysora and smoke"
uv run pytest tests/ -m ruijieCloud
```

### Run tests with helper script

```powershell
.\run_tests_and_allure.ps1 -Suite smoke
.\run_tests_and_allure.ps1 -Suite full -Component lysora -OpenReport
```

### Frontend build

```powershell
cd .\web-ui
yarn build
```

### Package desktop app

```powershell
uv sync
.\build_web_ui.bat
```

## Environment Assumptions

Expected local dependencies:

- Python
- Node.js and yarn
- Appium server
- adb
- Android device or emulator

Important env vars from `.env`:

- `APPIUM_SERVER_URL`
- `APPIUM_UDID`
- `DESKTOP_WEB_HOST`
- `DESKTOP_WEB_PORT`
- `DESKTOP_WEB_AUTO_PORT_FALLBACK`
- `LYSORA_APP_PACKAGE`
- `RUIJIECLOUD_APP_PACKAGE`
- `REMOTE_WS_ENABLED`
- `REMOTE_WS_URL`

## Runtime Outputs

- `reports/runtime_state.db`
  - SQLite runtime database

- `reports/task-logs/`
  - per-task log files

- `reports/task-reports/<task_id>/`
  - per-task `test_results.json`
  - per-task `test_report.html`

- `reports/test_results.json`
  - latest copied task result

- `reports/test_report.html`
  - latest copied report

## Core Execution Model

Typical flow for running tests:

1. frontend calls `POST /api/run_tests`
2. route delegates to `services_container.run_tests()`
3. `task_service.run_tests()` validates payload and Appium availability
4. backend starts a pytest subprocess
5. in-memory task state is updated
6. SQLite task history and device status are updated
7. watcher thread captures logs and final exit code
8. report post-processing runs
9. report data is saved into DB
10. frontend polls task status and report data endpoints

If you change task execution, inspect `desktop_app/task_service.py` first.

## API Surfaces That Commonly Matter

Frequently used endpoints:

- `POST /api/list_devices`
- `GET /api/get_app_options`
- `POST /api/list_test_packages`
- `POST /api/run_tests`
- `GET /api/task_status/<task_id>`
- `GET /api/task_history`
- `POST /api/stop_task`
- `GET /api/task_report/<task_id>`
- `GET /api/task_report_data/<task_id>`
- `GET /api/device_status/<device_serial>`
- `GET /api/appium_ready`

## File Coupling Rules

When changing one of these areas, also inspect the linked files.

### If you change API payloads or response fields

Also inspect:

- `desktop_app/api.py`
- `desktop_app/services_container.py`
- relevant backend service file
- `web-ui/src/App.tsx`

### If you change task execution behavior

Also inspect:

- `desktop_app/task_service.py`
- `desktop_app/services_container.py`
- `conftest.py`
- any report generation code that depends on task output files

### If you change report structure or asset URLs

Also inspect:

- `desktop_app/report_service.py`
- `desktop_app/db_service.py`
- `web-ui/src/App.tsx`

### If you change device status or device locking behavior

Also inspect:

- `desktop_app/task_service.py`
- `desktop_app/db_service.py`
- `desktop_app/device_service.py`
- `web-ui/src/App.tsx`

### If you change path handling

Also inspect:

- `desktop_web_app.py`
- `desktop_app/services_container.py`
- report asset resolution logic
- any code that assumes source mode only

## Important Constraints

### Keep the entry point light

Do not move business logic into `desktop_web_app.py` unless absolutely necessary.

Prefer:

- service module changes
- service container wiring
- thin API routes

### Respect source mode and packaged mode

The app supports both:

- source execution
- packaged execution through PyInstaller

Path changes must consider:

- `RESOURCE_ROOT`
- `RUNTIME_ROOT`
- generated report locations
- built frontend asset locations

Do not assume only local source mode.

### Keep state consistent

Task state exists in more than one place:

- in-memory runtime state
- SQLite runtime state
- frontend polling/rendered state

When changing task lifecycle behavior, make sure all three stay aligned.

### One device, one running task

Current behavior prevents concurrent execution on the same device.

Do not break this by accident when touching task scheduling logic.

### Keep routes thin

`desktop_app/api.py` should stay close to transport logic, not business orchestration.

## Testing Conventions

Tests currently live under:

- `tests/lysora/`
- `tests/ruijieCloud/`

Common markers:

- `smoke`
- `full`
- `lysora`
- `ruijieCloud`

The backend builds pytest `-m` expressions from `suite` and `app_key`.

If you introduce new suite concepts or filter behavior, update both backend and frontend assumptions.

## Safe Change Strategy

For most tasks, use this order:

1. trace current control flow
2. change the smallest backend or frontend surface needed
3. verify linked files for schema drift
4. run the narrowest useful validation
5. only then consider cleanup or refactor

Prefer incremental changes over broad rewrites.

## What Not To Do

- do not assume this is a pure frontend project
- do not assume this is a pure pytest project
- do not hardcode paths for source mode only
- do not change API fields without checking the frontend
- do not change task status semantics without checking DB and UI behavior
- do not add unrelated refactors while fixing a small issue

## Quick Troubleshooting Hints

- no devices in UI: check `adb devices` and `/api/list_devices`
- cannot start tasks: check `/api/appium_ready`
- report missing: check `reports/task-reports/<task_id>/`
- history exists but report details are empty: inspect report save flow
- packaged app path bugs: inspect runtime/resource path handling first

## Default Agent Working Style For This Repo

- read before editing
- prefer small, local changes
- verify assumptions against real files
- keep backend responsibilities separated
- keep frontend and backend contracts in sync
- mention risks clearly when you cannot fully verify behavior
