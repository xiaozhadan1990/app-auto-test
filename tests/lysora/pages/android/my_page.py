from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy

from tests.common.base_page import BasePage


class AndroidLysoraMyPage(BasePage):
    MY_TAB_LOCATORS = [
        (
            AppiumBy.XPATH,
            "(//android.view.View[@content-desc='My' and @clickable='true'])[last()]",
        ),
        (AppiumBy.XPATH, "(//*[@text='My' and @clickable='true'])[last()]"),
        (AppiumBy.XPATH, "(//android.widget.TextView[@text='My'])[last()]"),
    ]
    LOGIN_ENTRY_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Register/Log In , Log in to learn more"),
        (
            AppiumBy.XPATH,
            "//*[contains(@content-desc,'Register/Log In') or contains(@text,'Register/Log In')]",
        ),
    ]
    JOIN_CLOUD_LOCATORS = [(AppiumBy.XPATH, "//*[contains(@text,'Join Lysora Cloud')]")]

    def open(self) -> None:
        self.click_required(self.MY_TAB_LOCATORS, "My tab not found", timeout=10)

    def open_login_entry(self) -> None:
        self.click_required(self.LOGIN_ENTRY_LOCATORS, "Register/Log In entry not found", timeout=10)

    def is_account_visible(self, email: str, timeout: int = 4) -> bool:
        email_fragment = email.split("@", 1)[0]
        account_locators = [
            (
                AppiumBy.XPATH,
                f"//*[contains(@text,'{email_fragment}') or contains(@content-desc,'{email_fragment}')]",
            ),
            *self.JOIN_CLOUD_LOCATORS,
        ]
        return self.first_visible(account_locators, timeout=timeout) is not None

    def assert_account_visible(self, email: str, timeout: int = 12) -> None:
        assert self.is_account_visible(email, timeout=timeout), f"Account info not visible: {email}"
