from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from flask import Flask, Response, jsonify, request, send_file, send_from_directory


@dataclass
class ApiDeps:
    ui_html_file: Path
    ui_assets_dir: Path
    remote_ws_log_file: Path
    app_config: dict[str, dict[str, str]]
    list_devices: Callable[[], dict[str, Any]]
    list_test_packages: Callable[[str, str | None], list[dict[str, Any]]]
    run_tests: Callable[[dict[str, Any]], dict[str, Any]]
    task_status: Callable[[str], dict[str, Any]]
    get_task_history: Callable[..., list[dict[str, Any]]]
    get_task_record: Callable[[str], dict[str, Any] | None]
    task_report_paths: Callable[[str], tuple[Path, Path]]
    get_task_report_data: Callable[..., dict[str, Any] | None]
    resolve_report_asset_path: Callable[[str], Path | None]
    fetch_remote_report_asset: Callable[[str], tuple[bytes, str] | None]
    stop_task: Callable[[dict[str, Any]], dict[str, Any]]
    get_device_status: Callable[[str], dict[str, Any]]
    open_report: Callable[[], dict[str, Any]]
    startup_info: Callable[[], dict[str, Any]]
    appium_ready: Callable[[], dict[str, Any]]
    remote_ws_status: Callable[[], dict[str, Any]]
    read_remote_ws_log_lines: Callable[[int], list[str]]


def register_routes(app: Flask, deps: ApiDeps) -> None:
    @app.get("/")
    def index() -> Any:
        return send_file(deps.ui_html_file)

    @app.get("/assets/<path:filename>")
    def ui_assets(filename: str) -> Any:
        return send_from_directory(deps.ui_assets_dir, filename)

    @app.post("/api/list_devices")
    def api_list_devices() -> Any:
        return jsonify(deps.list_devices())

    @app.get("/api/get_app_options")
    def api_get_app_options() -> Any:
        apps = [{"key": k, "label": v["label"]} for k, v in deps.app_config.items()]
        return jsonify(apps)

    @app.post("/api/list_test_packages")
    def api_list_test_packages() -> Any:
        payload = request.get_json(silent=True) or {}
        app_key = payload.get("app_key") or "lysora"
        device_platform = (payload.get("device_platform") or "").strip().lower() or None
        packages = deps.list_test_packages(app_key, device_platform)
        return jsonify(
            {
                "ok": True,
                "packages": packages,
                "package_paths": [item["value"] for item in packages],
            }
        )

    @app.post("/api/run_tests")
    def api_run_tests() -> Any:
        payload = request.get_json(silent=True) or {}
        return jsonify(deps.run_tests(payload))

    @app.get("/api/task_status/<task_id>")
    def api_task_status(task_id: str) -> Any:
        return jsonify(deps.task_status(task_id))

    @app.get("/api/task_history")
    def api_task_history() -> Any:
        limit_raw = request.args.get("limit", "20")
        device = (request.args.get("device") or "").strip() or None
        status = (request.args.get("status") or "").strip().lower() or None
        if status and status not in {"running", "success", "failed", "stopped"}:
            status = None
        try:
            limit = max(1, min(int(limit_raw), 200))
        except ValueError:
            limit = 20
        return jsonify({"ok": True, "tasks": deps.get_task_history(limit=limit, device=device, status=status)})

    @app.get("/api/task_log/<task_id>")
    def api_task_log(task_id: str) -> Any:
        record = deps.get_task_record(task_id)
        if not record:
            return jsonify({"ok": False, "error": f"task not found: {task_id}"}), 404
        log_path = Path(str(record.get("log_path") or ""))
        if not log_path.exists():
            return jsonify({"ok": False, "error": f"log file not found: {log_path}"}), 404
        return send_file(log_path, as_attachment=True, download_name=f"{task_id}.log", mimetype="text/plain")

    @app.get("/api/task_report/<task_id>")
    def api_task_report(task_id: str) -> Any:
        _, report_file = deps.task_report_paths(task_id)
        if not report_file.exists():
            return jsonify({"ok": False, "error": f"task report not found: {task_id}"}), 404
        return send_file(report_file, mimetype="text/html")

    @app.get("/api/task_report_data/<task_id>")
    def api_task_report_data(task_id: str) -> Any:
        try:
            page = max(1, int(request.args.get("page", "1")))
        except ValueError:
            page = 1
        page_size_raw = (request.args.get("page_size") or "").strip()
        if page_size_raw:
            try:
                page_size = max(1, min(int(page_size_raw), 200))
            except ValueError:
                page_size = 20
        else:
            page_size = None
        status = (request.args.get("status") or "").strip().lower() or None
        if status and status not in {"passed", "failed", "skipped"}:
            status = None
        data = deps.get_task_report_data(task_id, page=page, page_size=page_size, status=status)
        if not data:
            return jsonify({"ok": False, "error": f"task report data not found: {task_id}"}), 404
        return jsonify({"ok": True, "task_id": task_id, **data})

    @app.get("/api/report_asset")
    def api_report_asset() -> Any:
        rel_path = (request.args.get("path") or "").strip()
        if not rel_path:
            return jsonify({"ok": False, "error": "path is required"}), 400
        if rel_path.startswith(("http://", "https://")):
            remote_asset = deps.fetch_remote_report_asset(rel_path)
            if remote_asset is None:
                return jsonify({"ok": False, "error": f"failed to fetch remote asset: {rel_path}"}), 404
            body, content_type = remote_asset
            return Response(body, mimetype=content_type)
        target = deps.resolve_report_asset_path(rel_path)
        if target is None:
            return jsonify({"ok": False, "error": f"file not found or path is invalid: {rel_path}"}), 404
        return send_file(target)

    @app.post("/api/stop_task")
    def api_stop_task() -> Any:
        payload = request.get_json(silent=True) or {}
        return jsonify(deps.stop_task(payload))

    @app.get("/api/device_status/<device_serial>")
    def api_device_status(device_serial: str) -> Any:
        return jsonify({"ok": True, "device_status": deps.get_device_status(device_serial)})

    @app.post("/api/open_report")
    def api_open_report() -> Any:
        return jsonify(deps.open_report())

    @app.get("/api/startup_info")
    def api_startup_info() -> Any:
        return jsonify(deps.startup_info())

    @app.get("/api/appium_ready")
    def api_appium_ready() -> Any:
        return jsonify(deps.appium_ready())

    @app.get("/api/remote_ws_status")
    def api_remote_ws_status() -> Any:
        return jsonify({"ok": True, "status": deps.remote_ws_status()})

    @app.get("/api/remote_ws_log")
    def api_remote_ws_log() -> Any:
        try:
            lines = max(1, min(int(request.args.get("lines", "200")), 2000))
        except Exception:
            lines = 200
        return jsonify({"ok": True, "file": str(deps.remote_ws_log_file), "lines": deps.read_remote_ws_log_lines(lines)})
