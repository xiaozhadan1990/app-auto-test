from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy

from tests.common.base_page import BasePage


class AndroidRuijieCloudLoginPage(BasePage):
    EMAIL_INPUT_LOCATORS = [
        (AppiumBy.XPATH, "(//android.widget.EditText)[1]"),
        (AppiumBy.XPATH, '//android.widget.EditText[contains(@text, "Email")]'),
    ]
    PASSWORD_INPUT_LOCATORS = [
        (AppiumBy.XPATH, "(//android.widget.EditText)[2]"),
        (AppiumBy.XPATH, '//android.widget.EditText[contains(@text, "password")]'),
    ]
    LOGIN_BUTTON_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Log in"),
        (AppiumBy.XPATH, '//android.widget.Button[@content-desc="Log in"]'),
        (AppiumBy.XPATH, '//*[@text="Log in"]'),
    ]
    AGREE_TERMS_LOCATORS = [
        (
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().descriptionContains("I have read and agree")',
        ),
        (
            AppiumBy.XPATH,
            '//android.view.ViewGroup[contains(@content-desc,"I have read and agree")]',
        ),
    ]
    ACCEPT_DIALOG_LOCATORS = [
        (AppiumBy.XPATH, '//*[@text="Agree"]'),
        (AppiumBy.XPATH, '//*[@text="AGREE"]'),
        (AppiumBy.XPATH, '//*[@text="Accept"]'),
        (AppiumBy.XPATH, '//*[@text="ACCEPT"]'),
    ]

    def enter_email(self, email: str) -> None:
        self.type_visible(self.EMAIL_INPUT_LOCATORS, email, blur=True)

    def enter_password(self, password: str) -> None:
        self.type_visible(self.PASSWORD_INPUT_LOCATORS, password, blur=True)

    def agree_terms_if_present(self) -> None:
        self.click_if_exists(self.AGREE_TERMS_LOCATORS, timeout=2)

    def tap_login(self) -> None:
        self.click_required(self.LOGIN_BUTTON_LOCATORS, "Login button not found", timeout=8)

    def accept_dialogs_if_needed(self) -> None:
        self.click_if_exists(self.ACCEPT_DIALOG_LOCATORS, timeout=3)
