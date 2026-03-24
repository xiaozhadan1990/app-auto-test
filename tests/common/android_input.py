from __future__ import annotations

import os
import subprocess


def adb_input_text(text: str) -> bool:
    serial = (os.getenv("APPIUM_UDID") or "").strip()
    if not serial:
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=8,
                encoding="utf-8",
                errors="ignore",
            )
            if result.returncode == 0:
                for line in (result.stdout or "").splitlines():
                    line = line.strip()
                    if "\tdevice" in line:
                        serial = line.split("\t", 1)[0].strip()
                        break
        except Exception:
            serial = ""
    if not serial:
        return False

    safe_text = text.replace(" ", "%s")
    try:
        result = subprocess.run(
            ["adb", "-s", serial, "shell", "input", "text", safe_text],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="ignore",
        )
        return result.returncode == 0
    except Exception:
        return False
