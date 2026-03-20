from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Mapping


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
    combined = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    return result.returncode, combined.strip()


def _adb(adb_bin: str, serial: str, shell_args: list[str], cwd: Path, timeout: int = 30) -> tuple[int, str]:
    """在指定设备上执行 adb shell 子命令。"""
    return _run_command([adb_bin, "-s", serial, "shell", *shell_args], cwd=cwd, timeout=timeout)


def _get_prop(adb_bin: str, serial: str, prop: str, cwd: Path) -> str:
    """读取设备系统属性，失败时返回 '-'。"""
    code, out = _adb(adb_bin, serial, ["getprop", prop], cwd=cwd)
    return out.strip() or "-" if code == 0 else "-"


def _get_app_version(adb_bin: str, serial: str, package_name: str, cwd: Path) -> str:
    """通过 dumpsys package 读取应用版本号，未安装时返回提示文案。"""
    code, out = _adb(adb_bin, serial, ["dumpsys", "package", package_name], cwd=cwd, timeout=40)
    if code != 0:
        return "未安装"
    m = re.search(r"versionName=([^\s]+)", out)
    return m.group(1) if m else "未安装"


def list_devices(
    adb_bin: str,
    app_config: Mapping[str, Mapping[str, str]],
    project_root: Path,
) -> dict[str, Any]:
    """列举 ADB 设备并补充品牌、型号、系统及应用版本信息。"""
    code, out = _run_command([adb_bin, "devices"], cwd=project_root, timeout=20)
    if code != 0:
        return {"ok": False, "devices": [], "error": out or "无法执行 adb devices"}

    devices: list[dict[str, Any]] = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices") or "\t" not in line:
            continue
        serial, status = line.split("\t", 1)
        serial, status = serial.strip(), status.strip()
        if status != "device":
            devices.append(
                {
                    "serial": serial,
                    "status": status,
                    "brand": "-",
                    "model": "-",
                    "os_version": "-",
                    "app_versions": {},
                }
            )
            continue
        app_versions = {
            k: _get_app_version(adb_bin, serial, v["package_name"], project_root)
            for k, v in app_config.items()
        }
        devices.append(
            {
                "serial": serial,
                "status": status,
                "brand": _get_prop(adb_bin, serial, "ro.product.brand", project_root),
                "model": _get_prop(adb_bin, serial, "ro.product.model", project_root),
                "os_version": _get_prop(adb_bin, serial, "ro.build.version.release", project_root),
                "app_versions": app_versions,
            }
        )
    return {"ok": True, "devices": devices}

