from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy

from tests.lysora.pages.ios._base import IOSLysoraPage


class IOSLysoraLoginPage(IOSLysoraPage):
    feature_name = "Lysora login page"
    EMAIL_INPUT_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Email"),
        (
            AppiumBy.IOS_PREDICATE,
            'type == "XCUIElementTypeTextField" AND (name CONTAINS "Email" OR label CONTAINS "Email" OR value CONTAINS "Email")',
        ),
        (AppiumBy.IOS_CLASS_CHAIN, '**/XCUIElementTypeTextField'),
    ]
    PASSWORD_INPUT_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Password"),
        (
            AppiumBy.IOS_PREDICATE,
            'type == "XCUIElementTypeSecureTextField" OR (type == "XCUIElementTypeTextField" AND (name CONTAINS "Password" OR label CONTAINS "Password" OR value CONTAINS "Password"))',
        ),
        (AppiumBy.IOS_CLASS_CHAIN, '**/XCUIElementTypeSecureTextField'),
    ]
    LOGIN_BUTTON_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Log in"),
        (AppiumBy.ACCESSIBILITY_ID, "Login"),
        (
            AppiumBy.IOS_PREDICATE,
            'type == "XCUIElementTypeButton" AND (name == "Log in" OR label == "Log in" OR name == "Login" OR label == "Login")',
        ),
        (
            AppiumBy.IOS_CLASS_CHAIN,
            '**/XCUIElementTypeButton[`name == "Log in" OR label == "Log in" OR name == "Login" OR label == "Login"`]',
        ),
    ]
    AGREE_BUTTON_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Agree"),
        (AppiumBy.ACCESSIBILITY_ID, "Accept"),
        (AppiumBy.ACCESSIBILITY_ID, "I Agree"),
        (
            AppiumBy.IOS_PREDICATE,
            'type == "XCUIElementTypeButton" AND (name == "Agree" OR label == "Agree" OR name == "Accept" OR label == "Accept" OR name == "I Agree" OR label == "I Agree")',
        ),
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
        if password_input is not None:
            password_input.click()

    def enter_password(self, password: str) -> None:
        self.type_visible(self.PASSWORD_INPUT_LOCATORS, password, blur=True)

    def tap_login(self) -> None:
        self.click_required(self.LOGIN_BUTTON_LOCATORS, "Login button not found", timeout=10)

    def accept_dialog_if_present(self) -> None:
        self.click_if_exists(self.AGREE_BUTTON_LOCATORS, timeout=8)
