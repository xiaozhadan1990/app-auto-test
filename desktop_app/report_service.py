from __future__ import annotations

import json
import mimetypes
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4


def task_report_paths(task_id: str, task_report_dir: Path) -> tuple[Path, Path]:
    """返回指定任务的测试结果 JSON 文件路径和 HTML 报告文件路径。"""
    base = task_report_dir / task_id
    return base / "test_results.json", base / "test_report.html"


def task_report_url(task_id: str) -> str:
    """根据任务 ID 生成对应的 HTML 报告 API URL。"""
    return f"/api/task_report/{task_id}"


def report_asset_url(rel_path: str | None) -> str | None:
    """将报告资源相对路径转换为 API URL。"""
    value = (rel_path or "").strip()
    if not value:
        return None
    return f"/api/report_asset?path={urllib.parse.quote(value)}"


def _remote_report_upload_url() -> str:
    return (os.getenv("REMOTE_REPORT_UPLOAD_URL") or "").strip()


def _remote_report_upload_token() -> str:
    return (os.getenv("REMOTE_REPORT_UPLOAD_TOKEN") or "").strip()


def _remote_report_upload_timeout_sec(env_int: Callable[[str, int], int]) -> int:
    return max(2, env_int("REMOTE_REPORT_UPLOAD_TIMEOUT_SEC", 20))


def fetch_remote_report_asset(
    asset_url: str,
    *,
    env_int: Callable[[str, int], int],
) -> tuple[bytes, str] | None:
    value = asset_url.strip()
    if not value.startswith(("http://", "https://")):
        return None

    headers = {"Accept": "*/*"}
    token = _remote_report_upload_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(value, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=_remote_report_upload_timeout_sec(env_int)) as resp:
            content_type = resp.headers.get_content_type() or "application/octet-stream"
            return resp.read(), content_type
    except Exception:
        return None


def resolve_report_asset_path(
    rel_path: str,
    *,
    reports_root: Path,
    resource_root: Path,
    runtime_root: Path,
    project_root: Path,
) -> Path | None:
    """将报告媒体相对路径解析为本地绝对路径。"""
    value = rel_path.strip()
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return None
    allowed_roots = [reports_root.resolve(), (resource_root / "reports").resolve()]
    candidate_roots = [runtime_root.resolve(), resource_root.resolve(), project_root.resolve()]
    for root in candidate_roots:
        candidate = (root / value).resolve()
        try:
            if any(candidate.is_relative_to(base) for base in allowed_roots):
                if candidate.exists():
                    return candidate
        except Exception:
            continue
    return None


