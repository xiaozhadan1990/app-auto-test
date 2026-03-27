from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy

from tests.common.base_page import BasePage


class AndroidReyeeMyPage(BasePage):
    MY_TAB_LOCATORS = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("我的")'),
        (AppiumBy.ACCESSIBILITY_ID, "My"),
        (AppiumBy.XPATH, '//*[@text="我的"]'),
    ]
    LOGIN_ENTRY_LOCATORS = [
        (AppiumBy.XPATH, '//*[contains(@text, "注册/登录")]'),
        (AppiumBy.XPATH, '//*[contains(@content-desc, "Register/Log In")]'),
        (AppiumBy.XPATH, '//*[contains(@text, "登录")]'),
    ]

    def open(self) -> None:
        self.click_required(self.MY_TAB_LOCATORS, "My tab not found", timeout=8)

    def open_login_entry(self) -> None:
        self.click_required(self.LOGIN_ENTRY_LOCATORS, "Register/Login entry not found", timeout=8)

    def assert_account_visible(self, phone: str) -> None:
        self.save_extra_screenshot("reyee_login_my_account.png", "reyee")
        assert self.is_account_visible(phone), (
            f"Account phone not found on My page: {phone}"
        )

    def is_account_visible(self, phone: str) -> bool:
        account_locators = [
            (AppiumBy.XPATH, f'//*[contains(@text, "{phone}")]'),
            (AppiumBy.XPATH, f'//*[contains(@content-desc, "{phone}")]'),
        ]
        return self.first_visible(account_locators, timeout=6) is not None
