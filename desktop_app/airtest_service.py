from __future__ import annotations

import html
import json
import os
import urllib.parse
from pathlib import Path
from typing import Callable
from typing import Any


DEFAULT_AIRTEST_CASE_ROOT = (
    Path(r"D:\workspace\airtestProject\自动化测试")
    if os.name == "nt"
    else Path("/Users/ruijie/Documents/workspace/airProject/自动化测试")
)


def airtest_case_root() -> Path:
    configured = (os.getenv("AIRTEST_CASE_ROOT") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_AIRTEST_CASE_ROOT.resolve()


def airtest_bin() -> str:
    return (os.getenv("AIRTEST_BIN") or "airtest").strip() or "airtest"


_PREFERRED_SCRIPT_DIR_ORDER = ("海外app", "国内app", "白牌app")


def _contains_common_segment(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.resolve().relative_to(root.resolve()).parts
    except Exception:
        rel_parts = path.parts
    for part in rel_parts:
        normalized = part.strip().lower()
        if normalized == "common":
            return True
        if Path(normalized).stem == "common":
            return True
    return False


def _safe_subdir(root: Path, subdir: str | None) -> Path | None:
    value = (subdir or "").strip()
    if not value:
        return root
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except Exception:
        return None
    if not candidate.exists() or not candidate.is_dir():
        return None
    return candidate


def discover_airtest_cases(
    case_root: Path | None = None,
    *,
    script_dir: str | None = None,
    exclude_common: bool = False,
) -> list[Path]:
    root = (case_root or airtest_case_root()).resolve()
    if not root.exists():
        return []
    scan_root = _safe_subdir(root, script_dir)
    if scan_root is None:
        return []
    discovered = sorted(path for path in scan_root.rglob("*.air") if path.is_dir())
    if not exclude_common:
        return discovered
    return [path for path in discovered if not _contains_common_segment(path, root)]


def list_airtest_script_dirs(case_root: Path | None = None) -> list[dict[str, str]]:
    root = (case_root or airtest_case_root()).resolve()
    if not root.exists() or not root.is_dir():
        return []
    discovered = discover_airtest_cases(root, exclude_common=True)
    top_dirs: set[str] = set()
    for case_path in discovered:
        rel_parts = case_path.relative_to(root).parts
        if not rel_parts:
            continue
        name = rel_parts[0].strip()
        if name and name.lower() != "common":
            top_dirs.add(name)
    if not top_dirs:
        return []

    def _sort_key(name: str) -> tuple[int, str]:
        try:
            return (_PREFERRED_SCRIPT_DIR_ORDER.index(name), name)
        except ValueError:
            return (len(_PREFERRED_SCRIPT_DIR_ORDER), name)

    ordered = sorted(top_dirs, key=_sort_key)
    return [{"key": name, "label": f"{name} Airtest 脚本集"} for name in ordered]


def case_id(case_path: Path, case_root: Path | None = None) -> str:
    root = (case_root or airtest_case_root()).resolve()
    return case_path.resolve().relative_to(root).as_posix()


def resolve_airtest_cases(selected_cases: list[str], case_root: Path | None = None) -> list[Path]:
    root = (case_root or airtest_case_root()).resolve()
    discovered = discover_airtest_cases(root)
    case_map = {case_id(path, root): path for path in discovered}

    resolved: list[Path] = []
    missing: list[str] = []
    for raw_value in selected_cases:
        value = raw_value.strip()
        if not value:
            continue
        mapped = case_map.get(value)
        if mapped is not None:
            resolved.append(mapped)
            continue

        direct_path = Path(value).expanduser()
        if not direct_path.is_absolute():
            direct_path = root / direct_path
        direct_path = direct_path.resolve()
        if direct_path.is_dir() and direct_path.suffix == ".air":
            resolved.append(direct_path)
            continue

        fuzzy_matches = [path for key, path in case_map.items() if key.endswith(value)]
        if len(fuzzy_matches) == 1:
            resolved.append(fuzzy_matches[0])
            continue

        missing.append(value)

    if missing:
        values = ", ".join(missing)
        raise FileNotFoundError(f"未找到 Airtest 用例: {values}")

    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in resolved:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return deduped


def list_airtest_packages(
    case_root: Path | None = None,
    *,
    script_dir: str | None = None,
    exclude_common: bool = True,
) -> list[dict[str, str | int]]:
    root = (case_root or airtest_case_root()).resolve()
    packages: list[dict[str, str | int]] = []
    for path in discover_airtest_cases(root, script_dir=script_dir, exclude_common=exclude_common):
        rel_id = case_id(path, root)
        label = path.stem.strip() or rel_id
        packages.append(
            {
                "value": rel_id,
                "label": label,
                "tooltip": f"{label}\n{path}",
            }
        )
    return packages


def build_airtest_device_uri(platform: str, device: str) -> str:
    normalized = (platform or "").strip().lower()
    if normalized == "android":
        return f"Android://127.0.0.1:5037/{device}"
    if normalized == "ios":
        return f"iOS:///{device}"
    return device


def find_first_artifact(log_root: Path, suffixes: tuple[str, ...]) -> Path | None:
    if not log_root.exists():
        return None
    candidates = sorted(
        (path for path in log_root.rglob("*") if path.is_file() and path.suffix.lower() in suffixes),
        key=lambda item: item.stat().st_mtime_ns if item.exists() else 0,
        reverse=True,
    )
    return candidates[0] if candidates else None


def write_task_results(
    task_id: str,
    task_results: list[dict[str, Any]],
    results_file: Path,
    *,
    session_start: str,
    session_end: str,
) -> None:
    passed = sum(1 for item in task_results if str(item.get("status") or "").lower() == "passed")
    failed = sum(1 for item in task_results if str(item.get("status") or "").lower() == "failed")
    skipped = sum(1 for item in task_results if str(item.get("status") or "").lower() == "skipped")
    payload = {
        "task_id": task_id,
        "session_start": session_start,
        "session_end": session_end,
        "total": len(task_results),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "tests": task_results,
    }
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_task_html_report(
    task_id: str,
    task_results: list[dict[str, Any]],
    report_file: Path,
    *,
    report_path_mapper: Callable[[str], str],
    session_start: str,
    session_end: str,
) -> None:
    rows: list[str] = []
    for item in task_results:
        status = str(item.get("status") or "-")
        color = "#16a34a" if status == "passed" else "#dc2626" if status == "failed" else "#d97706"
        report_rel_path = str(item.get("case_report_path") or "").strip()
        report_link = (
            f'<a href="/api/report_asset?path={urllib.parse.quote(report_path_mapper(report_rel_path))}" target="_blank">查看 Airtest 报告</a>'
            if report_rel_path
            else "-"
        )
        error_message = html.escape(str(item.get("error_message") or "-"))
        rows.append(
            "<tr>"
            f"<td>{int(item.get('case_index') or 0)}</td>"
            f"<td>{html.escape(str(item.get('name') or '-'))}</td>"
            f"<td>{html.escape(str(item.get('node_id') or '-'))}</td>"
            f"<td style='color:{color};font-weight:700'>{html.escape(status)}</td>"
            f"<td>{float(item.get('duration') or 0):.2f}s</td>"
            f"<td>{report_link}</td>"
            f"<td><pre>{error_message}</pre></td>"
            "</tr>"
        )

    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(
        f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Airtest Task Report - {html.escape(task_id)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; background: #f8fafc; color: #0f172a; }}
    h1 {{ margin-bottom: 8px; }}
    .meta {{ margin-bottom: 20px; color: #475569; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; }}
    th, td {{ padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: left; vertical-align: top; }}
    th {{ background: #e2e8f0; }}
    pre {{ margin: 0; white-space: pre-wrap; }}
    .summary {{ display: flex; gap: 12px; margin: 16px 0 20px; }}
    .card {{ background: #fff; padding: 14px 16px; border-radius: 12px; min-width: 120px; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06); }}
    .value {{ font-size: 24px; font-weight: 700; }}
  </style>
</head>
<body>
  <h1>Airtest 任务报告</h1>
  <div class="meta">任务 ID: {html.escape(task_id)} | 开始时间: {html.escape(session_start)} | 结束时间: {html.escape(session_end)}</div>
  <div class="summary">
    <div class="card"><div>总数</div><div class="value">{len(task_results)}</div></div>
    <div class="card"><div>通过</div><div class="value">{sum(1 for item in task_results if str(item.get("status") or "").lower() == "passed")}</div></div>
    <div class="card"><div>失败</div><div class="value">{sum(1 for item in task_results if str(item.get("status") or "").lower() == "failed")}</div></div>
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>脚本</th>
        <th>标识</th>
        <th>状态</th>
        <th>耗时</th>
        <th>报告</th>
        <th>错误信息</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows) if rows else '<tr><td colspan="7">暂无执行结果</td></tr>'}
    </tbody>
  </table>
</body>
</html>
""",
        encoding="utf-8",
    )
