from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4


@dataclass
class TaskRuntime:
    lock: threading.Lock
    tasks: dict[str, dict[str, Any]]
    device_running_task: dict[str, str]


def _read_log_tail(log_path: Path, max_bytes: int = 120_000) -> str:
    if max_bytes <= 0 or not log_path.exists():
        return ""
    with log_path.open("rb") as fp:
        fp.seek(0, os.SEEK_END)
        file_size = fp.tell()
        fp.seek(max(file_size - max_bytes, 0))
        chunk = fp.read()
    return chunk.decode("utf-8", errors="ignore")


def run_tests(
    payload: dict[str, Any],
    *,
    runtime: TaskRuntime,
    app_config: dict[str, dict[str, str]],
    project_root: Path,
    task_log_dir: Path,
    test_results_file: Path,
    report_html_file: Path,
    is_frozen: Callable[[], bool],
    python_executable: str,
    ensure_task_log_dir: Callable[[], None],
    safe_display_path: Callable[[Path], str],
    appium_ready: Callable[[], dict[str, Any]],
    task_report_paths: Callable[[str], tuple[Path, Path]],
    save_task_report_to_db: Callable[[str, Path], bool],
    insert_task_history: Callable[[str, str, str, str, list[str], str], None],
    update_task_history: Callable[..., None],
    set_device_status: Callable[..., None],
) -> dict[str, Any]:
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

    appium_state = appium_ready()
    if not appium_state.get("running"):
        server_url = appium_state.get("server_url") or "http://127.0.0.1:4723"
        detail = appium_state.get("error") or "unknown error"
        return {"ok": False, "error": f"Appium 未启动，请先启动后再执行测试。地址: {server_url}，详情: {detail}"}

    pytest_args = [*test_packages, "-v"]
    if suite in ("smoke", "full"):
        marker_expr = suite
        if app_key in app_config:
            marker_expr = f"{app_key} and {suite}"
        pytest_args.extend(["-m", marker_expr])

    if is_frozen():
        cmd = [python_executable, "--run-pytest", *pytest_args]
    else:
        cmd = [python_executable, "-m", "pytest", *pytest_args]

    with runtime.lock:
        if device in runtime.device_running_task:
            task_id = runtime.device_running_task[device]
            return {"ok": False, "error": f"该设备已有任务在运行中: {task_id}", "task_id": task_id}

    ensure_task_log_dir()
    task_id = uuid4().hex[:12]
    log_path = task_log_dir / f"{task_id}.log"
    task_results, task_report = task_report_paths(task_id)
    task_results.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["APPIUM_UDID"] = device
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONWARNINGS"] = "ignore:pkg_resources is deprecated as an API:UserWarning"
    env["TEST_RESULTS_FILE"] = str(task_results)
    env["TEST_REPORT_FILE"] = str(task_report)

    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
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

    with runtime.lock:
        runtime.tasks[task_id] = task_info
        runtime.device_running_task[device] = task_id

    insert_task_history(task_id, device, app_key, suite, test_packages, str(log_path))
    set_device_status(device, "running", task_id=task_id, message="任务执行中")

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
            with runtime.lock:
                info = runtime.tasks.get(task_id)
                if info is not None:
                    info["status"] = "failed"
                    info["error"] = str(exc)
                runtime.device_running_task.pop(device, None)
            update_task_history(task_id=task_id, status="failed", error=str(exc))
            set_device_status(device, "failed", task_id=task_id, message=str(exc))
            return

        report_ok = False
        post_errors: list[str] = []
        try:
            report_ok = task_report.exists()
            if not report_ok:
                from report_generator import generate_report

                report_ok = generate_report(task_results, task_report)
            allure_output = (
                f"HTML report generated: {safe_display_path(task_report)}"
                if report_ok
                else "HTML report generate failed"
            )
            if report_ok:
                try:
                    shutil.copyfile(task_report, report_html_file)
                    if task_results.exists():
                        shutil.copyfile(task_results, test_results_file)
                except Exception as exc:
                    post_errors.append(f"copy latest report failed: {exc}")
            report_data_ok = save_task_report_to_db(task_id, task_results)
            if not report_data_ok:
                post_errors.append("report data save failed")
        except Exception as exc:
            allure_output = "report post-process failed"
            post_errors.append(str(exc))

        allure_code = 0 if report_ok else 1
        if post_errors:
            allure_output = f"{allure_output}; {'; '.join(post_errors)}"

        with runtime.lock:
            info = runtime.tasks.get(task_id)
            was_stopped = bool(info is not None and info.get("status") == "stopped")
            if info is not None:
                info["pytest_exit_code"] = exit_code
                info["allure_exit_code"] = allure_code
                info["allure_output"] = allure_output
                if not was_stopped:
                    info["status"] = "success" if exit_code == 0 else "failed"
            runtime.device_running_task.pop(device, None)

        final_task_status = "stopped" if was_stopped else ("success" if exit_code == 0 else "failed")
        final_status = "idle" if final_task_status in {"success", "stopped"} else "failed"
        if final_task_status == "stopped":
            final_msg = "任务已停止"
        elif final_status == "idle":
            final_msg = "任务完成"
        else:
            final_msg = "任务失败，请查看日志"
        update_error = "任务被手动停止" if final_task_status == "stopped" else None
        update_task_history(
            task_id=task_id,
            status=final_task_status,
            pytest_exit_code=exit_code,
            allure_exit_code=allure_code,
            error=update_error,
            allure_output=allure_output,
        )
        set_device_status(device, final_status, task_id=task_id, message=final_msg)

    threading.Thread(target=_watch_task, daemon=True).start()
    return {"ok": True, "task_id": task_id, "status": "running"}


