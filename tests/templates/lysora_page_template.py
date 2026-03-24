from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy

from tests.common.base_page import BasePage


class LysoraFeaturePage(BasePage):
    ENTRY_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Feature Entry"),
        (AppiumBy.XPATH, "//*[@text='Feature Entry']"),
    ]
    RESULT_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Expected Result"),
        (AppiumBy.XPATH, "//*[@text='Expected Result']"),
    ]

    def open_feature(self) -> None:
        self.click_required(self.ENTRY_LOCATORS, "Feature entry not found", timeout=10)

    def assert_result_visible(self) -> None:
        assert self.first_visible(self.RESULT_LOCATORS, timeout=10) is not None, (
            "Expected result not visible"
        )
