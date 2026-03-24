from __future__ import annotations

import os
import shutil
import socket
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .api import ApiDeps
from .db_service import db_conn as db_conn_impl
from .db_service import get_device_status as get_device_status_impl
from .db_service import get_task_history as get_task_history_impl
from .db_service import get_task_record as get_task_record_impl
from .db_service import init_runtime_db as init_runtime_db_impl
from .db_service import insert_task_history as insert_task_history_impl
from .db_service import set_device_status as set_device_status_impl
from .db_service import update_task_history as update_task_history_impl
from .device_service import list_devices as list_devices_impl
from .package_service import list_test_packages as list_test_packages_impl
from .remote_ws_service import RemoteWsDeps
from .remote_ws_service import RemoteWsRuntime
from .remote_ws_service import read_remote_ws_log_lines as read_remote_ws_log_lines_impl
from .remote_ws_service import remote_ws_client_id as remote_ws_client_id_impl
from .remote_ws_service import remote_ws_log as remote_ws_log_impl
from .remote_ws_service import remote_ws_status as remote_ws_status_impl
from .remote_ws_service import start_remote_ws_if_needed as start_remote_ws_if_needed_impl
from .report_service import get_task_report_data as get_task_report_data_impl
from .report_service import fetch_remote_report_asset as fetch_remote_report_asset_impl
from .report_service import resolve_report_asset_path as resolve_report_asset_path_impl
from .report_service import save_task_report_to_db as save_task_report_to_db_impl
from .report_service import task_has_report as task_has_report_impl
from .report_service import task_has_report_data as task_has_report_data_impl
from .report_service import task_report_paths as task_report_paths_impl
from .report_service import task_report_url as task_report_url_impl
from .task_service import TaskRuntime
from .task_service import run_tests as run_tests_impl
from .task_service import stop_task as stop_task_impl
from .task_service import task_status as task_status_impl


