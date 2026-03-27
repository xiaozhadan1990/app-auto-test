from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy

from tests.common.base_page import BasePage


class AndroidReyeeLoginPage(BasePage):
    PHONE_INPUT_LOCATORS = [
        (AppiumBy.XPATH, '//android.widget.EditText[contains(@text, "手机号")]'),
        (AppiumBy.XPATH, "(//android.widget.EditText)[1]"),
    ]
    PASSWORD_INPUT_LOCATORS = [
        (AppiumBy.XPATH, '//android.widget.EditText[contains(@text, "密码")]'),
        (AppiumBy.XPATH, "(//android.widget.EditText)[2]"),
    ]
    LOGIN_BUTTON_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "登录"),
        (AppiumBy.XPATH, '//*[@text="登录"]'),
    ]
    AGREE_DIALOG_LOCATORS = [
        (AppiumBy.XPATH, '//*[@text="同意"]'),
        (AppiumBy.XPATH, '//*[@text="我同意"]'),
        (AppiumBy.XPATH, '//*[@text="Agree"]'),
    ]

    def enter_phone(self, phone: str) -> None:
        self.type_visible(self.PHONE_INPUT_LOCATORS, phone, blur=True)

    def enter_password(self, password: str) -> None:
        self.type_visible(self.PASSWORD_INPUT_LOCATORS, password, blur=True)

    def tap_login(self) -> None:
        self.click_required(self.LOGIN_BUTTON_LOCATORS, "Login button not found", timeout=8)

    def accept_user_agreement_if_present(self) -> None:
        self.click_if_exists(self.AGREE_DIALOG_LOCATORS, timeout=5)
