from __future__ import annotations

import time

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import InvalidElementStateException

from tests.common.android_input import adb_input_text
from tests.common.base_page import BasePage


class AndroidLysoraPingPage(BasePage):
    PING_ENTRY_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Ping"),
        (AppiumBy.XPATH, "//*[@text='Ping' and @clickable='true']"),
        (AppiumBy.XPATH, "//*[contains(@content-desc,'Ping') and @clickable='true']"),
        (AppiumBy.XPATH, "(//*[@text='Ping'])[last()]"),
    ]
    PING_FORM_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Enter an IP address or domain name."),
        (AppiumBy.XPATH, "//android.widget.EditText"),
        (AppiumBy.XPATH, "//*[contains(@content-desc,'IP address') or contains(@content-desc,'domain')]"),
        (AppiumBy.XPATH, "//*[contains(@text,'IP address') or contains(@text,'domain')]"),
    ]
    HOST_HINT_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Enter an IP address or domain name."),
        (AppiumBy.XPATH, "//*[contains(@content-desc,'IP address') or contains(@content-desc,'domain')]"),
        (AppiumBy.XPATH, "//*[contains(@text,'IP address') or contains(@text,'domain')]"),
    ]
    HOST_INPUT_LOCATORS = [
        (AppiumBy.XPATH, "//android.widget.EditText"),
        (AppiumBy.XPATH, "(//android.widget.EditText)[1]"),
    ]
    RUN_BUTTON_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Ping"),
        (AppiumBy.XPATH, "//*[@content-desc='Ping' and @clickable='true']"),
        (AppiumBy.XPATH, "(//*[@text='Ping' and @clickable='true'])[last()]"),
    ]
    END_BUTTON_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "End"),
        (AppiumBy.XPATH, "//*[@text='End' and @clickable='true']"),
        (AppiumBy.XPATH, "//*[contains(@content-desc,'End') and @clickable='true']"),
    ]
    RESULT_ACTION_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Compare"),
        (AppiumBy.XPATH, "//*[@text='Compare']"),
        (AppiumBy.XPATH, "//*[contains(@content-desc,'Compare') or contains(@text,'Compare')]"),
        (AppiumBy.ACCESSIBILITY_ID, "End"),
        (AppiumBy.XPATH, "//*[@text='End']"),
        (AppiumBy.XPATH, "//*[contains(@content-desc,'End') or contains(@text,'End')]"),
    ]

    def open(self) -> None:
        if self.is_form_visible():
            return
        for _ in range(3):
            self.click_required(self.PING_ENTRY_LOCATORS, "Ping entry not found", timeout=6)
            time.sleep(0.8)
            if self.is_form_visible():
                return
        raise AssertionError("Ping page did not open after tapping the entry")

    def is_form_visible(self) -> bool:
        return self.first_visible(self.PING_FORM_LOCATORS, timeout=3) is not None

    def enter_host(self, host: str) -> None:
        hint_box = self.first_clickable(self.HOST_HINT_LOCATORS, timeout=8)
        if hint_box is not None:
            hint_box.click()
            time.sleep(0.3)

        host_input = self.first_visible(self.HOST_INPUT_LOCATORS, timeout=12)
        if not self._try_input_text(host, host_input, hint_box):
            raise AssertionError("Ping host input failed")

        typed = self.first_visible(
            [
                (AppiumBy.XPATH, f"//android.widget.EditText[@text='{host}']"),
                (AppiumBy.XPATH, f"//*[contains(@text,'{host}')]"),
            ],
            timeout=4,
        )
        if typed is None:
            time.sleep(0.4)

    def start_ping(self) -> None:
        self.hide_keyboard()
        self.click_required(self.RUN_BUTTON_LOCATORS, "Ping run button not found", timeout=12)

    def end_ping(self) -> None:
        self.click_required(self.END_BUTTON_LOCATORS, "End button not found", timeout=15)

    def assert_result_actions_visible(self) -> None:
        assert self.first_visible(self.RESULT_ACTION_LOCATORS, timeout=30) is not None, (
            "Compare/End actions were not shown after ping execution"
        )

    def _try_input_text(self, host: str, host_input, hint_box) -> bool:
        candidates = []
        if hint_box is not None:
            candidates.append(hint_box)
        try:
            candidates.extend(self.driver.find_elements(AppiumBy.XPATH, "//android.widget.EditText"))
        except Exception:
            pass
        if host_input is not None:
            candidates.insert(0, host_input)

        seen = set()
        for element in candidates:
            element_id = getattr(element, "id", id(element))
            if element_id in seen:
                continue
            seen.add(element_id)
            try:
                element.click()
                try:
                    element.clear()
                except Exception:
                    pass
                for _ in range(2):
                    try:
                        element.set_value(host)
                    except Exception:
                        pass
                    try:
                        element.send_keys(host)
                    except Exception:
                        pass
                    time.sleep(0.3)
                    try:
                        if element.get_attribute("text") == host:
                            return True
                    except Exception:
                        continue
            except InvalidElementStateException:
                continue
            except Exception:
                continue

        try:
            active = self.driver.switch_to.active_element
            for _ in range(2):
                try:
                    active.send_keys(host)
                except Exception:
                    pass
                time.sleep(0.3)
                try:
                    if active.get_attribute("text") == host:
                        return True
                except Exception:
                    continue
        except Exception:
            pass

        if not adb_input_text(host):
            return False
        time.sleep(0.6)
        return True
