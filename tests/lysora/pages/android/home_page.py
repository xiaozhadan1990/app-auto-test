from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy

from tests.common.base_page import BasePage


class AndroidLysoraHomePage(BasePage):
    PROJECT_TAB_LOCATORS = [
        (AppiumBy.XPATH, "(//*[@text='Project' and @clickable='true'])[last()]"),
        (
            AppiumBy.XPATH,
            "(//android.view.View[@content-desc='Project' and @clickable='true'])[last()]",
        ),
        (AppiumBy.XPATH, "(//android.widget.TextView[@text='Project'])[last()]"),
    ]
    SCAN_ENTRY_LOCATORS = [
        (AppiumBy.XPATH, '//*[@text="Scan"]'),
        (AppiumBy.XPATH, '//*[contains(@text, "Scan QR Code")]'),
        (AppiumBy.ACCESSIBILITY_ID, "Scan"),
    ]

    def assert_loaded(self) -> None:
        project_tab = self.first_clickable(self.PROJECT_TAB_LOCATORS, timeout=5)
        if project_tab is not None:
            project_tab.click()
        scan_entry = self.first_visible(self.SCAN_ENTRY_LOCATORS, timeout=12)
        assert scan_entry is not None, "Lysora home did not load correctly"
