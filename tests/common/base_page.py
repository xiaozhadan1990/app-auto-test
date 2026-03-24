from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from tests.common.mobile_platform import driver_platform_name
from tests.common.reporting import rel_path

Locator = tuple[str, str]


class BasePage:
    def __init__(self, driver):
        self.driver = driver

    @property
    def platform_name(self) -> str:
        return driver_platform_name(self.driver)

    def is_android(self) -> bool:
        return self.platform_name == "android"

    def is_ios(self) -> bool:
        return self.platform_name == "ios"

    def first_clickable(self, locators: Iterable[Locator], timeout: int = 10):
        for by, value in locators:
            try:
                return WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((by, value))
                )
            except TimeoutException:
                continue
        return None

    def first_visible(self, locators: Iterable[Locator], timeout: int = 10):
        for by, value in locators:
            try:
                return WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((by, value))
                )
            except TimeoutException:
                continue
        return None

    def click_if_exists(self, locators: Iterable[Locator], timeout: int = 8) -> bool:
        element = self.first_clickable(locators, timeout=timeout)
        if element is None:
            return False
        element.click()
        return True

    def click_required(
        self,
        locators: Iterable[Locator],
        error_message: str,
        timeout: int = 8,
    ) -> None:
        if not self.click_if_exists(locators, timeout=timeout):
            raise AssertionError(error_message)

    def type_visible(
        self,
        locators: Iterable[Locator],
        text: str,
        *,
        timeout: int = 10,
        blur: bool = False,
    ) -> None:
        element = self.first_visible(locators, timeout=timeout)
        if element is None:
            raise AssertionError(f"Input not found for text: {text}")
        element.click()
        element.clear()
        element.send_keys(text)
        if blur:
            self.hide_keyboard()

    def hide_keyboard(self) -> None:
        try:
            self.driver.hide_keyboard()
            return
        except Exception:
            pass
        if self.is_android():
            try:
                self.driver.press_keycode(4)
            except Exception:
                pass

    def go_back(self) -> None:
        if self.is_android():
            try:
                self.driver.press_keycode(4)
                return
            except Exception:
                pass
        try:
            self.driver.back()
        except Exception:
            pass

    def activate_app(self, app_id: str, settle_seconds: float = 2.0) -> None:
        self.driver.activate_app(app_id)
        if settle_seconds > 0:
            time.sleep(settle_seconds)

    def extra_artifact_dir(self, base: str, app_name: str) -> Path:
        target = Path("reports") / base / app_name / self.platform_name
        target.mkdir(parents=True, exist_ok=True)
        return target

    def save_extra_screenshot(self, file_name: str, app_name: str) -> Path:
        target = self.extra_artifact_dir("screenshots", app_name) / file_name
        self.driver.save_screenshot(str(target))
        return target

    def extra_artifact_rel_path(self, path: Path) -> str:
        return rel_path(path, Path.cwd())
