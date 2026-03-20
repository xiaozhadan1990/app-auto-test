from __future__ import annotations

import json
import sqlite3
from typing import Any, Callable


def db_conn(*, reports_root: Any, runtime_db_file: Any) -> sqlite3.Connection:
    """创建并返回一个指向运行时 SQLite 数据库的连接。"""
    reports_root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(runtime_db_file)
    conn.row_factory = sqlite3.Row
    return conn


def init_runtime_db(*, db_conn_fn: Callable[[], sqlite3.Connection]) -> None:
    """初始化运行时 SQLite 数据库结构。"""
    conn = db_conn_fn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS device_runtime_status (
                device_serial TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                task_id TEXT,
                message TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_run_history (
                task_id TEXT PRIMARY KEY,
                device_serial TEXT NOT NULL,
                app_key TEXT,
                suite TEXT,
                test_packages TEXT,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                pytest_exit_code INTEGER,
                allure_exit_code INTEGER,
                error TEXT,
                log_path TEXT,
                allure_output TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_report_summary (
                task_id TEXT PRIMARY KEY,
                session_start TEXT,
                session_end TEXT,
                total INTEGER NOT NULL,
                passed INTEGER NOT NULL,
                failed INTEGER NOT NULL,
                skipped INTEGER NOT NULL,
                total_duration REAL NOT NULL,
                pass_rate REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_report_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                case_index INTEGER NOT NULL,
                node_id TEXT,
                name TEXT,
                status TEXT,
                duration REAL,
                app TEXT,
                screenshot TEXT,
                video TEXT,
                error_message TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_report_cases_task_id ON task_report_cases(task_id)")
        conn.commit()
    finally:
        conn.close()


def set_device_status(
    device_serial: str,
    status: str,
    *,
    db_conn_fn: Callable[[], sqlite3.Connection],
    task_id: str | None = None,
    message: str = "",
) -> None:
    conn = db_conn_fn()
    try:
        conn.execute(
            """
            INSERT INTO device_runtime_status(device_serial, status, task_id, message, updated_at)
            VALUES(?, ?, ?, ?, datetime('now', 'localtime'))
            ON CONFLICT(device_serial) DO UPDATE SET
              status=excluded.status,
              task_id=excluded.task_id,
              message=excluded.message,
              updated_at=excluded.updated_at
            """,
            (device_serial, status, task_id, message),
        )
        conn.commit()
    finally:
        conn.close()


def get_device_status(device_serial: str, *, db_conn_fn: Callable[[], sqlite3.Connection]) -> dict[str, Any]:
    conn = db_conn_fn()
    try:
        row = conn.execute(
            "SELECT device_serial, status, task_id, message, updated_at FROM device_runtime_status WHERE device_serial=?",
            (device_serial,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return {
            "device_serial": device_serial,
            "status": "idle",
            "task_id": None,
            "message": "",
            "updated_at": None,
        }
    return dict(row)


def insert_task_history(
    task_id: str,
    device: str,
    app_key: str,
    suite: str,
    test_packages: list[str],
    log_path: str,
    *,
    db_conn_fn: Callable[[], sqlite3.Connection],
) -> None:
    conn = db_conn_fn()
    try:
        conn.execute(
            """
            INSERT INTO task_run_history(
              task_id, device_serial, app_key, suite, test_packages, status, start_time, log_path
            ) VALUES(?, ?, ?, ?, ?, 'running', datetime('now', 'localtime'), ?)
            """,
            (task_id, device, app_key, suite, json.dumps(test_packages, ensure_ascii=False), log_path),
        )
        conn.commit()
    finally:
        conn.close()


def update_task_history(
    task_id: str,
    status: str,
    *,
    db_conn_fn: Callable[[], sqlite3.Connection],
    pytest_exit_code: int | None = None,
    allure_exit_code: int | None = None,
    error: str | None = None,
    allure_output: str | None = None,
) -> None:
    conn = db_conn_fn()
    try:
        conn.execute(
            """
            UPDATE task_run_history
            SET status=?,
                end_time=datetime('now', 'localtime'),
                pytest_exit_code=?,
                allure_exit_code=?,
                error=?,
                allure_output=?
            WHERE task_id=?
            """,
            (status, pytest_exit_code, allure_exit_code, error, allure_output, task_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_task_history(
    *,
    db_conn_fn: Callable[[], sqlite3.Connection],
    task_has_report: Callable[[str], bool],
    task_report_url: Callable[[str], str],
    task_has_report_data: Callable[[str], bool],
    limit: int = 20,
    device: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    conn = db_conn_fn()
    try:
        if device and status:
            rows = conn.execute(
                """
                SELECT * FROM task_run_history
                WHERE device_serial=? AND status=?
                ORDER BY start_time DESC
                LIMIT ?
                """,
                (device, status, limit),
            ).fetchall()
        elif device:
            rows = conn.execute(
                """
                SELECT * FROM task_run_history
                WHERE device_serial=?
                ORDER BY start_time DESC
                LIMIT ?
                """,
                (device, limit),
            ).fetchall()
        elif status:
            rows = conn.execute(
                """
                SELECT * FROM task_run_history
                WHERE status=?
                ORDER BY start_time DESC
                LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM task_run_history
                ORDER BY start_time DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    items = [dict(r) for r in rows]
    for item in items:
        task_id = str(item.get("task_id") or "")
        has_report = task_has_report(task_id) if task_id else False
        item["has_report"] = has_report
        item["report_url"] = task_report_url(task_id) if has_report else None
        item["has_report_data"] = task_has_report_data(task_id) if task_id else False
    return items


def get_task_record(task_id: str, *, db_conn_fn: Callable[[], sqlite3.Connection]) -> dict[str, Any] | None:
    conn = db_conn_fn()
    try:
        row = conn.execute("SELECT * FROM task_run_history WHERE task_id=?", (task_id,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None

