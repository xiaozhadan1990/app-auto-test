from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy

from tests.common.base_page import BasePage


class AndroidLysoraToolkitPage(BasePage):
    TOOLKIT_TAB_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "ToolKit"),
        (AppiumBy.ACCESSIBILITY_ID, "Toolkit"),
        (AppiumBy.ACCESSIBILITY_ID, "Tool Kit"),
        (AppiumBy.XPATH, "//*[@content-desc='ToolKit' and @clickable='true']"),
        (AppiumBy.XPATH, "//*[@content-desc='Toolkit' and @clickable='true']"),
        (AppiumBy.XPATH, "//*[@content-desc='Tool Kit' and @clickable='true']"),
        (AppiumBy.XPATH, "//*[@text='ToolKit' and @clickable='true']"),
        (AppiumBy.XPATH, "//*[@text='Toolkit' and @clickable='true']"),
        (AppiumBy.XPATH, "//*[@text='Tool Kit' and @clickable='true']"),
        (AppiumBy.XPATH, "//*[contains(@content-desc,'Tool') and contains(@content-desc,'Kit')]"),
        (AppiumBy.XPATH, "//*[contains(@text,'Tool') and contains(@text,'Kit')]"),
        (AppiumBy.XPATH, "(//*[@text='ToolKit'])[last()]"),
        (AppiumBy.XPATH, "(//*[@text='Toolkit'])[last()]"),
    ]

    def open(self) -> None:
        self.click_required(self.TOOLKIT_TAB_LOCATORS, "ToolKit tab not found", timeout=12)

    def back_to_toolkit(self) -> None:
        toolkit_tab = self.first_visible(self.TOOLKIT_TAB_LOCATORS, timeout=8)
        if toolkit_tab is not None:
            toolkit_tab.click()
            return
        self.go_back()
        toolkit_tab = self.first_visible(self.TOOLKIT_TAB_LOCATORS, timeout=6)
        if toolkit_tab is not None:
            toolkit_tab.click()
