from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .airtest_service import airtest_case_root, list_airtest_packages, list_airtest_script_dirs


def list_script_directories() -> list[dict[str, str]]:
    return list_airtest_script_dirs(airtest_case_root())


def list_test_packages(
    app_key: str,
    app_config: Mapping[str, Mapping[str, str]],
    project_root: Path,
    device_platform: str | None = None,
) -> list[dict[str, str | int]]:
    """返回外部 Airtest 目录中的可执行脚本列表。"""
    del app_config, project_root, device_platform
    script_dirs = list_airtest_script_dirs(airtest_case_root())
    known_keys = {item["key"] for item in script_dirs}
    selected_dir = app_key if app_key in known_keys else (script_dirs[0]["key"] if script_dirs else None)
    return list_airtest_packages(
        airtest_case_root(),
        script_dir=selected_dir,
        exclude_common=True,
    )
