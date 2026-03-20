from __future__ import annotations

import json
import os
import platform
import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class RemoteWsRuntime:
    lock: threading.Lock = field(default_factory=threading.Lock)
    send_lock: threading.Lock = field(default_factory=threading.Lock)
    log_lock: threading.Lock = field(default_factory=threading.Lock)
    stop_event: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None
    app: Any = None
    status_state: dict[str, Any] = field(
        default_factory=lambda: {
            "enabled": False,
            "url": "",
            "connected": False,
            "client_id": "",
            "last_error": "",
            "last_connect_ts": 0,
            "last_message_ts": 0,
            "last_heartbeat_ts": 0,
        }
    )


@dataclass
class RemoteWsDeps:
    reports_root: Path
    remote_ws_log_file: Path
    default_host: str
    default_port: int
    env_int: Callable[[str, int], int]
    get_running_task_ids: Callable[[], list[str]]
    remote_ws_exec_command: Callable[[str, dict[str, Any]], dict[str, Any]]


def remote_ws_client_id() -> str:
    raw = (os.getenv("REMOTE_WS_CLIENT_ID") or "").strip()
    if raw:
        return raw
    host = platform.node().strip() or socket.gethostname().strip() or "desktop-client"
    return f"{host}-{os.getpid()}"


def remote_ws_enabled() -> bool:
    raw = (os.getenv("REMOTE_WS_ENABLED") or "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    return bool((os.getenv("REMOTE_WS_URL") or "").strip())


def remote_ws_set_status(runtime: RemoteWsRuntime, **kwargs: Any) -> None:
    with runtime.lock:
        runtime.status_state.update(kwargs)


def remote_ws_status(runtime: RemoteWsRuntime) -> dict[str, Any]:
    with runtime.lock:
        return dict(runtime.status_state)


def remote_ws_log(runtime: RemoteWsRuntime, deps: RemoteWsDeps, event: str, **fields: Any) -> None:
    deps.reports_root.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    payload = {"event": event, **fields}
    safe_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    line = f"[{ts}] {safe_payload}\n"
    try:
        with runtime.log_lock:
            with deps.remote_ws_log_file.open("a", encoding="utf-8") as f:
                f.write(line)
    except Exception:
        pass


def read_remote_ws_log_lines(deps: RemoteWsDeps, max_lines: int = 200) -> list[str]:
    if max_lines <= 0:
        max_lines = 1
    max_lines = min(max_lines, 2000)
    if not deps.remote_ws_log_file.exists():
        return []
    try:
        lines = deps.remote_ws_log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []
    if len(lines) <= max_lines:
        return lines
    return lines[-max_lines:]


def _remote_ws_send_json(runtime: RemoteWsRuntime, deps: RemoteWsDeps, payload: dict[str, Any]) -> bool:
    app = runtime.app
    if app is None:
        return False
    try:
        with runtime.send_lock:
            app.send(json.dumps(payload, ensure_ascii=False))
        return True
    except Exception as exc:
        remote_ws_set_status(runtime, last_error=str(exc), connected=False)
        remote_ws_log(runtime, deps, "send_failed", error=str(exc), payload_type=str(payload.get("type") or "unknown"))
        return False


def _remote_ws_heartbeat_payload(deps: RemoteWsDeps) -> dict[str, Any]:
    running_task_ids = deps.get_running_task_ids()
    bind_host = (os.getenv("DESKTOP_WEB_HOST") or deps.default_host).strip() or deps.default_host
    bind_port = deps.env_int("DESKTOP_WEB_PORT", deps.default_port)
    desktop_base_url = (os.getenv("REMOTE_WS_PUBLIC_BASE_URL") or "").strip() or f"http://{bind_host}:{bind_port}"
    return {
        "type": "heartbeat",
        "client_id": remote_ws_client_id(),
        "data": {
            "status": "running" if running_task_ids else "idle",
            "running_task_count": len(running_task_ids),
            "running_task_ids": running_task_ids,
            "desktop_base_url": desktop_base_url,
            "ts": int(time.time()),
        },
    }


def _remote_ws_handle_message(runtime: RemoteWsRuntime, deps: RemoteWsDeps, raw: str) -> None:
    remote_ws_set_status(runtime, last_message_ts=int(time.time()))
    try:
        msg = json.loads(raw)
    except Exception:
        remote_ws_log(runtime, deps, "message_parse_failed", raw_preview=raw[:200])
        return
    msg_type = str(msg.get("type") or "").strip().lower()
    remote_ws_log(runtime, deps, "message_received", message_type=msg_type or "unknown")
    if msg_type == "command":
        action = str(msg.get("action") or "").strip()
        request_id = str(msg.get("request_id") or "").strip()
        payload = msg.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        try:
            result = deps.remote_ws_exec_command(action, payload)
            ok = bool(result.get("ok", True)) if isinstance(result, dict) else True
            resp = {
                "type": "response",
                "client_id": remote_ws_client_id(),
                "request_id": request_id,
                "action": action,
                "data": result,
                "ok": ok,
            }
        except Exception as exc:
            resp = {
                "type": "response",
                "client_id": remote_ws_client_id(),
                "request_id": request_id,
                "action": action,
                "ok": False,
                "error": str(exc),
            }
        _remote_ws_send_json(runtime, deps, resp)
    elif msg_type in {"register_ack", "heartbeat_ack"}:
        remote_ws_set_status(runtime, last_heartbeat_ts=int(time.time()))
        remote_ws_log(runtime, deps, "message_ack", message_type=msg_type)


def _remote_ws_heartbeat_loop(runtime: RemoteWsRuntime, deps: RemoteWsDeps, app: Any, interval_sec: int) -> None:
    while not runtime.stop_event.is_set():
        if runtime.app is not app:
            return
        _remote_ws_send_json(runtime, deps, _remote_ws_heartbeat_payload(deps))
        remote_ws_set_status(runtime, last_heartbeat_ts=int(time.time()))
        runtime.stop_event.wait(max(1, interval_sec))


def _remote_ws_runner(runtime: RemoteWsRuntime, deps: RemoteWsDeps, websocket_client_module: Any) -> None:
    if websocket_client_module is None:
        remote_ws_set_status(runtime, last_error="websocket-client 未安装", enabled=False)
        remote_ws_log(runtime, deps, "disabled", reason="websocket-client missing")
        return
    ws_url = (os.getenv("REMOTE_WS_URL") or "").strip()
    if not ws_url:
        remote_ws_set_status(runtime, enabled=False, url="", connected=False)
        remote_ws_log(runtime, deps, "disabled", reason="REMOTE_WS_URL empty")
        return
    remote_ws_set_status(runtime, enabled=True, url=ws_url, client_id=remote_ws_client_id())
    remote_ws_log(runtime, deps, "runner_started", ws_url=ws_url, client_id=remote_ws_client_id())
    heartbeat_sec = max(5, deps.env_int("REMOTE_WS_HEARTBEAT_SEC", 15))
    reconnect_sec = max(2, deps.env_int("REMOTE_WS_RECONNECT_SEC", 5))
    ping_interval = max(10, deps.env_int("REMOTE_WS_PING_INTERVAL_SEC", 20))
    ping_timeout = max(5, deps.env_int("REMOTE_WS_PING_TIMEOUT_SEC", 10))

    while not runtime.stop_event.is_set():
        def _on_open(app: Any) -> None:
            remote_ws_set_status(runtime, connected=True, last_connect_ts=int(time.time()), last_error="")
            remote_ws_log(runtime, deps, "connected", ws_url=ws_url, client_id=remote_ws_client_id())
            bind_host = (os.getenv("DESKTOP_WEB_HOST") or deps.default_host).strip() or deps.default_host
            bind_port = deps.env_int("DESKTOP_WEB_PORT", deps.default_port)
            desktop_base_url = (os.getenv("REMOTE_WS_PUBLIC_BASE_URL") or "").strip() or f"http://{bind_host}:{bind_port}"
            _remote_ws_send_json(
                runtime,
                deps,
                {
                    "type": "register",
                    "client_id": remote_ws_client_id(),
                    "data": {
                        "hostname": platform.node(),
                        "pid": os.getpid(),
                        "status": "online",
                        "version": "desktop-web-app",
                        "desktop_base_url": desktop_base_url,
                    },
                },
            )
            threading.Thread(
                target=_remote_ws_heartbeat_loop,
                args=(runtime, deps, app, heartbeat_sec),
                daemon=True,
            ).start()

        def _on_message(_: Any, message: str) -> None:
            _remote_ws_handle_message(runtime, deps, message)

        def _on_error(_: Any, err: Any) -> None:
            remote_ws_set_status(runtime, last_error=str(err), connected=False)
            remote_ws_log(runtime, deps, "error", error=str(err))

        def _on_close(_: Any, __: Any, ___: Any) -> None:
            remote_ws_set_status(runtime, connected=False)
            remote_ws_log(runtime, deps, "closed")

        app = websocket_client_module.WebSocketApp(
            ws_url,
            on_open=_on_open,
            on_message=_on_message,
            on_error=_on_error,
            on_close=_on_close,
        )
        runtime.app = app
        try:
            app.run_forever(ping_interval=ping_interval, ping_timeout=ping_timeout)
        except Exception as exc:
            remote_ws_set_status(runtime, last_error=str(exc), connected=False)
            remote_ws_log(runtime, deps, "run_forever_exception", error=str(exc))
        if runtime.stop_event.wait(reconnect_sec):
            remote_ws_log(runtime, deps, "runner_stopped")
            break
        remote_ws_log(runtime, deps, "reconnecting", wait_sec=reconnect_sec)


def start_remote_ws_if_needed(runtime: RemoteWsRuntime, deps: RemoteWsDeps, websocket_client_module: Any) -> None:
    if not remote_ws_enabled():
        remote_ws_set_status(runtime, enabled=False)
        remote_ws_log(runtime, deps, "startup_skipped", reason="REMOTE_WS disabled")
        return
    if runtime.thread and runtime.thread.is_alive():
        remote_ws_log(runtime, deps, "startup_skipped", reason="thread already running")
        return
    runtime.stop_event.clear()
    runtime.thread = threading.Thread(
        target=_remote_ws_runner,
        args=(runtime, deps, websocket_client_module),
        daemon=True,
        name="remote-ws-client",
    )
    runtime.thread.start()
    remote_ws_log(runtime, deps, "startup_triggered")

