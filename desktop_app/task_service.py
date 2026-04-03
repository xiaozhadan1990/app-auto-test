from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .airtest_service import airtest_bin
from .airtest_service import airtest_case_root
from .airtest_service import build_airtest_device_uri
from .airtest_service import case_id
from .airtest_service import find_first_artifact
from .airtest_service import resolve_airtest_cases
from .airtest_service import write_task_html_report
from .airtest_service import write_task_results


@dataclass
class TaskRuntime:
    lock: threading.Lock
    tasks: dict[str, dict[str, Any]]
    device_running_task: dict[str, str]


def _sync_task_report_artifacts(
    *,
    task_id: str,
    task_results: Path,
    task_report: Path,
    test_results_file: Path,
    report_html_file: Path,
    save_task_report_to_db: Callable[[str, Path], bool],
) -> tuple[bool, list[str]]:
    report_ok = task_report.exists()
    sync_errors: list[str] = []

    if report_ok:
        try:
            shutil.copyfile(task_report, report_html_file)
            if task_results.exists():
                shutil.copyfile(task_results, test_results_file)
        except Exception as exc:
            sync_errors.append(f"copy latest report failed: {exc}")

    if task_results.exists():
        report_data_ok = save_task_report_to_db(task_id, task_results)
        if not report_data_ok:
            sync_errors.append("report data save failed")

    return report_ok, sync_errors


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
    task_report_paths: Callable[[str], tuple[Path, Path]],
    save_task_report_to_db: Callable[[str, Path], bool],
    insert_task_history: Callable[[str, str, str, str, list[str], str], None],
    update_task_history: Callable[..., None],
    set_device_status: Callable[..., None],
) -> dict[str, Any]:
    device = (payload.get("device") or "").strip()
    device_platform = (payload.get("device_platform") or "").strip().lower()
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
    if shutil.which(airtest_bin()) is None:
        return {"ok": False, "error": "未找到 airtest 命令，请先确认环境已安装并可在命令行直接执行"}

    case_root = airtest_case_root()
    try:
        resolved_cases = resolve_airtest_cases(test_packages, case_root)
    except FileNotFoundError as exc:
        return {"ok": False, "error": str(exc)}
    if not resolved_cases:
        return {"ok": False, "error": "没有可执行的 Airtest 用例"}

    with runtime.lock:
        if device in runtime.device_running_task:
            task_id = runtime.device_running_task[device]
            return {"ok": False, "error": f"该设备已有任务在运行中: {task_id}", "task_id": task_id}

    ensure_task_log_dir()
    task_id = uuid4().hex[:12]
    log_path = task_log_dir / f"{task_id}.log"
    task_results, task_report = task_report_paths(task_id)
    task_results.parent.mkdir(parents=True, exist_ok=True)
    task_results.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "session_start": datetime.now().isoformat(timespec="seconds"),
                "session_end": "",
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "tests": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    if device_platform in {"android", "ios"}:
        env["AIRTEST_PLATFORM"] = device_platform
    env["AIRTEST_DEVICE"] = device
    env["AIRTEST_CASE_ROOT"] = str(case_root)
    env["TEST_RESULTS_FILE"] = str(task_results)
    env["TEST_REPORT_FILE"] = str(task_report)

    task_info = {
        "task_id": task_id,
        "device": device,
        "status": "running",
        "cmd": [airtest_bin(), "run", *[case_id(item, case_root) for item in resolved_cases]],
        "process": None,
        "log_path": str(log_path),
        "start_time": time.time(),
        "run_exit_code": None,
        "report_exit_code": None,
        "report_output": "",
        "error": None,
    }

    with runtime.lock:
        runtime.tasks[task_id] = task_info
        runtime.device_running_task[device] = task_id

    insert_task_history(task_id, device, app_key, suite, test_packages, str(log_path))
    set_device_status(device, "running", task_id=task_id, message="任务执行中")

    initial_report_ok, initial_sync_errors = _sync_task_report_artifacts(
        task_id=task_id,
        task_results=task_results,
        task_report=task_report,
        test_results_file=test_results_file,
        report_html_file=report_html_file,
        save_task_report_to_db=save_task_report_to_db,
    )
    if initial_report_ok or initial_sync_errors:
        initial_output = (
            f"HTML report generated: {safe_display_path(task_report)}"
            if initial_report_ok
            else "HTML report waiting for first case result"
        )
        if initial_sync_errors:
            initial_output = f"{initial_output}; {'; '.join(initial_sync_errors)}"
        with runtime.lock:
            info = runtime.tasks.get(task_id)
            if info is not None:
                info["report_exit_code"] = 0 if initial_report_ok else None
                info["report_output"] = initial_output

    def _watch_task() -> None:
        exit_code: int | None = None
        last_results_mtime_ns = 0
        last_report_mtime_ns = 0
        sync_errors: list[str] = []
        overall_failed = False
        run_results: list[dict[str, Any]] = []
        session_start = datetime.now().isoformat(timespec="seconds")
        device_uri = build_airtest_device_uri(device_platform, device) if device_platform else device

        def _sync_if_report_changed() -> None:
            nonlocal last_results_mtime_ns, last_report_mtime_ns, sync_errors
            try:
                results_mtime_ns = task_results.stat().st_mtime_ns if task_results.exists() else 0
                report_mtime_ns = task_report.stat().st_mtime_ns if task_report.exists() else 0
            except Exception:
                return
            if results_mtime_ns == last_results_mtime_ns and report_mtime_ns == last_report_mtime_ns:
                return
            report_ok, current_errors = _sync_task_report_artifacts(
                task_id=task_id,
                task_results=task_results,
                task_report=task_report,
                test_results_file=test_results_file,
                report_html_file=report_html_file,
                save_task_report_to_db=save_task_report_to_db,
            )
            last_results_mtime_ns = results_mtime_ns
            last_report_mtime_ns = report_mtime_ns
            sync_errors = current_errors
            with runtime.lock:
                info = runtime.tasks.get(task_id)
                if info is not None:
                    info["report_exit_code"] = 0 if report_ok else None
                    info["report_output"] = (
                        f"HTML report generated: {safe_display_path(task_report)}"
                        if report_ok
                        else "HTML report waiting for first case result"
                    )
                    if current_errors:
                        info["report_output"] = f"{info['report_output']}; {'; '.join(current_errors)}"

        try:
            with log_path.open("w", encoding="utf-8") as fp:
                fp.write(
                    "[runner] launch context:"
                    f" device={device},"
                    f" device_platform={device_platform or '-'},"
                    f" suite={suite},"
                    f" case_root={case_root},"
                    f" device_uri={device_uri}\n"
                )
                fp.flush()
                for index, current_case in enumerate(resolved_cases, start=1):
                    case_key = case_id(current_case, case_root)
                    case_started_at = time.monotonic()
                    case_output_dir = task_results.parent / f"case-{index:03d}"
                    case_output_dir.mkdir(parents=True, exist_ok=True)
                    case_report_file = case_output_dir / "report.html"

                    run_cmd = [
                        airtest_bin(),
                        "run",
                        str(current_case),
                        "--device",
                        device_uri,
                        "--log",
                        str(case_output_dir),
                    ]
                    fp.write(f"\n[airtest] start case {index}: {case_key}\n")
                    fp.write(f"[airtest] cmd: {' '.join(run_cmd)}\n")
                    fp.flush()

                    process = subprocess.Popen(
                        run_cmd,
                        cwd=str(project_root),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="ignore",
                        env=env,
                    )
                    with runtime.lock:
                        info = runtime.tasks.get(task_id)
                        if info is not None:
                            info["process"] = process

                    case_output_lines: list[str] = []
                    if process.stdout is not None:
                        for line in process.stdout:
                            case_output_lines.append(line.rstrip("\n"))
                            fp.write(line)
                            fp.flush()
                    case_exit_code = process.wait()
                    case_duration = time.monotonic() - case_started_at

                    report_cmd = [
                        airtest_bin(),
                        "report",
                        str(current_case),
                        "--log_root",
                        str(case_output_dir),
                        "--outfile",
                        str(case_report_file),
                        "--lang",
                        "zh",
                    ]
                    report_completed = subprocess.run(
                        report_cmd,
                        cwd=str(project_root),
                        check=False,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="ignore",
                        env=env,
                    )
                    if report_completed.stdout:
                        fp.write(report_completed.stdout)
                    if report_completed.stderr:
                        fp.write(report_completed.stderr)
                    fp.flush()

                    screenshot = find_first_artifact(case_output_dir, (".png", ".jpg", ".jpeg"))
                    video = find_first_artifact(case_output_dir, (".mp4", ".mov", ".avi"))
                    screenshot_rel = screenshot.relative_to(project_root).as_posix() if screenshot and screenshot.is_relative_to(project_root) else ""
                    video_rel = video.relative_to(project_root).as_posix() if video and video.is_relative_to(project_root) else ""
                    report_rel = case_report_file.relative_to(project_root).as_posix() if case_report_file.is_relative_to(project_root) else ""
                    error_message = ""
                    if case_exit_code != 0:
                        overall_failed = True
                        tail = "\n".join(case_output_lines[-20:])
                        error_message = tail or f"Airtest exit code: {case_exit_code}"
                    elif report_completed.returncode != 0:
                        error_message = (report_completed.stderr or report_completed.stdout or "").strip()

                    run_results.append(
                        {
                            "case_index": index,
                            "node_id": case_key,
                            "name": current_case.stem,
                            "status": "passed" if case_exit_code == 0 else "failed",
                            "duration": round(case_duration, 3),
                            "app": app_key or "airtest",
                            "screenshot": screenshot_rel,
                            "video": video_rel,
                            "error_message": error_message,
                            "case_report_path": report_rel,
                        }
                    )
                    write_task_results(
                        task_id,
                        run_results,
                        task_results,
                        session_start=session_start,
                        session_end=datetime.now().isoformat(timespec="seconds"),
                    )
                    write_task_html_report(
                        task_id,
                        run_results,
                        task_report,
                        report_path_mapper=lambda value: value,
                        session_start=session_start,
                        session_end=datetime.now().isoformat(timespec="seconds"),
                    )
                    _sync_if_report_changed()

                exit_code = 1 if overall_failed else 0
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

        post_errors: list[str] = []
        try:
            report_ok = task_report.exists() and task_results.exists()
            report_ok, current_sync_errors = _sync_task_report_artifacts(
                task_id=task_id,
                task_results=task_results,
                task_report=task_report,
                test_results_file=test_results_file,
                report_html_file=report_html_file,
                save_task_report_to_db=save_task_report_to_db,
            )
            report_output = (
                f"HTML report generated: {safe_display_path(task_report)}"
                if report_ok
                else "HTML report generate failed"
            )
            post_errors.extend(sync_errors)
            post_errors.extend(current_sync_errors)
        except Exception as exc:
            report_ok = False
            report_output = "report post-process failed"
            post_errors.append(str(exc))

        report_exit_code = 0 if report_ok else 1
        deduped_errors = list(dict.fromkeys(post_errors))
        if deduped_errors:
            report_output = f"{report_output}; {'; '.join(deduped_errors)}"

        with runtime.lock:
            info = runtime.tasks.get(task_id)
            was_stopped = bool(info is not None and info.get("status") == "stopped")
            if info is not None:
                info["run_exit_code"] = exit_code
                info["report_exit_code"] = report_exit_code
                info["report_output"] = report_output
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
            run_exit_code=exit_code,
            report_exit_code=report_exit_code,
            error=update_error,
            report_output=report_output,
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
                "run_exit_code": info.get("run_exit_code"),
                "report_exit_code": info.get("report_exit_code"),
                "report_output": info.get("report_output"),
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
                "run_exit_code": record.get("run_exit_code"),
                "report_exit_code": record.get("report_exit_code"),
                "report_output": record.get("report_output") or "",
                "error": record.get("error"),
                "has_report": has_report,
                "report_url": task_report_url(task_id) if has_report else None,
                "has_report_data": task_has_report_data(task_id),
            }
            log_path = Path(str(record.get("log_path") or ""))
    try:
        payload["log_output"] = _read_log_tail(log_path)
    except Exception:
        payload["log_output"] = ""
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
