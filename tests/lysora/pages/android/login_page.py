from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy

from tests.common.base_page import BasePage


class AndroidLysoraLoginPage(BasePage):
    EMAIL_INPUT_LOCATORS = [
        (AppiumBy.XPATH, "(//android.widget.EditText)[1]"),
        (AppiumBy.XPATH, "//*[contains(@text,'Email')]"),
    ]
    PASSWORD_INPUT_LOCATORS = [
        (AppiumBy.XPATH, "(//android.widget.EditText)[2]"),
        (AppiumBy.XPATH, "//*[contains(@text,'password')]"),
    ]
    LOGIN_BUTTON_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Log in"),
        (AppiumBy.XPATH, "//*[@text='Log in' or @content-desc='Log in']"),
    ]
    AGREE_BUTTON_LOCATORS = [
        (
            AppiumBy.XPATH,
            "//*[@text='Agree' or @text='AGREE' or @text='Accept' or @text='I Agree' "
            "or @content-desc='Agree' or @content-desc='Accept']",
        )
    ]
    LOGIN_PAGE_READY_LOCATORS = [
        *EMAIL_INPUT_LOCATORS,
        *PASSWORD_INPUT_LOCATORS,
        *LOGIN_BUTTON_LOCATORS,
    ]

    def is_login_form_visible(self, timeout: int = 8) -> bool:
        return self.first_visible(self.LOGIN_PAGE_READY_LOCATORS, timeout=timeout) is not None

    def assert_login_form_visible(self, timeout: int = 8) -> None:
        assert self.is_login_form_visible(timeout=timeout), "Lysora login page did not open"

    def enter_email(self, email: str) -> None:
        self.type_visible(self.EMAIL_INPUT_LOCATORS, email)
        password_input = self.first_clickable(self.PASSWORD_INPUT_LOCATORS, timeout=10)
        assert password_input is not None, "Password input not found"
        password_input.click()

    def enter_password(self, password: str) -> None:
        self.type_visible(self.PASSWORD_INPUT_LOCATORS, password, blur=True)

    def tap_login(self) -> None:
        self.click_required(self.LOGIN_BUTTON_LOCATORS, "Login button not found", timeout=10)

    def accept_dialog_if_present(self) -> None:
        self.click_if_exists(self.AGREE_BUTTON_LOCATORS, timeout=8)
