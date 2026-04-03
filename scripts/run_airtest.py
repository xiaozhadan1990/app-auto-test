from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from desktop_app.airtest_service import DEFAULT_AIRTEST_CASE_ROOT


DEFAULT_CASE_ROOT = DEFAULT_AIRTEST_CASE_ROOT
DEFAULT_LOG_ROOT = PROJECT_ROOT / "reports" / "airtest"


def discover_cases(case_root: Path) -> list[Path]:
    return sorted(path for path in case_root.rglob("*.air") if path.is_dir())


def case_id(case_path: Path, case_root: Path) -> str:
    return case_path.resolve().relative_to(case_root.resolve()).as_posix()


def build_device_uri(platform: str, device: str) -> str:
    normalized = platform.strip().lower()
    if normalized == "android":
        return f"Android://127.0.0.1:5037/{device}"
    if normalized == "ios":
        return f"iOS:///{device}"
    raise ValueError(f"Unsupported platform: {platform}")


def resolve_cases(case_root: Path, selected_cases: list[str]) -> list[Path]:
    available_cases = discover_cases(case_root)
    case_map = {case_id(path, case_root): path for path in available_cases}

    resolved: list[Path] = []
    missing: list[str] = []
    for raw_value in selected_cases:
        value = raw_value.strip()
        if not value:
            continue

        direct_path = Path(value).expanduser()
        if not direct_path.is_absolute():
            direct_path = (case_root / value).resolve()
        if direct_path.is_dir() and direct_path.suffix == ".air":
            resolved.append(direct_path)
            continue

        mapped = case_map.get(value)
        if mapped is not None:
            resolved.append(mapped)
            continue

        matches = [path for key, path in case_map.items() if key.endswith(value)]
        if len(matches) == 1:
            resolved.append(matches[0])
            continue

        missing.append(value)

    if missing:
        display = "\n".join(f"- {item}" for item in missing)
        raise SystemExit(f"Airtest case not found:\n{display}")

    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in resolved:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return deduped


def run_case(
    *,
    case_path: Path,
    case_root: Path,
    device_uri: str,
    log_root: Path,
    airtest_bin: str,
    extra_args: list[str],
) -> int:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    case_log_dir = log_root / case_path.stem / timestamp
    case_log_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        airtest_bin,
        "run",
        str(case_path),
        "--device",
        device_uri,
        "--log",
        str(case_log_dir),
        *extra_args,
    ]

    print(f"\n[airtest] running: {case_id(case_path, case_root)}")
    print(f"[airtest] command: {shlex.join(cmd)}")
    print(f"[airtest] log dir: {case_log_dir}")

    completed = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        check=False,
        text=True,
    )
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Airtest cases on a specified device.",
    )
    parser.add_argument("--platform", required=True, choices=["android", "ios"], help="Target mobile platform.")
    parser.add_argument("--device", required=True, help="Target device serial/UDID.")
    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        default=[],
        help="Airtest case path or relative case id, for example tests/lysora/airtest/login.air",
    )
    parser.add_argument("--device-uri", help="Override the generated Airtest device URI.")
    parser.add_argument("--case-root", default=str(DEFAULT_CASE_ROOT), help="Directory used to discover .air cases.")
    parser.add_argument("--log-root", default=str(DEFAULT_LOG_ROOT), help="Directory used to store Airtest logs.")
    parser.add_argument("--airtest-bin", default="airtest", help="Airtest executable name or full path.")
    parser.add_argument("--list", action="store_true", help="List discoverable Airtest cases and exit.")
    parser.add_argument(
        "--continue-on-fail",
        action="store_true",
        help="Keep running the remaining cases after one case fails.",
    )
    parser.add_argument(
        "extra_args",
        nargs=argparse.REMAINDER,
        help="Extra args passed through to `airtest run` after `--`.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    case_root = Path(args.case_root).resolve()
    log_root = Path(args.log_root).resolve()
    available_cases = discover_cases(case_root)

    if args.list:
        if not available_cases:
            print("No Airtest cases found.")
            return 0
        for path in available_cases:
            print(case_id(path, case_root))
        return 0

    if not args.cases:
        parser.error("At least one --case is required unless --list is used.")

    selected_cases = resolve_cases(case_root, args.cases)
    device_uri = args.device_uri or build_device_uri(args.platform, args.device)
    extra_args = list(args.extra_args)
    if extra_args[:1] == ["--"]:
        extra_args = extra_args[1:]

    failures: list[str] = []
    for current_case in selected_cases:
        exit_code = run_case(
            case_path=current_case,
            case_root=case_root,
            device_uri=device_uri,
            log_root=log_root,
            airtest_bin=args.airtest_bin,
            extra_args=extra_args,
        )
        if exit_code == 0:
            continue
        failures.append(f"{case_id(current_case, case_root)} (exit code: {exit_code})")
        if not args.continue_on_fail:
            break

    if failures:
        print("\n[airtest] failed cases:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\n[airtest] all selected cases finished successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
