from __future__ import annotations

import time

from appium.webdriver.common.appiumby import AppiumBy

from tests.common.base_page import BasePage


class AndroidLysoraDemoExperiencePage(BasePage):
    PROJECT_TAB_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Project"),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("Project")'),
        (AppiumBy.XPATH, '//*[@text="Project"]'),
    ]
    DEMO_EXPERIENCE_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "DEMO, Demo Experience"),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("Demo Experience")'),
        (AppiumBy.XPATH, '//*[@text="Demo Experience"]'),
    ]
    SMB_CCTV_DEMO_LOCATORS = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("SMB_CCTVDemo")'),
        (AppiumBy.XPATH, '//*[contains(@text, "SMB_CCTVDemo")]'),
        (AppiumBy.XPATH, '//*[contains(@content-desc, "SMB_CCTVDemo")]'),
    ]
    CREATE_DEMO_PROJECT_LOCATORS = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("Create a Demo Project")'),
        (AppiumBy.XPATH, '//*[@text="Create a Demo Project"]'),
    ]

    def open_project_tab(self) -> None:
        self.click_required(self.PROJECT_TAB_LOCATORS, "Project tab not found", timeout=8)

    def open_demo_experience(self) -> None:
        self.click_required(self.DEMO_EXPERIENCE_LOCATORS, "Demo Experience button not found", timeout=8)

    def open_smb_cctv_demo(self) -> None:
        self.click_required(self.SMB_CCTV_DEMO_LOCATORS, "SMB_CCTVDemo entry not found", timeout=10)

    def create_demo_project(self) -> None:
        self.click_required(self.CREATE_DEMO_PROJECT_LOCATORS, "Create a Demo Project button not found", timeout=8)

    def wait_and_assert_smb_project_exists(self, wait_seconds: int = 10) -> None:
        time.sleep(wait_seconds)
        self.save_extra_screenshot("demo_project_after_wait.png", "lysora")
        assert self.first_visible(self.SMB_CCTV_DEMO_LOCATORS, timeout=8) is not None, (
            "SMB_CCTVDemo is not visible after creating demo project"
        )
