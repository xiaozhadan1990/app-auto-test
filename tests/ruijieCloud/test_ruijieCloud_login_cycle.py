import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pytest
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

"""RuijieCloud 云账号登录用例：覆盖各朵云账号的登录/登出流程验证。"""


@dataclass(frozen=True)
class Account:
    name: str
    email: str
    password: str


ACCOUNTS = [
    Account("la_cloud", "xujianbin-la@yopmail.net", "xzd@1234"),
    Account("me_cloud", "xujianbin-me@yopmail.net", "Ruijie@123"),
    Account("a1_cloud", "xujianbin-a1@yopmail.net", "xzd@1234"),
    Account("ap_cloud", "xujianbin-ap@yopmail.net", "Ruijie@123"),
    Account("us_cloud", "xujianbin-uk@yopmail.net", "Ruijie@123"),
    Account("as_cloud", "xujianbin-as@yopmail.net", "Ruijie@123"),
    Account("uk_cloud", "xujianbin-uk@yopmail.net", "Ruijie@123"),
]
SMOKE_ACCOUNT = next(account for account in ACCOUNTS if account.name == "la_cloud")


def _first_clickable(driver, locators: Iterable[tuple[str, str]], timeout: int = 10):
    for by, value in locators:
        try:
            return WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        except TimeoutException:
            continue
    return None


def _first_visible(driver, locators: Iterable[tuple[str, str]], timeout: int = 10):
    for by, value in locators:
        try:
            return WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
        except TimeoutException:
            continue
    return None


def _click_if_exists(driver, locators: Iterable[tuple[str, str]], timeout: int = 4) -> bool:
    element = _first_clickable(driver, locators, timeout=timeout)
    if not element:
        return False
    element.click()
    return True


def _fill_input(driver, locators: Iterable[tuple[str, str]], text: str, timeout: int = 10):
    input_el = _first_visible(driver, locators, timeout=timeout)
    if not input_el:
        raise AssertionError(f"未找到输入框，无法输入: {text}")
    input_el.click()
    input_el.clear()
    input_el.send_keys(text)

    # 优先尝试收起键盘，避免遮挡登录按钮。
    try:
        driver.hide_keyboard()
    except Exception:
        try:
            driver.press_keycode(4)
        except Exception:
            pass


def _tap_my_tab(driver):
    assert _click_if_exists(
        driver,
        [
            (AppiumBy.XPATH, '//android.view.View[@content-desc="My"]'),
            (AppiumBy.XPATH, '(//android.view.View[@content-desc="My"])[1]'),
            (
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().className("android.view.View").description("My")',
            ),
            (AppiumBy.XPATH, '//*[@text="My" or @text="my"]'),
        ],
        timeout=8,
    ), "未找到底部 my tab"


def _open_login_page(driver):
    assert _click_if_exists(
        driver,
        [
            (AppiumBy.ACCESSIBILITY_ID, "Register/Log In , Log in to learn more"),
            (
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().descriptionContains("Register/Log In")',
            ),
            (
                AppiumBy.XPATH,
                '//android.view.ViewGroup[contains(@content-desc,"Register/Log In")]',
            ),
        ],
        timeout=8,
    ), "未找到 Register/Log in 按钮"


def _click_login(driver):
    assert _click_if_exists(
        driver,
        [
            (AppiumBy.ACCESSIBILITY_ID, "Log in"),
            (AppiumBy.XPATH, '//android.widget.Button[@content-desc="Log in"]'),
            (AppiumBy.XPATH, '//*[@text="Log in"]'),
        ],
        timeout=8,
    ), "未找到登录按钮"


def _accept_dialogs_if_needed(driver):
    _click_if_exists(
        driver,
        [
            (AppiumBy.XPATH, '//*[@text="Agree"]'),
            (AppiumBy.XPATH, '//*[@text="AGREE"]'),
            (AppiumBy.XPATH, '//*[@text="Accept"]'),
            (AppiumBy.XPATH, '//*[@text="ACCEPT"]'),
        ],
        timeout=3,
    )


def _agree_terms_if_present(driver):
    _click_if_exists(
        driver,
        [
            (
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().descriptionContains("I have read and agree")',
            ),
            (
                AppiumBy.XPATH,
                '//android.view.ViewGroup[contains(@content-desc,"I have read and agree")]',
            ),
        ],
        timeout=2,
    )