def _upload_report_asset(
    task_id: str,
    case_index: int,
    asset_type: str,
    rel_path: str,
    *,
    reports_root: Path,
    resource_root: Path,
    runtime_root: Path,
    project_root: Path,
    env_int: Callable[[str, int], int],
    remote_ws_client_id: Callable[[], str],
    remote_ws_log: Callable[..., None],
) -> str | None:
    upload_url = _remote_report_upload_url()
    if not upload_url:
        return None

    local_file = resolve_report_asset_path(
        rel_path,
        reports_root=reports_root,
        resource_root=resource_root,
        runtime_root=runtime_root,
        project_root=project_root,
    )
    if local_file is None:
        return None

    boundary = f"----DesktopReportBoundary{uuid4().hex}"
    mime_type = mimetypes.guess_type(local_file.name)[0] or "application/octet-stream"
    token = _remote_report_upload_token()
    fields: list[tuple[str, str]] = [
        ("task_id", task_id),
        ("case_index", str(case_index)),
        ("asset_type", asset_type),
        ("client_id", remote_ws_client_id()),
        ("file_name", local_file.name),
    ]

    body = bytearray()
    for key, value in fields:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        body.extend((value or "").encode("utf-8"))
        body.extend(b"\r\n")
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        (
            f'Content-Disposition: form-data; name="file"; filename="{local_file.name}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8")
    )
    body.extend(local_file.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(upload_url, data=bytes(body), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=_remote_report_upload_timeout_sec(env_int)) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            payload = json.loads(raw) if raw.strip() else {}
    except Exception as exc:
        remote_ws_log(
            "report_asset_upload_failed",
            task_id=task_id,
            case_index=case_index,
            asset_type=asset_type,
            error=str(exc),
            source_path=rel_path,
        )
        return None

    if not isinstance(payload, dict):
        return None
    url: Any = payload.get("url") or payload.get("asset_url") or payload.get("file_url")
    if not url:
        data_field = payload.get("data")
        if isinstance(data_field, dict):
            url = data_field.get("url") or data_field.get("asset_url") or data_field.get("file_url")
        elif isinstance(data_field, str):
            url = data_field
    if isinstance(url, str) and url.strip():
        return url.strip()
    return None


def _rewrite_report_assets_for_remote(
    task_id: str,
    tests: list[dict[str, Any]],
    *,
    reports_root: Path,
    resource_root: Path,
    runtime_root: Path,
    project_root: Path,
    env_int: Callable[[str, int], int],
    remote_ws_client_id: Callable[[], str],
    remote_ws_log: Callable[..., None],
) -> list[dict[str, Any]]:
    upload_url = _remote_report_upload_url()
    if not upload_url:
        return tests
    for idx, case in enumerate(tests, start=1):
        screenshot = str(case.get("screenshot") or "").strip()
        if screenshot and not screenshot.startswith(("http://", "https://")):
            uploaded = _upload_report_asset(
                task_id,
                idx,
                "image",
                screenshot,
                reports_root=reports_root,
                resource_root=resource_root,
                runtime_root=runtime_root,
                project_root=project_root,
                env_int=env_int,
                remote_ws_client_id=remote_ws_client_id,
                remote_ws_log=remote_ws_log,
            )
            if uploaded:
                case["screenshot"] = uploaded
        video = str(case.get("video") or "").strip()
        if video and not video.startswith(("http://", "https://")):
            uploaded = _upload_report_asset(
                task_id,
                idx,
                "video",
                video,
                reports_root=reports_root,
                resource_root=resource_root,
                runtime_root=runtime_root,
                project_root=project_root,
                env_int=env_int,
                remote_ws_client_id=remote_ws_client_id,
                remote_ws_log=remote_ws_log,
            )
            if uploaded:
                case["video"] = uploaded
    return tests


def task_has_report(task_id: str, *, task_report_dir: Path) -> bool:
    _, report_file = task_report_paths(task_id, task_report_dir)
    return report_file.exists()


def task_has_report_data(task_id: str, *, db_conn: Callable[[], Any]) -> bool:
    conn = db_conn()
    try:
        row = conn.execute("SELECT task_id FROM task_report_summary WHERE task_id=?", (task_id,)).fetchone()
    finally:
        conn.close()
    return row is not None


def save_task_report_to_db(
    task_id: str,
    results_file: Path,
    *,
    db_conn: Callable[[], Any],
    reports_root: Path,
    resource_root: Path,
    runtime_root: Path,
    project_root: Path,
    env_int: Callable[[str, int], int],
    remote_ws_client_id: Callable[[], str],
    remote_ws_log: Callable[..., None],
) -> bool:
    if not results_file.exists():
        return False
    try:
        data = json.loads(results_file.read_text(encoding="utf-8"))
    except Exception:
        return False

    tests = data.get("tests", [])
    if not isinstance(tests, list):
        tests = []
    normalized_tests: list[dict[str, Any]] = [dict(t) for t in tests if isinstance(t, dict)]
    tests = _rewrite_report_assets_for_remote(
        task_id,
        normalized_tests,
        reports_root=reports_root,
        resource_root=resource_root,
        runtime_root=runtime_root,
        project_root=project_root,
        env_int=env_int,
        remote_ws_client_id=remote_ws_client_id,
        remote_ws_log=remote_ws_log,
    )
    total = int(data.get("total", len(tests)) or 0)
    passed = int(data.get("passed", 0) or 0)
    failed = int(data.get("failed", 0) or 0)
    skipped = int(data.get("skipped", 0) or 0)
    total_duration = float(sum((t.get("duration", 0) or 0) for t in tests))
    pass_rate = (passed / total * 100.0) if total > 0 else 0.0

    conn = db_conn()
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


def get_task_report_data(task_id: str, *, db_conn: Callable[[], Any]) -> dict[str, Any] | None:
    conn = db_conn()
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
        case["screenshot_url"] = report_asset_url(str(case.get("screenshot") or ""))
        case["video_url"] = report_asset_url(str(case.get("video") or ""))
    return {"summary": summary, "tests": cases}