@dataclass
class DesktopServiceContainer:
    resource_root: Path
    runtime_root: Path
    project_root: Path
    reports_root: Path
    test_results_file: Path
    report_html_file: Path
    runtime_db_file: Path
    task_log_dir: Path
    task_report_dir: Path
    remote_ws_log_file: Path
    app_config: dict[str, dict[str, str]]
    adb_bin: str
    default_host: str
    default_port: int
    tasks_lock: Any
    tasks: dict[str, dict[str, Any]]
    device_running_task: dict[str, str]
    task_runtime: TaskRuntime = field(init=False)
    remote_ws_runtime: RemoteWsRuntime = field(init=False)
    remote_ws_deps: RemoteWsDeps = field(init=False)

    def __post_init__(self) -> None:
        self.task_runtime = TaskRuntime(
            lock=self.tasks_lock,
            tasks=self.tasks,
            device_running_task=self.device_running_task,
        )
        self.remote_ws_runtime = RemoteWsRuntime()
        self.remote_ws_deps = RemoteWsDeps(
            reports_root=self.reports_root,
            remote_ws_log_file=self.remote_ws_log_file,
            default_host=self.default_host,
            default_port=self.default_port,
            env_int=self.env_int,
            get_running_task_ids=self.get_running_task_ids,
            remote_ws_exec_command=self.remote_ws_exec_command,
        )

    def is_frozen(self) -> bool:
        return bool(getattr(sys, "frozen", False))

    def safe_display_path(self, path: Path) -> str:
        p = path.resolve()
        for base in (self.runtime_root, self.resource_root, self.project_root):
            try:
                return p.relative_to(base.resolve()).as_posix()
            except Exception:
                continue
        return str(path)

    def db_conn(self) -> Any:
        return db_conn_impl(reports_root=self.reports_root, runtime_db_file=self.runtime_db_file)

    def init_runtime_db(self) -> None:
        init_runtime_db_impl(db_conn_fn=self.db_conn)

    def set_device_status(self, device_serial: str, status: str, task_id: str | None = None, message: str = "") -> None:
        set_device_status_impl(
            device_serial,
            status,
            db_conn_fn=self.db_conn,
            task_id=task_id,
            message=message,
        )

    def get_device_status(self, device_serial: str) -> dict[str, Any]:
        return get_device_status_impl(device_serial, db_conn_fn=self.db_conn)

    def ensure_task_log_dir(self) -> None:
        self.task_log_dir.mkdir(parents=True, exist_ok=True)

    def task_report_paths(self, task_id: str) -> tuple[Path, Path]:
        return task_report_paths_impl(task_id, self.task_report_dir)

    def task_report_url(self, task_id: str) -> str:
        return task_report_url_impl(task_id)

    def resolve_report_asset_path(self, rel_path: str) -> Path | None:
        return resolve_report_asset_path_impl(
            rel_path,
            reports_root=self.reports_root,
            resource_root=self.resource_root,
            runtime_root=self.runtime_root,
            project_root=self.project_root,
        )

    def fetch_remote_report_asset(self, asset_url: str) -> tuple[bytes, str] | None:
        return fetch_remote_report_asset_impl(asset_url, env_int=self.env_int)

    def task_has_report(self, task_id: str) -> bool:
        return task_has_report_impl(task_id, task_report_dir=self.task_report_dir)

    def task_has_report_data(self, task_id: str) -> bool:
        return task_has_report_data_impl(task_id, db_conn=self.db_conn)

    def save_task_report_to_db(self, task_id: str, results_file: Path) -> bool:
        return save_task_report_to_db_impl(
            task_id,
            results_file,
            db_conn=self.db_conn,
            reports_root=self.reports_root,
            resource_root=self.resource_root,
            runtime_root=self.runtime_root,
            project_root=self.project_root,
            env_int=self.env_int,
            remote_ws_client_id=self.remote_ws_client_id,
            remote_ws_log=self.remote_ws_log,
        )

    def get_task_report_data(self, task_id: str) -> dict[str, Any] | None:
        return get_task_report_data_impl(task_id, db_conn=self.db_conn)

    def insert_task_history(
        self,
        task_id: str,
        device: str,
        app_key: str,
        suite: str,
        test_packages: list[str],
        log_path: str,
    ) -> None:
        insert_task_history_impl(
            task_id,
            device,
            app_key,
            suite,
            test_packages,
            log_path,
            db_conn_fn=self.db_conn,
        )

    def update_task_history(
        self,
        task_id: str,
        status: str,
        pytest_exit_code: int | None = None,
        allure_exit_code: int | None = None,
        error: str | None = None,
        allure_output: str | None = None,
    ) -> None:
        update_task_history_impl(
            task_id,
            status,
            db_conn_fn=self.db_conn,
            pytest_exit_code=pytest_exit_code,
            allure_exit_code=allure_exit_code,
            error=error,
            allure_output=allure_output,
        )

    def get_task_history(
        self, limit: int = 20, device: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        return get_task_history_impl(
            db_conn_fn=self.db_conn,
            task_has_report=self.task_has_report,
            task_report_url=self.task_report_url,
            task_has_report_data=self.task_has_report_data,
            limit=limit,
            device=device,
            status=status,
        )

    def get_task_record(self, task_id: str) -> dict[str, Any] | None:
        return get_task_record_impl(task_id, db_conn_fn=self.db_conn)

    def env_int(self, name: str, default: int) -> int:
        raw = (os.getenv(name) or "").strip()
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    def env_bool(self, name: str, default: bool) -> bool:
        raw = (os.getenv(name) or "").strip().lower()
        if not raw:
            return default
        return raw in {"1", "true", "yes", "on"}

    def get_running_task_ids(self) -> list[str]:
        with self.tasks_lock:
            return list(self.device_running_task.values())

    def remote_ws_client_id(self) -> str:
        return remote_ws_client_id_impl()

    def remote_ws_status(self) -> dict[str, Any]:
        return remote_ws_status_impl(self.remote_ws_runtime)

    def remote_ws_log(self, event: str, **fields: Any) -> None:
        remote_ws_log_impl(self.remote_ws_runtime, self.remote_ws_deps, event, **fields)

    def read_remote_ws_log_lines(self, max_lines: int = 200) -> list[str]:
        return read_remote_ws_log_lines_impl(self.remote_ws_deps, max_lines)

    def remote_ws_exec_command(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        if action == "list_devices":
            return self.list_devices()
        if action == "list_test_packages":
            return {"ok": True, "packages": self.list_test_packages(str(payload.get("app_key") or "lysora"))}
        if action == "run_tests":
            return self.run_tests(payload)
        if action == "stop_task":
            return self.stop_task(payload)
        if action == "task_status":
            task_id = str(payload.get("task_id") or "").strip()
            if not task_id:
                return {"ok": False, "error": "task_id 不能为空"}
            return self.task_status(task_id)
        if action == "task_report_data":
            task_id = str(payload.get("task_id") or "").strip()
            if not task_id:
                return {"ok": False, "error": "task_id 不能为空"}
            data = self.get_task_report_data(task_id)
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
            return {"ok": True, "tasks": self.get_task_history(limit=limit, device=device, status=status)}
        if action == "device_status":
            device = str(payload.get("device_serial") or "").strip()
            if not device:
                return {"ok": False, "error": "device_serial 不能为空"}
            return {"ok": True, "device_status": self.get_device_status(device)}
        if action == "startup_info":
            return self.startup_info()
        if action == "appium_ready":
            return self.appium_ready()
        return {"ok": False, "error": f"unsupported action: {action}"}

    def start_remote_ws_if_needed(self, websocket_client_module: Any) -> None:
        start_remote_ws_if_needed_impl(self.remote_ws_runtime, self.remote_ws_deps, websocket_client_module)

    def list_devices(self) -> dict[str, Any]:
        return list_devices_impl(
            adb_bin=self.adb_bin,
            app_config=self.app_config,
            project_root=self.project_root,
        )

    def list_test_packages(self, app_key: str) -> list[dict[str, str]]:
        return list_test_packages_impl(
            app_key=app_key,
            app_config=self.app_config,
            project_root=self.project_root,
        )

    def startup_info(self) -> dict[str, Any]:
        missing: list[str] = []
        if shutil.which("adb") is None:
            missing.append("adb")
        return {"ok": True, "missing_dependencies": missing}

    def appium_ready(self) -> dict[str, Any]:
        server_url = (os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723") or "").strip().rstrip("/")
        if not server_url:
            return {"ok": True, "running": False, "server_url": "", "error": "APPIUM_SERVER_URL 为空"}
        import urllib.request

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

    def run_tests(self, payload: dict[str, Any]) -> dict[str, Any]:
        return run_tests_impl(
            payload,
            runtime=self.task_runtime,
            app_config=self.app_config,
            project_root=self.project_root,
            task_log_dir=self.task_log_dir,
            test_results_file=self.test_results_file,
            report_html_file=self.report_html_file,
            is_frozen=self.is_frozen,
            python_executable=sys.executable,
            ensure_task_log_dir=self.ensure_task_log_dir,
            safe_display_path=self.safe_display_path,
            appium_ready=self.appium_ready,
            task_report_paths=self.task_report_paths,
            save_task_report_to_db=self.save_task_report_to_db,
            insert_task_history=self.insert_task_history,
            update_task_history=self.update_task_history,
            set_device_status=self.set_device_status,
        )

    def task_status(self, task_id: str) -> dict[str, Any]:
        return task_status_impl(
            task_id,
            runtime=self.task_runtime,
            task_has_report=self.task_has_report,
            task_report_url=self.task_report_url,
            task_has_report_data=self.task_has_report_data,
            get_task_record=self.get_task_record,
        )

    def stop_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        return stop_task_impl(
            payload,
            runtime=self.task_runtime,
            set_device_status=self.set_device_status,
            update_task_history=self.update_task_history,
        )

    def open_report(self) -> dict[str, Any]:
        if not self.report_html_file.exists():
            from report_generator import generate_report

            if not generate_report(self.test_results_file, self.report_html_file):
                return {"ok": False, "error": "暂无报告，且生成失败"}
        try:
            os.startfile(str(self.report_html_file))  # type: ignore[attr-defined]
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def get_free_port(self, host: str, preferred_port: int) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((host, preferred_port)) != 0:
                return preferred_port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock2:
            sock2.bind((host, 0))
            return int(sock2.getsockname()[1])

    def build_api_deps(self) -> ApiDeps:
        return ApiDeps(
            ui_html_file=self.resource_root / "ui" / "index.html",
            ui_assets_dir=self.resource_root / "ui" / "assets",
            remote_ws_log_file=self.remote_ws_log_file,
            app_config=self.app_config,
            list_devices=self.list_devices,
            list_test_packages=self.list_test_packages,
            run_tests=self.run_tests,
            task_status=self.task_status,
            get_task_history=self.get_task_history,
            get_task_record=self.get_task_record,
            task_report_paths=self.task_report_paths,
            get_task_report_data=self.get_task_report_data,
            resolve_report_asset_path=self.resolve_report_asset_path,
            fetch_remote_report_asset=self.fetch_remote_report_asset,
            stop_task=self.stop_task,
            get_device_status=self.get_device_status,
            open_report=self.open_report,
            startup_info=self.startup_info,
            appium_ready=self.appium_ready,
            remote_ws_status=self.remote_ws_status,
            read_remote_ws_log_lines=self.read_remote_ws_log_lines,
        )

