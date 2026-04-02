from __future__ import annotations

import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Mapping


_DEVICE_CACHE_TTL_SEC = 10.0
_device_cache_lock = threading.Lock()
_device_cache: dict[str, dict[str, Any]] = {}


def _run_command(
    args: list[str],
    *,
    cwd: Path,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> tuple[int, str]:
    """执行外部命令并返回退出码及合并后的标准输出/错误输出。"""
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout,
            env=env,
        )
    except FileNotFoundError as exc:
        return 127, f"Command not found: {args[0]}\n{exc}"
    except subprocess.TimeoutExpired:
        return 124, f"Command timed out after {timeout}s"
    combined = (result.stdout or "") + \
        ("\n" + result.stderr if result.stderr else "")
    return result.returncode, combined.strip()


def _adb(adb_bin: str, serial: str, shell_args: list[str], cwd: Path, timeout: int = 30) -> tuple[int, str]:
    """在指定设备上执行 adb shell 子命令。"""
    return _run_command([adb_bin, "-s", serial, "shell", *shell_args], cwd=cwd, timeout=timeout)


def _get_prop(adb_bin: str, serial: str, prop: str, cwd: Path) -> str:
    """读取设备系统属性，失败时返回 '-'。"""
    code, out = _adb(adb_bin, serial, ["getprop", prop], cwd=cwd)
    return out.strip() or "-" if code == 0 else "-"


def _get_device_props(adb_bin: str, serial: str, cwd: Path) -> dict[str, str]:
    code, out = _adb(adb_bin, serial, ["getprop"], cwd=cwd)
    if code != 0:
        return {"brand": "-", "model": "-", "os_version": "-"}
    props: dict[str, str] = {}
    for line in out.splitlines():
        match = re.match(r"\[(.+?)\]:\s*\[(.*)\]", line.strip())
        if not match:
            continue
        props[match.group(1)] = match.group(2)
    return {
        "brand": props.get("ro.product.brand", "-") or "-",
        "model": props.get("ro.product.model", "-") or "-",
        "os_version": props.get("ro.build.version.release", "-") or "-",
    }


def _get_app_version(adb_bin: str, serial: str, package_name: str, cwd: Path) -> str:
    """通过 dumpsys package 读取应用版本号，未安装时返回提示文案。"""
    code, out = _adb(adb_bin, serial, [
                     "dumpsys", "package", package_name], cwd=cwd, timeout=40)
    if code != 0:
        return "未安装"
    m = re.search(r"versionName=([^\s]+)", out)
    return m.group(1) if m else "未安装"


def _app_config_signature(app_config: Mapping[str, Mapping[str, str]]) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (str(key), str(value.get("package_name") or ""))
            for key, value in app_config.items()
        )
    )


def _get_cached_device_entry(
    serial: str,
    status: str,
    app_signature: tuple[tuple[str, str], ...],
) -> dict[str, Any] | None:
    now = time.time()
    with _device_cache_lock:
        cached = _device_cache.get(serial)
        if not cached:
            return None
        if cached.get("status") != status:
            return None
        if cached.get("app_signature") != app_signature:
            return None
        if now - float(cached.get("timestamp") or 0.0) > _DEVICE_CACHE_TTL_SEC:
            return None
        entry = cached.get("entry")
        return dict(entry) if isinstance(entry, dict) else None


def _set_cached_device_entry(
    serial: str,
    status: str,
    app_signature: tuple[tuple[str, str], ...],
    entry: dict[str, Any],
) -> None:
    with _device_cache_lock:
        _device_cache[serial] = {
            "status": status,
            "app_signature": app_signature,
            "timestamp": time.time(),
            "entry": dict(entry),
        }


def _build_device_entry(
    adb_bin: str,
    serial: str,
    status: str,
    app_config: Mapping[str, Mapping[str, str]],
    project_root: Path,
) -> dict[str, Any]:
    if status != "device":
        return {
            "serial": serial,
            "status": status,
            "brand": "-",
            "model": "-",
            "os_version": "-",
            "app_versions": {},
        }

    app_signature = _app_config_signature(app_config)
    cached = _get_cached_device_entry(serial, status, app_signature)
    if cached is not None:
        return cached

    props = _get_device_props(adb_bin, serial, project_root)
    app_versions = {
        k: _get_app_version(adb_bin, serial, v["package_name"], project_root)
        for k, v in app_config.items()
    }
    entry = {
        "serial": serial,
        "status": status,
        "brand": props["brand"],
        "model": props["model"],
        "os_version": props["os_version"],
        "app_versions": app_versions,
    }
    _set_cached_device_entry(serial, status, app_signature, entry)
    return entry


def list_devices(
    adb_bin: str,
    app_config: Mapping[str, Mapping[str, str]],
    project_root: Path,
) -> dict[str, Any]:
    """列举 ADB 设备并补充品牌、型号、系统及应用版本信息。"""
    code, out = _run_command([adb_bin, "devices"],
                             cwd=project_root, timeout=20)
    if code != 0:
        return {"ok": False, "devices": [], "error": out or "无法执行 adb devices"}

    parsed_devices: list[tuple[str, str]] = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices") or "\t" not in line:
            continue
        serial, status = line.split("\t", 1)
        parsed_devices.append((serial.strip(), status.strip()))
    if not parsed_devices:
        return {"ok": True, "devices": []}

    max_workers = min(max(len(parsed_devices), 1), 4)
    ordered: list[dict[str, Any] | None] = [None] * len(parsed_devices)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_build_device_entry, adb_bin, serial, status, app_config, project_root): idx
            for idx, (serial, status) in enumerate(parsed_devices)
        }
        for future in as_completed(future_map):
            ordered[future_map[future]] = future.result()
    devices = [item for item in ordered if item is not None]
    return {"ok": True, "devices": devices}