def _assert_login_success_and_screenshot(driver, account: Account):
    _tap_my_tab(driver)
    time.sleep(1)

    has_account = _first_visible(
        driver,
        [
            (
                AppiumBy.XPATH,
                f'//*[contains(@content-desc, "{account.email}") or contains(@text, "{account.email}")]',
            ),
            (AppiumBy.XPATH, f'//*[contains(@text, "{account.email}")]'),
            (AppiumBy.XPATH, '//*[contains(@text, "@")]'),
            (AppiumBy.ACCESSIBILITY_ID, "Log out"),
            (AppiumBy.XPATH, '//*[@text="Log out" or @text="Logout"]'),
        ],
        timeout=8,
    )

    screenshot_dir = Path("reports/screenshots/ruijieCloud")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot = screenshot_dir / f"{account.name}_login_status.png"
    driver.save_screenshot(str(screenshot))
    assert has_account is not None, f"{account.name} 登录失败，未检测到账号信息"


def _logout(driver):
    _click_if_exists(
        driver,
        [
            (
                AppiumBy.XPATH,
                '//android.view.ViewGroup[contains(@content-desc,"@")]',
            ),
            (AppiumBy.XPATH, '//*[contains(@text, "@")]'),
        ],
        timeout=5,
    )
    assert _click_if_exists(
        driver,
        [
            (AppiumBy.ACCESSIBILITY_ID, "Log out"),
            (AppiumBy.XPATH, '//*[@text="Log out"]'),
            (AppiumBy.XPATH, '//*[@text="Logout"]'),
            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().description("Log out")'),
        ],
        timeout=8,
    ), "未找到 Log out 按钮"
    assert _click_if_exists(
        driver,
        [
            (AppiumBy.XPATH, '(//android.widget.TextView[@text="Logout"])[2]'),
            (AppiumBy.XPATH, '//*[@text="Log out"]'),
            (AppiumBy.XPATH, '//*[@text="Confirm"]'),
        ],
        timeout=8,
    ), "未找到 Logout 弹窗确认按钮"


def _run_ruijie_cloud_login_logout_cycle(driver, account: Account) -> None:
    app_package = os.getenv("RUIJIECLOUD_APP_PACKAGE") or os.getenv("REEYEE_APP_PACKAGE")
    if app_package:
        driver.activate_app(app_package)

    _accept_dialogs_if_needed(driver)
    _tap_my_tab(driver)
    _open_login_page(driver)

    _fill_input(
        driver,
        [
            (AppiumBy.XPATH, '(//android.widget.EditText)[1]'),
            (AppiumBy.XPATH, '//android.widget.EditText[contains(@text, "Email")]'),
        ],
        account.email,
    )
    _fill_input(
        driver,
        [
            (AppiumBy.XPATH, '(//android.widget.EditText)[2]'),
            (AppiumBy.XPATH, '//android.widget.EditText[contains(@text, "password")]'),
        ],
        account.password,
    )

    _agree_terms_if_present(driver)
    _click_login(driver)
    _accept_dialogs_if_needed(driver)
    _assert_login_success_and_screenshot(driver, account)
    _logout(driver)


@pytest.mark.smoke
@pytest.mark.ruijieCloud
@pytest.mark.case_name("RuijieCloud 登录登出循环（冒烟）")
def test_ruijie_cloud_login_logout_cycle_smoke(driver):
    """冒烟：验证 la_cloud 账号可完成 RuijieCloud 登录/登出。"""
    _run_ruijie_cloud_login_logout_cycle(driver, SMOKE_ACCOUNT)


@pytest.mark.full
@pytest.mark.ruijieCloud
@pytest.mark.case_name("RuijieCloud 登录登出循环（全量）")
@pytest.mark.parametrize("account", ACCOUNTS, ids=[a.name for a in ACCOUNTS])
def test_ruijie_cloud_login_logout_cycle(driver, account: Account):
    """全量：验证各朵云账号均可完成 RuijieCloud 登录/登出。"""
    _run_ruijie_cloud_login_logout_cycle(driver, account)
