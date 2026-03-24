from __future__ import annotations

from typing import Any


def normalize_platform_name(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if raw in {"ios", "iphone", "ipad"}:
        return "ios"
    return "android"


def driver_platform_name(driver: Any) -> str:
    capabilities = getattr(driver, "capabilities", {}) or {}
    return normalize_platform_name(
        capabilities.get("platformName")
        or capabilities.get("appium:platformName")
    )

