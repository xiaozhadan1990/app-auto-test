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
    except Exception:
        return []

    try:
        tree = ast.parse(source)
    except Exception:
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


def _resolve_package_display(rel_path: str, abs_path: Path) -> tuple[str, str]:
    """返回测试包显示名与悬浮提示文案。"""
    case_names = _extract_case_names(abs_path)
    if not case_names:
        label = _fallback_package_label(rel_path)
        return label, label
    if len(case_names) == 1:
        label = case_names[0]
        return label, label
    label = f"{case_names[0]} 等{len(case_names)}个用例"
    tooltip = "\n".join(f"{idx}. {name}" for idx, name in enumerate(case_names, start=1))
    return label, tooltip


def list_test_packages(
    app_key: str,
    app_config: Mapping[str, Mapping[str, str]],
    project_root: Path,
) -> list[dict[str, str]]:
    """根据应用键返回可执行测试包列表（value 用于执行，label 用于中文显示）。"""
    default_pkg = app_config.get(app_key, {}).get("default_test_package", "tests")
    package_path = (project_root / default_pkg).resolve()
    packages: list[dict[str, str]] = [
        {
            "value": default_pkg,
            "label": "该应用全部用例",
            "tooltip": "执行该应用目录下全部测试文件",
        }
    ]
    if package_path.exists():
        for f in sorted(package_path.glob("test_*.py")):
            rel_path = f.relative_to(project_root).as_posix()
            label, tooltip = _resolve_package_display(rel_path, f)
            packages.append({"value": rel_path, "label": label, "tooltip": tooltip})
    return packages

