from __future__ import annotations

import json
import re
import subprocess
import threading
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import shutil
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


def _app_id_for_platform(app_item: Mapping[str, str], platform: str) -> str:
    if platform == "ios":
        return str(app_item.get("ios_bundle_id") or app_item.get("package_name") or "")
    return str(app_item.get("package_name") or "")


def _app_config_signature(
    app_config: Mapping[str, Mapping[str, str]],
    platform: str,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (str(key), _app_id_for_platform(value, platform))
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
            "platform": "android",
            "status": status,
            "brand": "-",
            "model": "-",
            "os_version": "-",
            "app_versions": {},
        }

    app_signature = _app_config_signature(app_config, "android")
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
        "platform": "android",
        "status": status,
        "brand": props["brand"],
        "model": props["model"],
        "os_version": props["os_version"],
        "app_versions": app_versions,
    }
    _set_cached_device_entry(serial, status, app_signature, entry)
    return entry


def _normalize_ios_version(raw_version: str) -> str:
    raw = (raw_version or "").strip()
    if not raw:
        return "-"
    # "26.3.1 (23D8133)" -> "26.3.1"
    return raw.split(" ", 1)[0]


def _extract_json_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        for key in ("string", "value", "number", "integer", "double"):
            val = value.get(key)
            if isinstance(val, (str, int, float)):
                return str(val).strip()
    return ""


def _iter_dict_nodes(payload: Any):
    if isinstance(payload, dict):
        yield payload
        for value in payload.values():
            yield from _iter_dict_nodes(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _iter_dict_nodes(item)


def _extract_ios_app_version_from_payload(payload: Any, bundle_id: str) -> str:
    bundle_keys = ("bundleid", "bundle_id", "bundleidentifier", "identifier")
    version_keys = (
        "shortversion",
        "shortversionstring",
        "bundleshortversionstring",
        "version",
        "bundleversion",
    )

    for node in _iter_dict_nodes(payload):
        normalized = {str(k).lower(): v for k, v in node.items()}
        node_bundle_id = ""
        for key in bundle_keys:
            if key in normalized:
                node_bundle_id = _extract_json_text(normalized[key])
                if node_bundle_id:
                    break
        if node_bundle_id != bundle_id:
            continue
        for key in version_keys:
            if key not in normalized:
                continue
            version = _extract_json_text(normalized[key])
            if version:
                return version
    return ""


def _get_ios_app_version(serial: str, bundle_id: str, cwd: Path) -> str:
    if not bundle_id:
        return "-"
    if shutil.which("xcrun") is None:
        return "-"

    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(prefix="devicectl-", suffix=".json", delete=False) as fp:
            tmp_path = fp.name
        code, _ = _run_command(
            [
                "xcrun",
                "devicectl",
                "--timeout",
                "10",
                "--json-output",
                tmp_path,
                "device",
                "info",
                "apps",
                "--device",
                serial,
                "--bundle-id",
                bundle_id,
            ],
            cwd=cwd,
            timeout=20,
        )
        if code != 0 and not Path(tmp_path).exists():
            return "-"
        try:
            payload = json.loads(Path(tmp_path).read_text(encoding="utf-8"))
        except Exception:
            return "-"
        version = _extract_ios_app_version_from_payload(payload, bundle_id)
        if version:
            return version
        # 无命中版本字段，通常代表应用未安装或设备暂不可查询。
        return "未安装" if code == 0 else "-"
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass


def _build_ios_device_entry(
    base_item: Mapping[str, Any],
    app_config: Mapping[str, Mapping[str, str]],
    project_root: Path,
) -> dict[str, Any]:
    serial = str(base_item.get("serial") or "")
    status = str(base_item.get("status") or "")
    app_signature = _app_config_signature(app_config, "ios")
    cached = _get_cached_device_entry(serial, status, app_signature)
    if cached is not None:
        return cached

    if status != "device":
        entry = dict(base_item)
        entry["app_versions"] = {}
        _set_cached_device_entry(serial, status, app_signature, entry)
        return entry

    app_versions = {
        app_key: _get_ios_app_version(serial, _app_id_for_platform(conf, "ios"), project_root)
        for app_key, conf in app_config.items()
    }
    entry = dict(base_item)
    entry["app_versions"] = app_versions
    _set_cached_device_entry(serial, status, app_signature, entry)
    return entry


def _list_ios_devices(
    app_config: Mapping[str, Mapping[str, str]],
    project_root: Path,
) -> tuple[list[dict[str, Any]], str | None]:
    if shutil.which("xcrun") is None:
        return [], None
    code, out = _run_command(["xcrun", "xcdevice", "list", "--timeout", "3"], cwd=project_root, timeout=30)
    if code != 0:
        return [], out or "无法执行 xcrun xcdevice list"
    try:
        payload = json.loads(out)
    except Exception as exc:
        return [], f"解析 iOS 设备列表失败: {exc}"
    if not isinstance(payload, list):
        return [], "iOS 设备列表格式异常"

    devices: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        if bool(item.get("simulator")):
            continue
        platform = str(item.get("platform") or "")
        if "iphoneos" not in platform:
            continue
        serial = str(item.get("identifier") or "").strip()
        if not serial:
            continue
        base_entry = {
            "serial": serial,
            "platform": "ios",
            "status": "device" if bool(item.get("available")) else "unavailable",
            "brand": "Apple",
            "model": str(item.get("modelName") or item.get("name") or "-"),
            "os_version": _normalize_ios_version(str(item.get("operatingSystemVersion") or "")),
            "app_versions": {},
        }
        devices.append(_build_ios_device_entry(base_entry, app_config, project_root))
    return devices, None


def list_devices(
    adb_bin: str,
    app_config: Mapping[str, Mapping[str, str]],
    project_root: Path,
) -> dict[str, Any]:
    """列举 Android/iOS 设备并补充品牌、型号、系统及应用版本信息。"""
    warnings: list[str] = []
    android_devices: list[dict[str, Any]] = []

    code, out = _run_command([adb_bin, "devices"], cwd=project_root, timeout=20)
    if code != 0:
        warnings.append(out or "无法执行 adb devices")
    else:
        parsed_devices: list[tuple[str, str]] = []
        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices") or "\t" not in line:
                continue
            serial, status = line.split("\t", 1)
            parsed_devices.append((serial.strip(), status.strip()))
        if parsed_devices:
            max_workers = min(max(len(parsed_devices), 1), 4)
            ordered: list[dict[str, Any] | None] = [None] * len(parsed_devices)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {
                    executor.submit(_build_device_entry, adb_bin, serial, status, app_config, project_root): idx
                    for idx, (serial, status) in enumerate(parsed_devices)
                }
                for future in as_completed(future_map):
                    ordered[future_map[future]] = future.result()
            android_devices = [item for item in ordered if item is not None]

    ios_devices, ios_error = _list_ios_devices(app_config, project_root)
    if ios_error:
        warnings.append(ios_error)

    devices = [*android_devices, *ios_devices]
    devices.sort(key=lambda item: (str(item.get("platform") or ""), str(item.get("serial") or "")))

    if devices:
        result: dict[str, Any] = {"ok": True, "devices": devices}
        if warnings:
            result["warnings"] = warnings
        return result
    if warnings:
        return {"ok": False, "devices": [], "error": "; ".join(warnings)}
    return {"ok": True, "devices": []}
