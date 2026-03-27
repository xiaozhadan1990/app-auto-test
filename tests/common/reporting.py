from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pytest

from tests.common.mobile_platform import normalize_platform_name


def safe_test_name(nodeid: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", nodeid).replace("::", "__")


def safe_artifact_name(nodeid: str) -> str:
    value = nodeid.strip()
    if not value:
        return "test_case"
    case_name = value.split("::")[-1]
    return re.sub(r'[\\/:*?"<>|]+', "_", case_name)


def resolve_app_group(node: pytest.Item | pytest.Collector | pytest.TestReport) -> str:
    nodeid = getattr(node, "nodeid", "").lower()
    if "tests/lysora/" in nodeid or "tests\\lysora\\" in nodeid:
        return "lysora"
    if "tests/ruijiecloud/" in nodeid or "tests\\ruijiecloud\\" in nodeid:
        return "ruijieCloud"
    if "tests/reyee/" in nodeid or "tests\\reyee\\" in nodeid:
        return "reyee"
    if hasattr(node, "get_closest_marker"):
        if node.get_closest_marker("lysora"):
            return "lysora"
        if node.get_closest_marker("ruijieCloud"):
            return "ruijieCloud"
        if node.get_closest_marker("reyee"):
            return "reyee"
    return "common"


def resolve_platform_group(
    node: pytest.Item | pytest.Collector | pytest.TestReport,
    platform_name: str | None = None,
) -> str:
    if platform_name:
        return normalize_platform_name(platform_name)
    value = getattr(node, "platform", None)
    if value:
        return normalize_platform_name(str(value))
    funcargs = getattr(node, "funcargs", None) or {}
    if "mobile_platform" in funcargs:
        return normalize_platform_name(str(funcargs["mobile_platform"]))
    return "android"


def artifact_dir(base_root: Path, node: pytest.Item, platform_name: str | None = None) -> Path:
    target = base_root / resolve_app_group(node) / resolve_platform_group(node, platform_name)
    target.mkdir(parents=True, exist_ok=True)
    return target


def rel_path(path: Path, project_root: Path) -> str:
    try:
        return str(path.relative_to(project_root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def resolve_case_name(item: pytest.Item, nodeid: str) -> str:
    marker = item.get_closest_marker("case_name")
    if marker and marker.args:
        display_name = str(marker.args[0])
        if "[" in nodeid and nodeid.endswith("]"):
            param_suffix = nodeid.rsplit("[", 1)[-1]
            display_name = f"{display_name}[{param_suffix}"
        return display_name
    return nodeid.split("::")[-1] if "::" in nodeid else nodeid


def collect_result_entry(report: pytest.TestReport) -> dict[str, object]:
    nodeid = report.nodeid
    status = "passed" if report.passed else ("failed" if report.failed else "skipped")
    return {
        "nodeid": nodeid,
        "name": str(getattr(report, "case_name", "") or (nodeid.split("::")[-1] if "::" in nodeid else nodeid)),
        "status": status,
        "duration": round(getattr(report, "duration", 0), 2),
        "app": resolve_app_group(report),
        "platform": resolve_platform_group(report),
        "error_message": str(report.longrepr) if report.failed else None,
    }


@dataclass
class SessionReportStore:
    project_root: Path
    session_start: str = field(default_factory=lambda: datetime.now().isoformat())
    test_results: list[dict[str, object]] = field(default_factory=list)
    test_artifacts: dict[str, dict[str, str]] = field(default_factory=dict)

    def add_result(self, report: pytest.TestReport) -> None:
        self.test_results.append(collect_result_entry(report))

    def attach_artifact(self, nodeid: str, kind: str, path: Path) -> None:
        self.test_artifacts.setdefault(nodeid, {})[kind] = rel_path(path, self.project_root)

    def build_payload(self) -> dict[str, object]:
        tests: list[dict[str, object]] = []
        for result in self.test_results:
            nodeid = str(result["nodeid"])
            artifacts = self.test_artifacts.get(nodeid, {})
            tests.append(
                {
                    "name": result["name"],
                    "node_id": nodeid,
                    "status": result["status"],
                    "duration": result["duration"],
                    "app": result["app"],
                    "platform": result["platform"],
                    "screenshot": artifacts.get("screenshot"),
                    "video": artifacts.get("video"),
                    "error_message": result["error_message"],
                }
            )

        passed = sum(1 for test in tests if test["status"] == "passed")
        failed = sum(1 for test in tests if test["status"] == "failed")
        skipped = sum(1 for test in tests if test["status"] == "skipped")
        return {
            "session_start": self.session_start,
            "session_end": datetime.now().isoformat(),
            "total": len(tests),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "tests": tests,
        }
