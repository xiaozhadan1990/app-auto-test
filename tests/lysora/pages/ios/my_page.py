from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy

from tests.lysora.pages.ios._base import IOSLysoraPage


class IOSLysoraMyPage(IOSLysoraPage):
    feature_name = "Lysora My page"
    MY_TAB_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "My"),
        (
            AppiumBy.IOS_PREDICATE,
            'type IN {"XCUIElementTypeButton","XCUIElementTypeStaticText","XCUIElementTypeOther"} AND (name == "My" OR label == "My")',
        ),
        (
            AppiumBy.IOS_CLASS_CHAIN,
            '**/XCUIElementTypeTabBar/**[`name == "My" OR label == "My"`]',
        ),
    ]
    LOGIN_ENTRY_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Register/Log In"),
        (AppiumBy.ACCESSIBILITY_ID, "Register / Log In"),
        (
            AppiumBy.IOS_PREDICATE,
            '(name CONTAINS "Register/Log In" OR label CONTAINS "Register/Log In" OR name CONTAINS "Register / Log In" OR label CONTAINS "Register / Log In")',
        ),
    ]
    JOIN_CLOUD_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Join Lysora Cloud"),
        (
            AppiumBy.IOS_PREDICATE,
            'name CONTAINS "Join Lysora Cloud" OR label CONTAINS "Join Lysora Cloud" OR value CONTAINS "Join Lysora Cloud"',
        ),
    ]

    def open(self) -> None:
        self.click_required(self.MY_TAB_LOCATORS, "My tab not found", timeout=10)

    def open_login_entry(self) -> None:
        self.click_required(self.LOGIN_ENTRY_LOCATORS, "Register/Log In entry not found", timeout=10)

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
