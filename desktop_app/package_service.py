from __future__ import annotations

import ast
from pathlib import Path
from typing import Mapping


def _fallback_package_label(package_path: str) -> str:
    """为未配置映射的测试文件生成中文兜底展示名。"""
    name = Path(package_path).stem
    if name.startswith("test_"):
        name = name[5:]
    pretty = name.replace("_", " ").strip() or package_path
    return f"测试文件-{pretty}"


def _extract_case_names(test_file: Path) -> list[str]:
    """从测试文件中提取 @pytest.mark.case_name("...") 文案。"""
    try:
        source = test_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return []

    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []

    case_names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            func = deco.func
            if not isinstance(func, ast.Attribute) or func.attr != "case_name":
                continue
            if not deco.args:
                continue
            first_arg = deco.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                name = first_arg.value.strip()
                if name:
                    case_names.append(name)

    dedup: list[str] = []
    seen: set[str] = set()
    for name in case_names:
        if name in seen:
            continue
        seen.add(name)
        dedup.append(name)
    return dedup


def _extract_case_priorities(test_file: Path) -> list[int]:
    """从测试文件中提取 @pytest.mark.case_priority(...) 优先级。"""
    try:
        source = test_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return []

    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []

    priorities: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            func = deco.func
            if not isinstance(func, ast.Attribute) or func.attr != "case_priority":
                continue
            if not deco.args:
                continue
            first_arg = deco.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, int) and first_arg.value >= 0:
                priorities.append(first_arg.value)

    dedup: list[int] = []
    seen: set[int] = set()
    for value in priorities:
        if value in seen:
            continue
        seen.add(value)
        dedup.append(value)
    return dedup


def _resolve_package_display(rel_path: str, abs_path: Path) -> tuple[str, str, int | None]:
    """返回测试包显示名、悬浮提示文案和最小优先级。"""
    case_names = _extract_case_names(abs_path)
    priorities = _extract_case_priorities(abs_path)
    min_priority = min(priorities) if priorities else None
    if not case_names:
        label = _fallback_package_label(rel_path)
        return label, label, min_priority
    if len(case_names) == 1:
        label = case_names[0]
        if min_priority is None:
            return label, label, None
        return label, f"P{min_priority} | {label}", min_priority
    label = f"{case_names[0]} 等{len(case_names)}个用例"
    lines = [f"{idx}. {name}" for idx, name in enumerate(case_names, start=1)]
    if min_priority is not None:
        lines.insert(0, f"建议最小优先级: P{min_priority}")
    return label, "\n".join(lines), min_priority


def list_test_packages(
    app_key: str,
    app_config: Mapping[str, Mapping[str, str]],
    project_root: Path,
) -> list[dict[str, str | int]]:
    """根据应用键返回可执行测试包列表（value 用于执行，label 用于中文显示）。"""
    default_pkg = app_config.get(app_key, {}).get("default_test_package", "tests")
    package_path = (project_root / default_pkg).resolve()
    packages: list[dict[str, str | int]] = [
        {
            "value": default_pkg,
            "label": "该应用全部用例",
            "tooltip": "执行该应用目录下全部测试文件（实际顺序由 用例等级 控制）",
            "priority": 0,
        }
    ]

    if not package_path.exists():
        return packages

    files = list(package_path.glob("test_*.py"))
    file_min_priority: dict[Path, int | None] = {}
    for file_path in files:
        priorities = _extract_case_priorities(file_path)
        file_min_priority[file_path] = min(priorities) if priorities else None

    files.sort(
        key=lambda f: (
            file_min_priority[f] is None,
            file_min_priority[f] if file_min_priority[f] is not None else 10_000,
            f.name.lower(),
        )
    )

    for file_path in files:
        rel_path = file_path.relative_to(project_root).as_posix()
        label, tooltip, priority = _resolve_package_display(rel_path, file_path)
        package_item: dict[str, str | int] = {"value": rel_path, "label": label, "tooltip": tooltip}
        if priority is not None:
            package_item["priority"] = priority
        packages.append(package_item)
    return packages
