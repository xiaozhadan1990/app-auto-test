from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy

from tests.common.base_page import BasePage


class AndroidRuijieCloudMyPage(BasePage):
    MY_TAB_LOCATORS = [
        (AppiumBy.XPATH, '//android.view.View[@content-desc="My"]'),
        (AppiumBy.XPATH, '(//android.view.View[@content-desc="My"])[1]'),
        (
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().className("android.view.View").description("My")',
        ),
        (AppiumBy.XPATH, '//*[@text="My" or @text="my"]'),
    ]
    LOGIN_ENTRY_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Register/Log In , Log in to learn more"),
        (
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().descriptionContains("Register/Log In")',
        ),
        (
            AppiumBy.XPATH,
            '//android.view.ViewGroup[contains(@content-desc,"Register/Log In")]',
        ),
    ]
    ACCOUNT_CARD_LOCATORS = [
        (AppiumBy.XPATH, '//android.view.ViewGroup[contains(@content-desc,"@")]'),
        (AppiumBy.XPATH, '//*[contains(@text, "@")]'),
    ]
    LOGOUT_BUTTON_LOCATORS = [
        (AppiumBy.ACCESSIBILITY_ID, "Log out"),
        (AppiumBy.XPATH, '//*[@text="Log out"]'),
        (AppiumBy.XPATH, '//*[@text="Logout"]'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().description("Log out")'),
    ]
    LOGOUT_CONFIRM_LOCATORS = [
        (AppiumBy.XPATH, '(//android.widget.TextView[@text="Logout"])[2]'),
        (AppiumBy.XPATH, '//*[@text="Log out"]'),
        (AppiumBy.XPATH, '//*[@text="Confirm"]'),
    ]

    def open(self) -> None:
        self.click_required(self.MY_TAB_LOCATORS, "My tab not found", timeout=8)

    def open_login_entry(self) -> None:
        self.click_required(self.LOGIN_ENTRY_LOCATORS, "Register/Log In button not found", timeout=8)

    def assert_logged_in(self, email: str, screenshot_name: str) -> None:
        email_locators = [
            (
                AppiumBy.XPATH,
                f'//*[contains(@content-desc, "{email}") or contains(@text, "{email}")]',
            ),
            (AppiumBy.XPATH, f'//*[contains(@text, "{email}")]'),
            (AppiumBy.XPATH, '//*[contains(@text, "@")]'),
            (AppiumBy.ACCESSIBILITY_ID, "Log out"),
            (AppiumBy.XPATH, '//*[@text="Log out" or @text="Logout"]'),
        ]
        self.save_extra_screenshot(screenshot_name, "ruijieCloud")
        assert self.first_visible(email_locators, timeout=8) is not None, (
            f"Login failed, account info not found: {email}"
        )

    def logout(self) -> None:
        self.click_if_exists(self.ACCOUNT_CARD_LOCATORS, timeout=5)
        self.click_required(self.LOGOUT_BUTTON_LOCATORS, "Log out button not found", timeout=8)
        self.click_required(self.LOGOUT_CONFIRM_LOCATORS, "Logout confirm button not found", timeout=8)
