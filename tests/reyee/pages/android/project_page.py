from __future__ import annotations

import time

from appium.webdriver.common.appiumby import AppiumBy

from tests.common.base_page import BasePage


class AndroidReyeeProjectPage(BasePage):
    PROJECT_TAB_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "项目"),
        (AppiumBy.XPATH, '//*[@text="项目" or @content-desc="项目"]'),
    ]
    VIRTUAL_EXPERIENCE_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "虚拟体验"),
        (AppiumBy.XPATH, '//*[@text="虚拟体验" or @content-desc="虚拟体验"]'),
    ]
    COMMON_SCENE_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "通用场景"),
        (AppiumBy.XPATH, '//*[@text="通用场景" or @content-desc="通用场景"]'),
    ]
    CREATE_VIRTUAL_PROJECT_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "创建虚拟项目"),
        (AppiumBy.XPATH, '//*[@text="创建虚拟项目" or @content-desc="创建虚拟项目"]'),
    ]
    PROJECT_MORE_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "更多"),
        (AppiumBy.XPATH, '//*[@text="更多" or @content-desc="更多"]'),
    ]
    DELETE_LOCATORS = [
        (AppiumBy.XPATH, '//*[@text="删除" or @content-desc="删除"]'),
    ]
    CONFIRM_DELETE_LOCATORS = [
        (AppiumBy.XPATH, '//*[@text="确定" or @content-desc="确定"]'),
        (AppiumBy.XPATH, '//*[@text="确认" or @content-desc="确认"]'),
    ]

    def open_project_tab(self) -> None:
        self.click_required(self.PROJECT_TAB_LOCATORS, "Project tab not found", timeout=8)

    def open_virtual_experience(self) -> None:
        self.click_required(self.VIRTUAL_EXPERIENCE_LOCATORS, "Virtual experience entrance not found", timeout=8)

    def open_common_scene(self) -> None:
        self.click_required(self.COMMON_SCENE_LOCATORS, "Common scene option not found", timeout=8)

    def create_virtual_project(self) -> None:
        self.click_required(self.CREATE_VIRTUAL_PROJECT_LOCATORS, "Create virtual project button not found", timeout=8)
        time.sleep(2)

    def assert_project_visible(self, project_keyword: str = "通用场景") -> None:
        keyword_locators = [
            (AppiumBy.XPATH, f'//*[contains(@text, "{project_keyword}")]'),
            (AppiumBy.XPATH, f'//*[contains(@content-desc, "{project_keyword}")]'),
        ]
        assert self.first_visible(keyword_locators, timeout=8) is not None, (
            f"Project keyword not found in project list: {project_keyword}"
        )

    def open_project_more_menu(self) -> None:
        self.click_required(self.PROJECT_MORE_LOCATORS, "Project more menu button not found", timeout=8)

    def click_delete_project(self) -> None:
        self.click_required(self.DELETE_LOCATORS, "Delete button not found", timeout=8)

    def confirm_delete_project(self) -> None:
        self.click_required(self.CONFIRM_DELETE_LOCATORS, "Delete confirm button not found", timeout=8)
        time.sleep(2)

    def assert_project_not_exists(self, project_keyword: str = "通用场景") -> None:
        keyword_locators = [
            (AppiumBy.XPATH, f'//*[contains(@text, "{project_keyword}")]'),
            (AppiumBy.XPATH, f'//*[contains(@content-desc, "{project_keyword}")]'),
        ]
        assert self.first_visible(keyword_locators, timeout=4) is None, (
            f"Project keyword still exists in project list: {project_keyword}"
        )