def task_status(
    task_id: str,
    *,
    runtime: TaskRuntime,
    task_has_report: Callable[[str], bool],
    task_report_url: Callable[[str], str],
    task_has_report_data: Callable[[str], bool],
    get_task_record: Callable[[str], dict[str, Any] | None],
) -> dict[str, Any]:
    with runtime.lock:
        info = runtime.tasks.get(task_id)
        if info:
            has_report = task_has_report(task_id)
            payload = {
                "ok": True,
                "task_id": task_id,
                "device": info.get("device"),
                "status": info.get("status"),
                "pytest_exit_code": info.get("pytest_exit_code"),
                "allure_exit_code": info.get("allure_exit_code"),
                "allure_output": info.get("allure_output"),
                "error": info.get("error"),
                "has_report": has_report,
                "report_url": task_report_url(task_id) if has_report else None,
                "has_report_data": task_has_report_data(task_id),
            }
            log_path = Path(str(info.get("log_path") or ""))
        else:
            record = get_task_record(task_id)
            if not record:
                return {"ok": False, "error": f"任务不存在: {task_id}"}
            has_report = task_has_report(task_id)
            payload = {
                "ok": True,
                "task_id": task_id,
                "device": record.get("device_serial"),
                "status": record.get("status"),
                "pytest_exit_code": record.get("pytest_exit_code"),
                "allure_exit_code": record.get("allure_exit_code"),
                "allure_output": record.get("allure_output") or "",
                "error": record.get("error"),
                "has_report": has_report,
                "report_url": task_report_url(task_id) if has_report else None,
                "has_report_data": task_has_report_data(task_id),
            }
            log_path = Path(str(record.get("log_path") or ""))
    try:
        payload["pytest_output"] = _read_log_tail(log_path)
    except Exception:
        payload["pytest_output"] = ""
    return payload


def stop_task(
    payload: dict[str, Any],
    *,
    runtime: TaskRuntime,
    set_device_status: Callable[..., None],
    update_task_history: Callable[..., None],
) -> dict[str, Any]:
    task_id = str(payload.get("task_id") or "").strip()
    device = str(payload.get("device") or "").strip()

    with runtime.lock:
        if not task_id and device:
            task_id = runtime.device_running_task.get(device) or ""
        if not task_id:
            return {"ok": False, "error": "task_id 或 device 至少提供一个"}
        info = runtime.tasks.get(task_id)
        if not info:
            return {"ok": False, "error": f"任务不存在: {task_id}"}
        process = info.get("process")
        dev = str(info.get("device") or "")

    if process is None:
        return {"ok": False, "error": "任务进程不存在"}
    if process.poll() is not None:
        set_device_status(dev, "idle", task_id=task_id, message="任务已结束")
        return {"ok": True, "task_id": task_id, "status": "finished"}

    try:
        process.terminate()
        try:
            process.wait(timeout=5)
        except Exception:
            process.kill()
    except Exception as exc:
        return {"ok": False, "error": f"停止任务失败: {exc}"}

    with runtime.lock:
        info = runtime.tasks.get(task_id)
        if info:
            info["status"] = "stopped"
            info["error"] = "任务被手动停止"
        runtime.device_running_task.pop(dev, None)
    update_task_history(task_id=task_id, status="stopped", error="任务被手动停止")
    set_device_status(dev, "idle", task_id=task_id, message="任务已停止")
    return {"ok": True, "task_id": task_id, "status": "stopped"}

