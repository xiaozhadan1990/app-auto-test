from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy

from tests.lysora.pages.ios._base import IOSLysoraPage


class IOSLysoraMyPage(IOSLysoraPage):
    feature_name = "Lysora My page"
    MY_TAB_LOCATORS = [
        (
            AppiumBy.IOS_CLASS_CHAIN,
            '**/XCUIElementTypeTabBar/**/XCUIElementTypeButton[`name == "My" OR label == "My"`]',
        ),
        (
            AppiumBy.XPATH,
            '//XCUIElementTypeTabBar//XCUIElementTypeButton[@name="My" or @label="My"]',
        ),
        (
            AppiumBy.XPATH,
            '(//XCUIElementTypeTabBar//*[contains(@name,"My") or contains(@label,"My")])[last()]',
        ),
        (
            AppiumBy.ACCESSIBILITY_ID,
            "My",
        ),
        (
            AppiumBy.IOS_PREDICATE,
            'type IN {"XCUIElementTypeButton","XCUIElementTypeStaticText","XCUIElementTypeOther"} AND (name == "My" OR label == "My")',
        ),
    ]
    LOGIN_ENTRY_LOCATORS = [
        (
            AppiumBy.XPATH,
            '//XCUIElementTypeCell[contains(@name,"Register/Log In") or contains(@label,"Register/Log In") or contains(@value,"Register/Log In") or .//*[contains(@name,"Register/Log In") or contains(@label,"Register/Log In") or contains(@value,"Register/Log In")]]',
        ),
        (
            AppiumBy.XPATH,
            '//XCUIElementTypeOther[contains(@name,"Register/Log In") or contains(@label,"Register/Log In") or contains(@value,"Register/Log In") or .//*[contains(@name,"Register/Log In") or contains(@label,"Register/Log In") or contains(@value,"Register/Log In")]]',
        ),
        (
            AppiumBy.XPATH,
            '//*[contains(@name,"Register/Log In") or contains(@label,"Register/Log In") or contains(@value,"Register/Log In")]/ancestor-or-self::XCUIElementTypeCell[1]',
        ),
        (
            AppiumBy.XPATH,
            '//*[contains(@name,"Register/Log In") or contains(@label,"Register/Log In") or contains(@value,"Register/Log In")]/ancestor-or-self::XCUIElementTypeOther[1]',
        ),
        (AppiumBy.ACCESSIBILITY_ID, "Register/Log In"),
        (AppiumBy.ACCESSIBILITY_ID, "Register / Log In"),
        (AppiumBy.ACCESSIBILITY_ID, "Register/Log In\nLog in to learn more"),
        (AppiumBy.ACCESSIBILITY_ID, "Register / Log In\nLog in to learn more"),
        (AppiumBy.ACCESSIBILITY_ID, "Register/Log In , Log in to learn more"),
        (AppiumBy.ACCESSIBILITY_ID, "Register / Log In , Log in to learn more"),
        (AppiumBy.ACCESSIBILITY_ID, "Register/Log In, Log in to learn more"),
        (AppiumBy.ACCESSIBILITY_ID, "Register / Log In, Log in to learn more"),
        (AppiumBy.ACCESSIBILITY_ID, "注册/登录"),
        (
            AppiumBy.IOS_PREDICATE,
            'type IN {"XCUIElementTypeButton","XCUIElementTypeStaticText","XCUIElementTypeOther","XCUIElementTypeCell"} AND (name CONTAINS[c] "Register/Log In" OR label CONTAINS[c] "Register/Log In" OR value CONTAINS[c] "Register/Log In" OR name CONTAINS[c] "Register / Log In" OR label CONTAINS[c] "Register / Log In" OR value CONTAINS[c] "Register / Log In" OR name CONTAINS[c] "Log In" OR label CONTAINS[c] "Log In" OR value CONTAINS[c] "Log In" OR name CONTAINS[c] "log in to learn more" OR label CONTAINS[c] "log in to learn more" OR value CONTAINS[c] "log in to learn more" OR name CONTAINS "登录" OR label CONTAINS "登录" OR value CONTAINS "登录")',
        ),
        (
            AppiumBy.IOS_CLASS_CHAIN,
            '**/XCUIElementTypeCell/**[`name CONTAINS[c] "Register" OR label CONTAINS[c] "Register" OR value CONTAINS[c] "Register" OR name CONTAINS[c] "learn more" OR label CONTAINS[c] "learn more" OR value CONTAINS[c] "learn more" OR name CONTAINS "登录" OR label CONTAINS "登录" OR value CONTAINS "登录"`]',
        ),
        (
            AppiumBy.XPATH,
            '//*[contains(@name,"Register/Log In") or contains(@label,"Register/Log In") or contains(@value,"Register/Log In") or contains(@name,"Register / Log In") or contains(@label,"Register / Log In") or contains(@value,"Register / Log In") or contains(@name,"Log In") or contains(@label,"Log In") or contains(@value,"Log In") or contains(@name,"learn more") or contains(@label,"learn more") or contains(@value,"learn more") or contains(@name,"登录") or contains(@label,"登录") or contains(@value,"登录")]',
        ),
    ]
    JOIN_CLOUD_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Join Lysora Cloud"),
        (
            AppiumBy.IOS_PREDICATE,
            'name CONTAINS "Join Lysora Cloud" OR label CONTAINS "Join Lysora Cloud" OR value CONTAINS "Join Lysora Cloud"',
        ),
    ]
    MY_PAGE_READY_LOCATORS = [
        *LOGIN_ENTRY_LOCATORS,
        (AppiumBy.ACCESSIBILITY_ID, "About Us"),
        (AppiumBy.ACCESSIBILITY_ID, "Submit Syslog"),
        (AppiumBy.ACCESSIBILITY_ID, "Company Management"),
        (
            AppiumBy.IOS_PREDICATE,
            'name CONTAINS[c] "About Us" OR label CONTAINS[c] "About Us" OR value CONTAINS[c] "About Us" OR name CONTAINS[c] "Submit Syslog" OR label CONTAINS[c] "Submit Syslog" OR value CONTAINS[c] "Submit Syslog" OR name CONTAINS[c] "Company Management" OR label CONTAINS[c] "Company Management" OR value CONTAINS[c] "Company Management"',
        ),
    ]

    def _tap_required(self, locators, error_message: str, timeout: int = 10) -> None:
        element = self.first_clickable(locators, timeout=timeout)
        if element is None:
            element = self.first_visible(locators, timeout=timeout)
        if element is None:
            raise AssertionError(error_message)
        element.click()

    def open(self) -> None:
        self._tap_required(self.MY_TAB_LOCATORS, "My tab not found", timeout=10)
        if self.first_visible(self.MY_PAGE_READY_LOCATORS, timeout=6) is None:
            self._tap_required(self.MY_TAB_LOCATORS, "My tab not found", timeout=10)
        assert self.first_visible(self.MY_PAGE_READY_LOCATORS, timeout=8) is not None, (
            "Failed to open Lysora My page after tapping bottom My tab"
        )

    def open_login_entry(self) -> None:
        if self.first_visible(self.MY_PAGE_READY_LOCATORS, timeout=3) is None:
            self.open()
        self._tap_required(
            self.LOGIN_ENTRY_LOCATORS,
            "Register/Log In entry not found",
            timeout=10,
        )

    def is_account_visible(self, email: str, timeout: int = 4) -> bool:
        email_fragment = email.split("@", 1)[0]
        account_locators = [
            (AppiumBy.ACCESSIBILITY_ID, email),
            (
                AppiumBy.IOS_PREDICATE,
                f'name CONTAINS "{email_fragment}" OR label CONTAINS "{email_fragment}" OR value CONTAINS "{email_fragment}"',
            ),
            *self.JOIN_CLOUD_LOCATORS,
        ]
        return self.first_visible(account_locators, timeout=timeout) is not None

    def assert_account_visible(self, email: str, timeout: int = 12) -> None:
        assert self.is_account_visible(email, timeout=timeout), f"Account info not visible: {email}"
