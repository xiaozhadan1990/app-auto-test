from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .airtest_service import airtest_case_root, list_airtest_packages


def list_test_packages(
    app_key: str,
    app_config: Mapping[str, Mapping[str, str]],
    project_root: Path,
    device_platform: str | None = None,
) -> list[dict[str, str | int]]:
    """返回外部 Airtest 目录中的可执行脚本列表。"""
    del app_key, app_config, project_root, device_platform
    return list_airtest_packages(airtest_case_root())
